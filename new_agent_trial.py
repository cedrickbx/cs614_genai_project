import os, json, asyncio, re, time
from datetime import datetime, timezone, timedelta
import zoneinfo
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from dotenv import load_dotenv
from typing import TypedDict, Any, Dict, List
from langchain_core.messages import HumanMessage, AIMessage, AnyMessage
from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, START, END
from langchain_core.tools import Tool
from fdagent_wrapper import food_drug_agent_node
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from food_drug_interaction_agent import utils


load_dotenv()

class AgentState(TypedDict):
    messages: List[AnyMessage]

SYS_PROMPT = r"""
You are a health enquiry helper bot for ONE user. You can read/update a small local DB, check for food-food/food-drug/drug-drug interactions, or search the web via MCP tools.

YOU HAVE ACCESS TO THESE TOOLS:
{tools}
(Available tool names: {tool_names})

TOOLS (exact argument shapes)
- check_schema() → returns all tables and their columns.
- table_query({
    "table": "medical_history"|"medication"|"food_24h",
    "columns": [string],                       # optional
    "where": { "<col>": value | {"op": "<=|>=|=|!=|<|>|LIKE|IN", "value": any} },  # optional
    "order_by": [string],                      # LIST, e.g. ["updated_at"]
    "limit": integer,                          # default 50
    "offset": integer                          # default 0
  })
- table_insert({ "table": string, "values": { "<col>": any, ... } })
- table_update({ "table": string, "values": { ... }, "where": { ... } })   # WHERE required
- table_delete({ "table": string, "where": { ... } })                      # WHERE required
- brave_web_search(query: string)
- brave_local_search(query: string)
- brave_video_search(query: string)
- brave_image_search(query: string)
- brave_news_search(query: string)
- brave_summarizer(url: string | text: string)


TIME ANCHOR
- Current absolute time (source of truth): {NOW_ISO} (UNIX {NOW_UNIX}, Asia/Singapore).
- When you say “last 24 hours”, compute the cutoff as {NOW_UNIX} - 86400 and use it in queries.
- Never guess times or fabricate logs. If a table query returns no rows, say that plainly and ask whether to log something.

DB FACTS
- Tables:
  medical_history(condition, diagnosis_date, severity, status, created_at, updated_at)
  medication(name, dosage, time_taken, condition_id, status, created_at, updated_at)
  food_24h(name, notes, taken_at, created_at)
  texts(texts_ID, document, link)
  TM_interactions(TM_interactions_ID, texts_ID, start_index, end_index, food, drug)
- No user_id columns (single-user DB).
- Auto-retention: food_24h >24h deleted; medical_history with status starting "recovered" deleted ~14 days after last update.

RULES
- Before writing, call check_schema to avoid typos.
- Prefer structured tool calls; do NOT write raw SQL.
- If no DB action is needed, answer directly in simple, non-jargony language.
- When calling table_query, OMIT optional fields if unused (do NOT send "where": {}, "order_by": [], or "columns": []).

USAGE RULES
- If the user asks about information that should exist in the DB (e.g., “what medical history have you logged?”, “what food have I eaten?”, “what meds did I log?”), you MUST first call `table_query` (do not describe the tool call). If you have not called `table_query` (or it returned 0 rows), do NOT invent or guess;  clearly say you found no records in the database.
- If user asks “can I take X now?”, first query DB for recent foods/meds; then reason and, if needed, use web search to fact-check interactions.
- On the first turn where the user mentions a condition or medication, attempt a quick read of relevant tables with `table_query` to ground the reply (e.g., query `medical_history`, `medication`, or `food_24h` as appropriate).
- If input is vague (e.g., “I just took Panadol”), ask up to 3 concise follow-ups (reason/condition, dose, time taken, any recent foods) and then confirm whether to log.
- Never print tool JSON or internal reasoning in your reply. Use tools internally, then give a concise, user-facing answer.
- Always reference relevant facts from earlier turns (e.g., if the user said “stomach cancer”, acknowledge that context in later replies).
- If the user describes an action that clearly implies eating or taking something, you MUST automatically record it in the correct table even if the user does not explicitly say "insert" or "log". For example:
  - “I ate chicken rice for lunch.” → call `table_insert` into `food_24h` with the current time.
  - “I took Panadol 500mg this morning.” → call `table_insert` into `medication` with name="Panadol", dosage="500mg", time_taken="morning".
- If the user describes **both** eating food and taking medication in the same message (e.g., “I ate chicken pasta and took paracetamol 500mg”), you MUST insert into **both** tables:
  - one `table_insert` into `food_24h` for the food,
  - and one `table_insert` into `medication` for the medication.
- Ask clarifying questions only if essential fields (like dosage or time) are missing, but otherwise insert immediately.
- Do NOT wait for the user to say “insert it” if the intent to record is obvious from the message.
  to summarize any possible interaction and include it in your answer.
- If both food and drug are mentioned, after logging them, you MUST call the tool:
  food_drug_interaction({"food": ..., "drug": ...}) immediately — do not just describe that you will do it.
- Use `brave_web_search` when you need general factual or health-related information that is not in the local DB.
- Use `brave_news_search` for time-sensitive or recent developments (e.g., "latest", "recent", "new study").
- Use `brave_image_search` or `brave_video_search` only when the user explicitly requests images or videos.
- Use `brave_local_search` only if the user asks for something location-specific (e.g., “clinics near me”).
- Use `brave_summarizer` to summarize a specific article or webpage when a URL is provided.

IMPORTANT CONTROL RULE:
  When both a food and a drug are detected in the same user input:
  1. ALWAYS call table_insert for the food.
  2. ALWAYS call table_insert for the medication.
  3. THEN, and only after both have succeeded, you MUST call food_drug_interaction({"food": ..., "drug": ...}).
  4. You are NOT finished until you have called food_drug_interaction and received its Observation.
  5. Your Final Answer must summarize that interaction result.

FINALIZATION RULES
- You MUST stop immediately after calling `food_drug_interaction` once.
- Never repeat any tool call that already succeeded.
- If you already logged both food and medication and got an interaction observation,
  you MUST produce your Final Answer and stop reasoning.
- If a tool returns "success" or "none", treat it as done and proceed to finalize.
- Do NOT ever call a tool twice in the same reasoning sequence.

CONCRETE EXAMPLES (follow exactly):
Example 1 — “what food have I eaten?”:
  Action: table_query
  Action Input: {"table":"food_24h","order_by":["taken_at"],"limit":20}
  (If rows==0) Final Answer: “I couldn’t find any food entries in the last 24 hours.”
  (If rows>0) Final Answer: short list with name + time; no extra items not in DB.

Example 2 — “what medications am I on?”:
  Action: table_query
  Action Input: {"table":"medication","order_by":["updated_at"],"limit":20}
  Then summarize ONLY rows returned.

Example 3 — “I ate chicken pasta and took 50mg of paclitaxel today at noon”:
  Thought: The user mentioned both food and medication. I should log both.
  Action 1: table_insert
  Action Input: {"table":"food_24h","values":{"name":"chicken pasta","notes":"","taken_at":"2025-11-01T12:00:00+08:00"}}
  Observation: {"status":"success"}

  Thought: Now I should log the medication.
  Action 2: table_insert
  Action Input: {"table":"medication","values":{"name":"paclitaxel","dosage":"50mg","time_taken":"2025-11-01T12:00:00+08:00"}}
  Observation: {"status":"success"}

  Thought: Both food and drug are logged. Now I will check their possible interaction.
  Action 3: food_drug_interaction
  Action Input: {"food":"chicken pasta","drug":"paclitaxel"}
  Observation: "No exact match found, but similar interactions suggest increased risk when co-administered."

  Thought: The local agent did not find a confident match, so I will verify with web search for the latest clinical or scientific references.
  Action 4: brave_news_search
  Action Input: {"query": "chicken pasta paclitaxel food drug interaction"}
  Observation: “Recent articles and health sources report that high-fat meals may affect paclitaxel absorption, suggesting general caution.”
  
  Final Answer: “I’ve logged your meal and medication. There’s no direct interaction found between chicken pasta and paclitaxel, but similar interactions show meals high in fat may influence absorption. (Verified via Brave Search MCP tool)”

Example 4 — "What are recent studies on grapefruit and paclitaxel?"
  Action: brave_news_search
  Action Input: {"query": "grapefruit paclitaxel site:pubmed.ncbi.nlm.nih.gov OR site:fda.gov"}
  Observation: Summary of top news or research.
  Final Answer: "I found recent PubMed and FDA studies showing grapefruit may increase paclitaxel absorption. (Source: Brave Search MCP tool)"

WEB SEARCH PRESENTATION RULES:
- When you call brave_web_search, brave_news_search, or any web search tool, you MUST include the findings in your final response.
- Format web search results as: "**Recent Studies/News:**\n[summarize key findings from the search]"
- ALWAYS cite that the information came from web search (e.g., "According to recent sources..." or "Recent studies show...")
- Place web search findings AFTER the database interaction results but BEFORE the warning disclaimer.
- Example format:
  I logged your **grapefruit** and **paclitaxel**...
  
  ---
  
  **Found exact interaction:** [database result]
  
  **Recent Studies:** A 2024 study found... [web search results]
  
  This summary is for informational purposes only...

FORMAT (ReAct controller only)
Use Thought/Action/Action Input/Observation internally so tools are called correctly, but your final user message must NOT include those lines. End with a short, friendly answer or a clear set of follow-up questions. Keep a warm tone.
"""

