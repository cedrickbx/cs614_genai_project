# file: test_tools.py
import json
from tools import find_exact_interaction, find_similar_interaction

# -----------------------------------------------------------------------------
# 1️⃣ Define test inputs
# -----------------------------------------------------------------------------
# Example 1: Known existing pair (you can change to a known pair in your DB)
food = "grapefruit"
drug = "paclitaxel"

# Example 2: Non-existing pair (to test fallback behavior)
food_no = "banana"
drug_no = "ibuprofen"

# -----------------------------------------------------------------------------
# 2️⃣ Run Exact Interaction Tool
# -----------------------------------------------------------------------------
print("\n==============================")
print("🔍 TEST 1: find_exact_interaction")
print("==============================")

input_json = json.dumps({"food": food, "drug": drug})
result_exact = find_exact_interaction.run(input_json)  # ✅ use .run() for LangChain tool
print(result_exact)

# -----------------------------------------------------------------------------
# 3️⃣ Run Similar Interaction Tool
# -----------------------------------------------------------------------------
print("\n==============================")
print("🤖 TEST 2: find_similar_interaction")
print("==============================")

input_json = json.dumps({"food": food, "drug": drug})
result_similar = find_similar_interaction.run(input_json)
print(result_similar)

# -----------------------------------------------------------------------------
# 4️⃣ Optional: test a pair that doesn’t exist (to trigger the fallback)
# -----------------------------------------------------------------------------
print("\n==============================")
print("🧩 TEST 3: Non-existing pair (should return no exact match)")
print("==============================")

input_json_no = json.dumps({"food": food_no, "drug": drug_no})
result_exact_no = find_exact_interaction.run(input_json_no)
print(result_exact_no)

if "❌" in result_exact_no:
    print("\n⚡ Triggering similar search since exact match failed...")
    result_similar_no = find_similar_interaction.run(input_json_no)
    print(result_similar_no)
