# file: agent_setup.py
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from food_drug_interaction_agent import tools as agent_tools
from food_drug_interaction_agent import utils
import json

# 1. Define Agent State
class AgentState(TypedDict):
    input: str
    food: str
    drug: str
    exact_result: str
    similar_result: str
    final_answer: str


# 2. Extract (food, drug)
def extract_food_drug_node(state: AgentState) -> AgentState:
    """
    Uses the LLM (llama3.1:8b) to extract the food and drug names from user input.
    If already provided by parent, reuse those values.
    """
    # If values already exist from parent agent, skip extraction
    if state.get("food") not in (None, "", "unknown") and state.get("drug") not in (None, "", "unknown"):
        print(f"Using pre-detected food/drug from parent: {state['food']} + {state['drug']}")
        return state

    user_input = state.get("input", "")
    prompt = f"""
    You are an expert information extractor for biomedical questions.
    From the following text, identify the FOOD and DRUG mentioned.

    If the text does not clearly mention either, output "unknown".

    Return your answer in **pure JSON only**, like this:
    {{
        "food": "grapefruit",
        "drug": "paclitaxel"
    }}

    Text: "{user_input}"
    """
    print("🔍 Extracting food & drug using LLM...")
    response = utils.llm.invoke(prompt)

    try:
        parsed = json.loads(response.content.strip())
        food = parsed.get("food", "unknown").strip().lower()
        drug = parsed.get("drug", "unknown").strip().lower()
    except Exception as e:
        print(f"LLM extraction failed: {e}. Response: {response}")
        food, drug = "unknown", "unknown"

    return {**state, "food": food, "drug": drug}


# 3. Exact Match Tool
def find_exact_interaction_node(state: AgentState) -> AgentState:
    """Call the exact interaction tool."""
    food, drug = state["food"], state["drug"]
    if food in ("unknown", None, "") or drug in ("unknown", None, ""):
        raise ValueError(f"Missing food/drug: {food}, {drug}")

    tool_input = json.dumps({"food": food, "drug": drug})
    result = agent_tools.find_exact_interaction.run(tool_input)
    return {**state, "exact_result": result}


# 4. Similarity Search Tool
def find_similar_interaction_node(state: AgentState) -> AgentState:
    """Call the similar interaction tool."""
    food, drug = state["food"], state["drug"]
    tool_input = json.dumps({"food": food, "drug": drug})
    result = agent_tools.find_similar_interaction.run(tool_input)
    return {**state, "similar_result": result}


# 5. Decision Logic
def decide_next(state: AgentState) -> str:
    """Decide whether to use exact result or search for similar."""
    exact_result = state["exact_result"]
    if "Found exact interaction" in exact_result:
        return "final_answer"
    return "similar_search"


# 6. Final Summarization & Output
def generate_final_answer(state: AgentState) -> AgentState:
    """
    Generate a summarized, user-friendly final answer:
    - If exact match found → summarize the exact interaction.
    - If similar matches found → list top 3 pairs with short summaries.
    """
    exact_result = state["exact_result"]
    similar_result = state.get("similar_result", "")
    food, drug = state["food"], state["drug"]

    # CASE 1 — Exact Interaction Found
    if "Found exact interaction" in exact_result:
        raw_text = exact_result.replace("Found exact interaction:", "").strip()
        print(f"Summarizing exact interaction for {food} + {drug}...")

        prompt = f"""
        You are a biomedical assistant.
        Summarize the following exact food–drug interaction information
        into 2–3 short sentences suitable for a patient.

        Focus on:
        - Type of interaction
        - Severity
        - What the patient should do

        Food: {food}
        Drug: {drug}

        Text to summarize:
        {raw_text[:2000]}

        Respond only with the summary text.
        """

        try:
            summary = utils.llm.invoke(prompt)
            summary_text = summary.content.strip()
            final_answer = (
                f"**Found exact interaction between '{food}' and '{drug}':**\n\n"
                f"{summary_text}\n\n"
                "This summary is for informational purposes only. Always consult your doctor."
            )
            print("Exact interaction summarized successfully.")
        except Exception as e:
            print(f"Summarization failed: {e}")
            final_answer = f"Found exact interaction:\n\n{raw_text[:600]}..."

    # CASE 2 — No Exact Match → Similar Matches
    else:
        if not similar_result or "An error occurred" in similar_result or "--- Result" not in similar_result:
            final_answer = f"No interaction information found between '{food}' and '{drug}'."
        else:
            print(f"🧠 Summarizing top 3 similar pairs for {food} + {drug}...")

            prompt = f"""
            You are a biomedical assistant analyzing food–drug similarity search results.

            The user asked about: {food} and {drug}

            Below are the top similar interactions retrieved from the database.
            For each of the top 3 results:
            1. Identify the food–drug pair
            2. Write 1–2 short sentences summarizing the interaction
            3. End with an overall conclusion about potential risk for {food} and {drug}

            Format your response exactly like this:

            **Top 3 Similar Interactions:**

            1. **[pair name]** — [summary 1–2 sentences]
            2. **[pair name]** — [summary 1–2 sentences]
            3. **[pair name]** — [summary 1–2 sentences]

            **Overall Assessment:** [final statement]

            Text to analyze:
            {similar_result}
            """

            try:
                summary = utils.llm.invoke(prompt)
                summary_text = summary.content.strip()
                final_answer = (
                    f"No exact match found for '{food}' and '{drug}'.\n\n"
                    f"{summary_text}\n\n"
                    "This summary is for informational purposes only. Always consult your doctor."
                )
                print("Similar interaction summaries generated.")
            except Exception as e:
                print(f"Summarization failed: {e}")
                final_answer = similar_result

    return {**state, "final_answer": final_answer}


# 7. Build the LangGraph Agent
def create_agent_graph():
    """Create and return the Food–Drug Interaction agent graph."""
    workflow = StateGraph(AgentState)

    # Define nodes
    workflow.add_node("parse_input", extract_food_drug_node)
    workflow.add_node("exact_search", find_exact_interaction_node)
    workflow.add_node("similar_search", find_similar_interaction_node)
    workflow.add_node("final_answer", generate_final_answer)

    # Define edges
    workflow.set_entry_point("parse_input")
    workflow.add_edge("parse_input", "exact_search")
    workflow.add_conditional_edges(
        "exact_search",
        decide_next,
        {
            "final_answer": "final_answer",
            "similar_search": "similar_search",
        },
    )
    workflow.add_edge("similar_search", "final_answer")
    workflow.add_edge("final_answer", END)

    agent = workflow.compile()
    return agent


# ======================================================
# 8. Instantiate Agent
# ======================================================
agent = create_agent_graph()
