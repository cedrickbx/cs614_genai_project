# agent_config.py
# Agent configuration with direct tools (NO MCP SERVERS)
import os
import sys
import torch
from typing import List
# from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage, AnyMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_react_agent
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
import utils

import tools as agent_tools

tools_list = [
    agent_tools.find_exact_interaction,
    agent_tools.find_similar_interaction,
]

# ========= SYSTEM PROMPT ==========
react_prompt_template = r"""
You are a helpful health assistant agent.
You MUST strictly follow this workflow.

Question: {messages}
{agent_scratchpad}

## Tools
You can use these tools:
{tools}

Valid tool names are: {tool_names}

---

## Workflow (Max 3 Tool Calls)

1️⃣ **Initial Understanding**
   - Thought: I need to understand what the user is asking — e.g., to check their medical history, record new food intake, add a medication, or search for general medical information.
   - If the query is about **data in the database** (medical_history, medication, or food_24h), use `check_schema` first to inspect available tables and columns.
   - Then use `query_table` or `search_by_condition` as needed to retrieve information.

2️⃣ **Information Update Phase**
   - If the user wants to **add** a new entry:
       - For a new condition: use find_exact_interaction
       - For a new medication: use find_exact_interaction
       - For a food intake: use find_exact_interaction
   - Thought: I will format the tool input correctly with required arguments and call the right insert tool.

3️⃣ **Web Information Phase**
   - IF the user asks for general medical knowledge (e.g., symptoms, treatment, diet advice), use `web_search`.
   - Thought: I will ensure the query is safe and relevant to medical information only.

4️⃣ **Final Reasoning and Response**
   - After gathering all Observations:
       - Thought: I have obtained all necessary information or confirmed updates.
       - Final Answer: Summarize findings or confirm actions in clear, human-readable language.
         (Example: "I’ve added your new medication record successfully." or "According to the web search, this food is rich in fiber and helps with digestion.")

---

## Critical Rules
- Never fabricate or assume medical data — only report what’s found in the database or web search.
- Never call the same insert or query tool more than once per user query.
- Always stop after producing **Final Answer:**
- Always preserve exact Observation text from tools when summarizing.
- If no results found, politely explain and suggest what the user could try next.

---

## Output Format
Use this format exactly:

Question: The user's input.
Thought: Your reasoning step.
Action: The chosen tool from [{tool_names}].
Action Input: JSON with the correct parameters.
Observation: The tool's output.
Thought: Your concluding reasoning.
Final Answer: [The complete summarized response. DO NOT include tool names or any debugging text.]

---
"""

# system_prompt = ChatPromptTemplate.from_template(react_prompt_template)
system_prompt = ChatPromptTemplate.from_messages([
    ("system", react_prompt_template)
])

# ========= AGENT BUILDER ==========
def build_agent(model_type="drive", model_path=None):
    """Build the complete agent"""
    # Initialize database
    print("🗄️  Initializing database...")
    
    # Load model
    model = utils.llm

    # Load tools
    tools = tools_list
    
    
    agent_runnable = create_react_agent(llm=model, tools=tools, prompt=system_prompt)

    agent = AgentExecutor(
        agent=agent_runnable,
        tools=tools_list,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=2,          # hard limit: prevents infinite loop
    )
    
    return agent
    
#     # Build workflow
#     workflow = StateGraph(dict)
    
#     def main_agent(state: dict):
#         result = agent.invoke({"messages": state["messages"]})
#         return {"messages": result["messages"]}
    
#     workflow.add_node("main_agent", main_agent)
#     workflow.add_edge(START, "main_agent")
#     workflow.add_edge("main_agent", END)
    
#     compiled = workflow.compile(checkpointer=InMemorySaver())
#     return compiled

# # ========= AGENT RUNNER ==========
# class AgentRunner:
#     """High-level agent wrapper"""
    
#     def __init__(self, model_type="drive", model_path=None):
#         self.model_type = model_type
#         self.model_path = model_path
#         self.graph = None
#         self.history: List[AnyMessage] = []
    
#     def init(self):
#         """Initialize the agent"""
#         print("\nInitializing Health Assistant Agent...")
#         self.graph = build_agent(self.model_type, self.model_path)
#         self.graph = self.graph.with_config({
#             "configurable": {"thread_id": "USER:local"}
#         })
#         print("Agent ready!\n")
    
#     def ask(self, text: str) -> str:
#         """Send query to agent with smart routing based on prefix"""
#         if not self.graph:
#             self.init()
        
#         # Classify query type and reformat for better tool usage
#         original_text = text
#         query_type = "general"
        
#         # Detect query type based on prefix
#         text_lower = text.lower().strip()
        
#         # Web search queries (support multiple common prefixes)
#         if text_lower.startswith(("web search:", "search:", "search web:", "web:")):
#             query_type = "web_search"
#             # Extract query after colon
#             query = text.split(":", 1)[1].strip()
#             # Be explicit to strongly bias tool usage with HF models
#             text = f"Call web_search with: {query}"
#             print(f"  Web Search Mode: '{query}'")
            
