import sys
from mcp.server.fastmcp import FastMCP
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage
from fdagent_wrapper import food_drug_agent_node

# redirect all print to stderr (so stdout stays JSON clean)
print = lambda *a, **kw: __builtins__.print(*a, file=sys.stderr, **kw)

mcp = FastMCP("FoodDrugInteractionServer")

# ---------- Build minimal graph ----------
async def _build_graph():
    workflow = StateGraph(dict)
    workflow.add_node("food_drug_agent", food_drug_agent_node)
    workflow.add_edge(START, "food_drug_agent")
    workflow.add_edge("food_drug_agent", END)
    graph = workflow.compile()
    graph = graph.with_config({"configurable": {"thread_id": "MCP:fooddrug"}})
    return graph

_graph_cache = None
async def get_graph():
    global _graph_cache
    if _graph_cache is None:
        _graph_cache = await _build_graph()
    return _graph_cache

# ---------- Expose tool ----------
@mcp.tool()
async def food_drug_interaction(food: str, drug: str) -> str:
    """Analyze potential interactions between a given food and drug."""
    query = f"How is the interaction between food {food} and drug {drug}?"
    print(f"🧠 Running food–drug agent for query: {query}")

    graph = await get_graph()

    # Pass the right state
    result = await graph.ainvoke({"messages": [HumanMessage(content=query)]})
    print("🧾 RAW FOOD–DRUG OUTPUT:\n", result)

    # Extract meaningful output
    if isinstance(result, dict):
        for k in ("final_answer", "exact_result", "similar_result"):
            if k in result and isinstance(result[k], str):
                return result[k]
        if "messages" in result:
            for m in reversed(result["messages"]):
                if hasattr(m, "content") and isinstance(m.content, str):
                    return m.content

    return "No interaction found or unable to determine."

if __name__ == "__main__":
    mcp.run(transport="stdio")
