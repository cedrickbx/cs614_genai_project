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
# from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.tools import Tool

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

TIME ANCHOR
- Current absolute time (source of truth): {NOW_ISO} (UNIX {NOW_UNIX}, Asia/Singapore).
- When you say “last 24 hours”, compute the cutoff as {NOW_UNIX} - 86400 and use it in queries.
- Never guess times or fabricate logs. If a table query returns no rows, say that plainly and ask whether to log something.

DB FACTS
- Tables:
  medical_history(condition, diagnosis_date, severity, status, created_at, updated_at)
  medication(name, dosage, time_taken, condition_id, status, created_at, updated_at)
  food_24h(name, notes, taken_at, created_at)
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
            args["where"] = {"taken_at":{"op": ">=", "value":int(time.time()) - 24*3600}}
        args.setdefault("limit", 50)
        # leave args["where"] as {} unless the model provided something

    elif tbl == "medical_history":
        args.setdefault("order_by", ["updated_at"])
        if not args["where"]:
            args["where"] = {"taken_at":{"op": ">=", "value":int(time.time()) - 24*3600}}
        args.setdefault("limit", 50)

    return args

async def build_once():
    # --- inject current time for grounding ---
    SGT = zoneinfo.ZoneInfo("Asia/Singapore")
    now_dt = datetime.now(SGT)
    NOW_ISO = now_dt.isoformat(timespec="seconds")
    NOW_UNIX = int(now_dt.timestamp())
    # Make a copy of the prompt and inject time markers without .format()
    prompt_with_time = SYS_PROMPT.replace("{NOW_ISO}", NOW_ISO).replace("{NOW_UNIX}", str(NOW_UNIX))
    
    # model_id = os.getenv("HF_MODEL_ID")
    # hf_token = os.getenv("HF_TOKEN")

    # endpoint = HuggingFaceEndpoint(repo_id=model_id, 
    #                         huggingfacehub_api_token=hf_token,
    #                         temperature=0.2,
    #                         max_new_tokens= 128,
    #                         )
    # model = ChatHuggingFace(llm=endpoint)
    # Fast local model; adjust as needed
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

    # 4) Load *all* tools now (will start each server once to fetch metadata)
    tools = await client.get_tools()

    wrapped: List[Tool] = []
    for t in tools:
        async def _acall(s: str, _t=t):
            # ---- schema guards for DB tools ----
            data = _extract_json_or_text(s)
            if getattr(_t, "name", "") == "table_query" and isinstance(data, dict):
                data = _normalize_query_args(data)
            else:
                data = _clean_tool_args(data)    

            if hasattr(_t, "ainvoke"):
                return await _t.ainvoke(data)
            if hasattr(_t, "invoke"):
                return _t.invoke(data)
            if hasattr(_t, "arun"):
                return await _t.arun(data)
            if hasattr(_t, "run"):
                return _t.run(data)
            return str(data)
        
        def _call(s: str, _t=t):
            data = _extract_json_or_text(s)
            if getattr(_t, "name", "") == "table_query" and isinstance(data, dict):
                data = _normalize_query_args(data)
            else:
                data = _clean_tool_args(data)

            if hasattr(_t, "invoke"):
                return _t.invoke(data)
            if hasattr(_t, "run"):
                return _t.run(data)
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

    agent = create_react_agent(model, wrapped, prompt=prompt_with_time)
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

    workflow.add_node("main_agent", main_agent)
    workflow.add_edge(START, "main_agent")
    workflow.add_edge("main_agent", END)
    # graph = workflow.compile(checkpointer=InMemorySaver())
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