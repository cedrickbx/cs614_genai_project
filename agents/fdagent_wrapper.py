# file: fdagent_wrapper.py
import os, sys
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from food_drug_interaction_agent.agent_setup import agent as fd_agent

async def food_drug_agent_node(state):
    """
    Async node to call the Food–Drug Interaction agent inside LangGraph.
    It extracts the user's last query, invokes the FD sub-agent synchronously,
    and appends its answer as a new AI message.
    Also includes web search results from earlier in the conversation.
    """
    input_messages = state.get("messages", [])
    user_msg = next((m for m in reversed(input_messages) if isinstance(m, HumanMessage)), None)
    query = user_msg.content if user_msg else state.get("input", "")

    # Check for web search results in the message history
    web_search_results = []
    
    print(f"[DEBUG] Total messages in state: {len(input_messages)}")
    print(f"[DEBUG] Message types: {[type(msg).__name__ for msg in input_messages]}")
    
    for msg in input_messages:
        if isinstance(msg, ToolMessage):
            tool_name = getattr(msg, 'name', '')
            print(f"[DEBUG] Found ToolMessage: name='{tool_name}', content_length={len(msg.content) if msg.content else 0}")
            if 'search' in tool_name.lower() or 'brave' in tool_name.lower():
                content = msg.content
                print(f"📰 [DEBUG] Web search tool found! Content preview: {content[:200] if content else 'EMPTY'}...")
                if content and len(content) > 50:  # Only include substantial results
                    web_search_results.append(content)
                    print(f"[DEBUG] Added to web_search_results (total: {len(web_search_results)})")
    
    print(f"[DEBUG] Final web_search_results count: {len(web_search_results)}")
    
    # Run the Food–Drug agent synchronously (it's not async)
    fd_state = {"input": query}
    result = await fd_agent.ainvoke(fd_state)

    # Extract final answer text and food/drug info
    final_answer = result.get("final_answer", "")
    food = result.get("food", "unknown")
    drug = result.get("drug", "unknown")
    
    # If final_answer is empty, it means the query wasn't about food-drug interaction
    # In this case, don't add any food-drug interaction content
    if not final_answer or final_answer.strip() == "":
        print("Food-drug agent returned empty result. Skipping food-drug response.")
        # Return the state unchanged - the main agent's response will be used
        return state
    
    # Build the enhanced answer
    parts = []
    
    # Add logging confirmation
    if food not in ("unknown", None, "") and drug not in ("unknown", None, ""):
        parts.append(f"I logged your **{food}** intake and **{drug}** medication to the database.\n\n---\n")
    
    # Add database interaction result
    parts.append(final_answer)
    
    # Add web search results if available
    if web_search_results:
        parts.append("\n\n**Recent Studies/Information:**\n")
        # Summarize or include the first web search result
        search_summary = web_search_results[0][:500] + "..." if len(web_search_results[0]) > 500 else web_search_results[0]
        parts.append(f"{search_summary}")
        parts.append("\n\n*(Source: Web Search)*")
    
    enhanced_answer = "".join(parts)
    
    # Return updated state with appended message
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=enhanced_answer)]
    }
