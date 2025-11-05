import sys

def main():
    print("\n--- Food–Drug Interaction Agent is Ready ---")
    print("Type 'exit' to quit.")
    
    # Now test the agent
    print("\n" + "="*70)
    print("🤖 TESTING AGENT")
    print("="*70)
    
    from agent_setup import agent
    
    # --- Test Case 1 ---
    query1 = "How is the interaction between food grapefruit and drug paclitaxel"
    print(f"\n[Test 1] Query: {query1}\n")
    
    try:
        # Call the LangGraph agent
        response1 = agent.invoke({"input": query1})
        
        # Debug: Print the raw response
        print("\n" + "="*70)
        print("🔍 DEBUG: Raw Response")
        print("="*70)
        print(f"Type: {type(response1)}")
        print(f"Content: {response1}")
        
        if isinstance(response1, dict):
            print(f"Keys: {response1.keys()}")
            for key, value in response1.items():
                print(f"  {key}: {type(value)} = {str(value)[:200]}...")
        
        # Extract final answer from LangGraph response
        output1 = response1.get("final_answer", "No answer generated")
        
        print("\n" + "="*70)
        print("✅ [Test 1] Final Answer:")
        print("="*70)
        print(output1)
        
    except Exception as e:
        print(f"\n❌ Agent invocation failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
if __name__ == "__main__":
    main()