def _extract_json_or_text(s: Any) -> Dict[str, Any]:
    if isinstance(s, dict):
        return s
    if not isinstance(s, str):
        return {"query": str(s)}
    s = s.strip()
    if s.startswith("{"):
        m = re.search(r"\{.*\}", s, flags=re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {"query": s.splitlines()[0].strip()}

def _clean_tool_args(d: Dict[str, Any]) -> Dict[str, Any]:
    """Remove empty optional fields so the MCP server sees them as absent."""
    if not isinstance(d, dict):
        return d
    # Normalize shapes first (in case the LLM produced single strings)
    if isinstance(d.get("order_by"), str):
        d["order_by"] = [d["order_by"]]
    if isinstance(d.get("columns"), str):
        d["columns"] = [d["columns"]]

    # Drop empties so Optional[...] defaults kick in on the server
    for k in ("where", "order_by", "columns"):
        v = d.get(k, None)
        if v is None or v == {} or v == []:
            d.pop(k, None)
    return d

def _normalize_query_args(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Force a consistent shape for table_query and backfill safe defaults."""
    # Some runners put args under 'arguments'
    args = payload if isinstance(payload, dict) and "table" in payload else payload.get("arguments", payload)
    if not isinstance(args, dict):
        return payload  # let the tool error with a clear message

    # Coerce singletons → lists
    if isinstance(args.get("order_by"), str):
        args["order_by"] = [args["order_by"]]
    if isinstance(args.get("columns"), str):
        args["columns"] = [args["columns"]]

    # Always provide a dict for `where` so pydantic sees a dict (not None/1/etc)
    if "where" not in args or args["where"] is None:
        args["where"] = {}

    # Table-specific helpful defaults:
    tbl = args.get("table")
    if tbl == "food_24h":
        # Keep results relevant and deterministic if the LLM omitted them
        args.setdefault("order_by", ["taken_at"])
        # If no user filter provided, default to last 24h
        if not args["where"]:
            args["where"] = {"taken_at":{"op": ">=", "value":int(time.time()) - 24*3600}}
        args.setdefault("limit", 50)

    elif tbl == "medication":
        args.setdefault("order_by", ["updated_at"])
        if not args["where"]:
            args["where"] = {"created_at":{"op": "<", "value":int(time.time())}}
        args.setdefault("limit", 50)
        # leave args["where"] as {} unless the model provided something

    elif tbl == "medical_history":
        args.setdefault("order_by", ["updated_at"])
        if not args["where"]:
            args["where"] = {"created_at":{"op": "<", "value":int(time.time())}}
        args.setdefault("limit", 50)

    return args

# Local extractor helper for main agent 
def extract_food_drug_node(state: dict) -> dict:
    """
    Uses the qwen:8b model (utils.llm) to extract FOOD and DRUG entities
    from a free-form user query.
    """
    user_input = state.get("input", "").strip()
    if not user_input:
        return {**state, "food": "unknown", "drug": "unknown"}

    prompt = f"""
    You are an expert biomedical text parser.
    Identify any FOOD and DRUG mentioned in the text below.

    For example, return ONLY valid JSON (no markdown, no commentary):
    {{
        "food": "grapefruit",
        "drug": "paclitaxel"
    }}

    Text: "{user_input}"
    """

    print("Extracting food & drug using LLM...")
    response = utils.llm.invoke(prompt)

    try:
        parsed = json.loads(response.content.strip())
        food = parsed.get("food", "unknown").strip().lower()
        drug = parsed.get("drug", "unknown").strip().lower()
    except Exception as e:
        print(f"LLM extraction failed: {e}. Response: {response}")
        food, drug = "unknown", "unknown"

    return {**state, "food": food, "drug": drug}


async def build_once():
    # --- inject current time for grounding ---
    SGT = zoneinfo.ZoneInfo("Asia/Singapore")
    now_dt = datetime.now(SGT)
    NOW_ISO = now_dt.isoformat(timespec="seconds")
    NOW_UNIX = int(now_dt.timestamp())
    # Make a copy of the prompt and inject time markers without .format()
    prompt_with_time = SYS_PROMPT.replace("{NOW_ISO}", NOW_ISO).replace("{NOW_UNIX}", str(NOW_UNIX))

    model = ChatOllama(model="qwen3:8b", temperature=0.2)
    mcp_servers = {
        "database": {
            "transport": "stdio",
            "command": "python",
            "args": ["userdb.py"],
        },
        "websearch": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@brave/brave-search-mcp-server", "--transport", "stdio"],
            "env": {"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY", "")},
        },
    }

    # 3) Create the client (no context manager here)
    client = MultiServerMCPClient(mcp_servers)

    # 4) Load all tools from the MCP client
    tools = await client.get_tools()

    wrapped: List[Tool] = []
    for t in tools:
        async def _acall(s: Any, _t=t):
            # if already a dict (LangGraph passes structured input), use it directly
            if isinstance(s, dict):
                data = s
            else:
                data = _extract_json_or_text(s)

            if getattr(_t, "name", "") == "table_query" and isinstance(data, dict):
                data = _normalize_query_args(data)
            else:
                data = _clean_tool_args(data)

            if hasattr(_t, "ainvoke"):
                return await _t.ainvoke(data)
            if hasattr(_t, "invoke"):
                return _t.invoke(data)
            return str(data)

        def _call(s: Any, _t=t):
            if isinstance(s, dict):
                data = s
            else:
                data = _extract_json_or_text(s)

            if getattr(_t, "name", "") == "table_query" and isinstance(data, dict):
                data = _normalize_query_args(data)
            else:
                data = _clean_tool_args(data)

            if hasattr(_t, "invoke"):
                return _t.invoke(data)
            return str(data)


        wrapped.append(
            Tool(
                name=t.name,
                description=getattr(t, "description", "") or "MCP tool",
                func=_call,
                coroutine=_acall,
                handle_tool_errors=True,
            )
        )
    print(f"Final wrapped tools: {[t.name for t in wrapped]}")
    agent = create_react_agent(model, wrapped, prompt=prompt_with_time)

    # CONDITIONAL ROUTER
    async def decide_next_step(state: AgentState) -> str:
        """Decide whether to call the Food–Drug Interaction agent or end."""

        # Only consider the most recent *HumanMessage* (not tool or AI)
        user_msg = ""
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage) and hasattr(msg, "content"):
                user_msg = msg.content.strip()
                if user_msg:
                    break

        if not user_msg:
            print("No user message found → terminating.")
            return "terminate"

        print(f"\n[DEBUG] Latest HumanMessage extracted for entity detection:\n{user_msg}\n")

        print("Checking for possible food–drug mention in query...")

        # Use local helper for extraction
        result_state = extract_food_drug_node({"input": user_msg})
        food = result_state.get("food")
        drug = result_state.get("drug")

        print("[DEBUG] Extraction result state:", result_state)
        print(f"[DEBUG] Parsed entities → food='{food}', drug='{drug}'\n")

        if food == "unknown" and drug == "unknown":
            print(f"No valid food–drug pair detected → ending process. (food={food}, drug={drug})")
            return "terminate"

        if food == "unknown" or drug == "unknown":
            missing = "food" if food == "unknown" else "drug"
            print(f"Only one entity found ({missing} missing) → ending process.")
            return "terminate"

        print(f"Detected valid pair → food='{food}', drug='{drug}'")

        structured_query = f"How is the interaction between food {food} and drug {drug}?"
        print(f"Reformatted for sub-agent: {structured_query}")

        state["messages"].append(HumanMessage(content=structured_query))
        return "food_drug_agent"

    workflow = StateGraph(AgentState)
    async def main_agent(state: AgentState) -> AgentState:
        #check by streaming events
        async for ev in agent.astream_events({"messages": state["messages"]},version="v2",config={"configurable": {"thread_id": "USER:local"}},):
            if ev["event"] == "on_tool_start":
                print(f"[tool] {ev.get('name')} → args={ev.get('inputs')}")
            elif ev["event"] == "on_tool_end":
                print(f"[tool] {ev.get('name')} ✓")
        result = await agent.ainvoke({"messages": state["messages"]},config={"configurable": {"thread_id": "USER:local"}})
        return {"messages": result["messages"]}

    # Add all nodes
    workflow.add_node("main_agent", main_agent)
    workflow.add_node("food_drug_agent", food_drug_agent_node)
    workflow.add_node("merge_node", lambda state: state)  

    # Add conditional branch logic
    workflow.add_conditional_edges(
        "main_agent",
        decide_next_step,
        {
            "food_drug_agent": "food_drug_agent",  
            "terminate": "merge_node",             
        },
    )

    # Merge both branches back together
    workflow.add_edge("food_drug_agent", "merge_node")

    # Entry & exit points
    workflow.set_entry_point("main_agent")
    workflow.add_edge("merge_node", END)

    conn = await aiosqlite.connect("agent_memory.sqlite3")
    checkpointer = AsyncSqliteSaver(conn)
    graph = workflow.compile(checkpointer=checkpointer)
    graph = graph.with_config({"configurable": {"thread_id": "USER:local", "checkpoint_ns":"healthbot"}})

    return client, agent, graph


async def async_main():
    client, agent, graph = await build_once()
    # Default thread for persistence
    graph = graph.with_config({"configurable": {"thread_id": "USER:local"}})

    # Persistent in-memory chat history of message objects
    history: List[AnyMessage] = []

    while True:
        q = input("Please enter your query (Ctrl+C to exit): ").strip()
        if not q:
            continue

        print("\nAssistant is thinking...\n")
        
        # FEED ONLY THE NEW USER MESSAGE; prior turns are loaded from the checkpointer
        final_state = await graph.with_config({"recursion_limit": 10}).ainvoke({"messages": [HumanMessage(content=q)]})
        
        # Print latest assistant reply
        msgs = final_state["messages"]
        last_ai = next((m for m in reversed(msgs) if isinstance(m, AIMessage)), None)
        print("\n" + (last_ai.content if last_ai else "").strip() + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nBye!\n")
