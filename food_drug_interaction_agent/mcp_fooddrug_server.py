import asyncio
from langchain_core.tools import tool
from food_drug_interaction_agent.agent_setup import agent

@tool
def food_drug_interaction(query: str) -> str:
    """
    Analyze potential interactions between a food and a drug mentioned in the query.
    Returns the summarized result from the internal LangGraph food-drug agent.
    """
    print(f"Running food-drug agent for query: {query}")
    state = {"input": query}
    result = agent.invoke(state)
    return result.get("final_answer", "No result found.")