#         # Database logging queries
#         elif text_lower.startswith("log:") or text_lower.startswith("add:"):
#             query_type = "database"
#             content = text.split(":", 1)[1].strip()
            
#             # Auto-detect what type of data to log
#             if any(word in content.lower() for word in ["food", "eat", "ate", "meal", "lunch", "dinner", "breakfast", "snack"]):
#                 # Provide explicit structured args to bias HF models to call the tool
#                 text = f"Call insert_food with: {{'name': '{content}'}}"
#                 print(f"   Food Logging Mode: '{content}'")
#             elif any(word in content.lower() for word in ["medication", "medicine", "drug", "pill"]):
#                 # Very lightweight heuristic to split name/dose if present, else pass raw
#                 text = f"Call insert_medication with: {{'name': '{content}'}}"
#                 print(f"  Medication Logging Mode: '{content}'")
#             elif any(word in content.lower() for word in ["condition", "disease", "diagnosis"]):
#                 text = f"Call insert_medical_history with: {{'condition': '{content}'}}"
#                 print(f" Medical History Mode: '{content}'")
#             else:
#                 # Default to food logging when ambiguous (e.g., 'log: chicken rice')
#                 text = f"Call insert_food with: {{'name': '{content}'}}"
#                 print(f"Auto Food Logging Mode (default): '{content}'")
        
#         # Database query requests        
#         elif text_lower.startswith("show:") or text_lower.startswith("list:") or text_lower.startswith("get:"):
#             query_type = "query"
#             content = text.split(":", 1)[1].strip()
#             text = f"Use query_table or search_by_condition to retrieve: {content}"
#             print(f"Query Mode: '{content}'")
        
#         # General conversation    
#         else:
#             query_type = "general"
#             print(f"General Chat Mode")
        
#         self.history.append(HumanMessage(content=text))
        
#         # Invoke agent
#         print("Processing...")
#         result = self.graph.invoke({"messages": self.history})
#         self.history = result["messages"]
        
#         # Display tool usage information
#         tool_used = False
#         for msg in result["messages"]:
#             # Check for tool calls
#             if hasattr(msg, 'tool_calls') and msg.tool_calls:
#                 for tool_call in msg.tool_calls:
#                     tool_used = True
#                     tool_name = tool_call.get('name', 'unknown')
#                     print(f" Tool Used: {tool_name}")
#                     if 'args' in tool_call:
#                         args_str = str(tool_call['args'])[:100]
#                         print(f"      └─ Args: {args_str}...")
            
#             # Check for tool results
#             if msg.__class__.__name__ == 'ToolMessage':
#                 tool_used = True
#                 result_preview = msg.content[:150].replace('\n', ' ')
#                 print(f" Result: {result_preview}...")
        
#         if not tool_used:
#             print("  Direct Answer (no tool)")
        
#         # Extract final AI response
#         ai_msg = None
#         for m in reversed(self.history):
#             if isinstance(m, AIMessage) and m.content:
#                 ai_msg = m
#                 break
        
#         if ai_msg:
#             response = ai_msg.content
            
#             # Clean up special tokens from response
#             cleanup_patterns = [
#                 '<bos>', '<eos>', 
#                 '<start_of_turn>', '<end_of_turn>',
#                 'user\n', 'model\n', 'assistant\n', 'user', 'model'
#             ]
            
#             for pattern in cleanup_patterns:
#                 response = response.replace(pattern, '')
            
#             # Remove repetitive lines
#             lines = [l.strip() for l in response.split('\n') if l.strip()]
            
#             unique_lines = []
#             seen_count = {}
            
#             for line in lines:
#                 # Track repetitions in markdown lists
#                 if line.startswith('- **') or line.startswith('**'):
#                     seen_count[line] = seen_count.get(line, 0) + 1
#                     # Only add first occurrence
#                     if seen_count[line] == 1:
#                         unique_lines.append(line)
#                 else:
#                     unique_lines.append(line)
            
#             # Truncate if response is too long (sign of repetition loop)
#             if len(unique_lines) > 30:
#                 unique_lines = unique_lines[:30]
#                 unique_lines.append("\n[Response truncated]")
            
#             return '\n'.join(unique_lines).strip()
        
#         return "No response generated."
    
# ========= TEST ENTRY POINT =========
# if __name__ == "__main__":
#     print("🚀 Starting quick test for Health Assistant Agent...")
#     runner = AgentRunner()
#     runner.init()

#     # --- Test 4: Insert medication example ---
#     print("\n=== TEST 4: Log Medication ===")
#     print(runner.ask("add: medication amoxicillin 500mg"))

#     # --- Test 5: Web search example ---
#     # print("\n=== TEST 5: Web Search ===")
#     # print(runner.ask("web search: benefits of oatmeal for cholesterol"))

#     print("\n✅ All test flows executed.\n")
