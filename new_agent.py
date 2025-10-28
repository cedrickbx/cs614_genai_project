import os, json, asyncio, re
from dotenv import load_dotenv
from typing import TypedDict, Any, Dict, List
from langchain_core.messages import HumanMessage, AIMessage, AnyMessage
from langchain_ollama import ChatOllama
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.tools import Tool

load_dotenv()

class AgentState(TypedDict):
    messages: List[AnyMessage]

SYS_PROMPT = r"""
You are a health enquiry helper bot for ONE user. You can read/update a small local DB, check for food-food/food-drug/drug-drug interactions or search for related events via MCP tools.

TOOLS (exact argument shapes)
- check_schema(table: string) → columns for a table.
- table_query({
    "table": "medical_history"|"medication"|"food_24h",
    "columns": [string],                       # optional
    "where": { "<col>": value | {"op": "<=|>=|=|!=|<|>|LIKE|IN", "value": any} },  # optional
    "order_by": [string],                      # <-- LIST of columns, e.g. ["updated_at"]
    "limit": integer,                          # default 50
    "offset": integer                          # default 0
  })
- table_insert({ "table": string, "values": { "<col>": any, ... } })
- table_update({ "table": string, "values": { ... }, "where": { ... } })   # WHERE required
- table_delete({ "table": string, "where": { ... } })                      # WHERE required

DB FACTS
- Tables:
  medical_history(condition, diagnosis_date, severity, status, created_at, updated_at)
  medication(name, dosage, time_taken, condition_id, status, created_at, updated_at)
  food_24h(name, notes, taken_at, created_at)
- No user_id columns (single-user DB).
- Auto-retention: food_24h >24h deleted; medical_history with status starting "recovered" deleted ~14 days after last update.

RULES
- Before writing, call check_schema to avoid typos.
- Ask brief confirmation before writes if info is ambiguous.
- Prefer structured tool calls; do NOT write raw SQL.
- If no DB action needed, answer directly in simple, non-jargony language.

USAGE RULES
- If the user asks about information that exists in the DB (e.g., “what medical history have you logged?”), CALL `table_query` directly. Do NOT explain the tool call; just do it.
- If user asks “can I take X now?”, first query DB for recent foods/meds; then reason and use the tools to support your reasoning if needed.
- Before any write, `check_schema` once to avoid typos. For reads, you may skip it if column names are obvious.
- If input is vague (e.g., “I just took Panadol”), ask up to 3 concise follow-ups: reason/condition, dose, time taken, and any recent foods/meds that might interact. Then confirm whether to log.
- Never print tool JSON or internal reasoning in your reply. Use tools internally, then give a concise, user-facing answer.

FORMAT (ReAct controller only)
Use Thought/Action/Action Input/Observation internally so tools are called correctly, but your final user message must NOT include those lines. End with a short, friendly ans warm answer or a clear set of follow-up questions.
Speak to the user directly in natural language. Keep a friendly and warm tone on your responses.
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

async def build_once():
    # Fast local model; adjust as needed
    model = ChatOllama(model="qwen3:4b", temperature=0.2)
    mcp_servers = {
        "database": {
            "transport": "stdio",
            "command": "python",
            "args": [os.path.join(os.getcwd(), "userdb.py")],
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
            # ---- schema guards for your DB tools ----
            if getattr(_t, "name", "") == "table_query" and isinstance(data, dict):
                args = data if "table" in data else data.get("arguments", data)
                ob = args.get("order_by")
                if isinstance(ob, str):
                    args["order_by"] = [ob]            # coerce to list
                # optional: ensure columns is a list if present but single string
                cols = args.get("columns")
                if isinstance(cols, str):
                    args["columns"] = [cols]
            # ----------------------------------------

            if hasattr(_t, "ainvoke"): return await _t.ainvoke(data)
            if hasattr(_t, "invoke"):  return _t.invoke(data)
            if hasattr(_t, "arun"):    return await _t.arun(data)
            if hasattr(_t, "run"):     return _t.run(data)
            return str(data)

        def _call(s: str, _t=t):
            data = _extract_json_or_text(s)
            if hasattr(_t, "invoke"):
                return _t.invoke(data)
            elif hasattr(_t, "run"):
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

    agent = create_react_agent(model, wrapped, prompt=SYS_PROMPT)
    workflow = StateGraph(AgentState)
    async def main_agent(state: AgentState) -> AgentState:
        result = await agent.ainvoke({"messages": state["messages"]},config={"configurable": {"thread_id": "USER:local"}})
        return {"messages": result["messages"]}

    workflow.add_node("main_agent", main_agent)
    workflow.add_edge(START, "main_agent")
    workflow.add_edge("main_agent", END)
    graph = workflow.compile(checkpointer=InMemorySaver())
    graph = graph.with_config({"configurable": {"thread_id": "USER:local"}})

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

        # Add the new user message
        history.append(HumanMessage(content=q))

        print("\nAssistant is thinking...\n")

        # Run the graph with full history; keep agent depth short
        final_state = await graph.with_config({"recursion_limit": 10}).ainvoke(
            {"messages": history}
        )

        # The agent returns a full updated message list (objects)
        history = final_state["messages"]

        # Find the most recent assistant reply and print its text
        last_ai = next((m for m in reversed(history) if isinstance(m, AIMessage)), None)
        print("\n" + (last_ai.content if last_ai else "").strip() + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nBye!\n")