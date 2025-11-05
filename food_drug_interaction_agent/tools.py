# file: tools.py

import json
from sqlalchemy import bindparam, text
from langchain_core.tools import tool
from pydantic import BaseModel, Field # <-- Import from Pydantic v2

# Import the singleton instances from utils
from food_drug_interaction_agent.utils import db_engine, vector_store

# --- We keep this schema for validation INSIDE the tool ---
class InteractionInput(BaseModel):
    food: str = Field(description="The food item, e.g., 'grapefruit'")
    drug: str = Field(description="The drug item, e.g., 'paclitaxel'")

# --- TOOL 1 ---
@tool
def find_exact_interaction(tool_input: str) -> str:
    """
    Finds the *exact* interaction document for a specific food and drug pair.
    Use this tool first.
    The input MUST be a JSON string with 'food' and 'drug' keys.
    Example input: {{"food": "grapefruit", "drug": "paclitaxel"}}
    """
    print(f"--- Calling Tool: find_exact_interaction ---")
    try:
        # 1. Manually parse the JSON string input
        input_data = json.loads(tool_input)
        # 2. Manually validate with Pydantic
        validated_input = InteractionInput(**input_data)
        food = validated_input.food
        drug = validated_input.drug
    except Exception as e:
        return f"❌ Input Error: {e}. Input must be a valid JSON string with 'food' and 'drug' keys."

    print(f"   (Parsed inputs: food='{food}', drug='{drug}')")
    
    query = text("""
        SELECT T2.document
        FROM FinalFooDrugs_v4.TM_interactions AS T1
        JOIN FinalFooDrugs_v4.texts AS T2 ON T1.texts_ID = T2.texts_ID
        WHERE lower(T1.food) = :food AND lower(T1.drug) = :drug
        LIMIT 1
        """
    )

    result = None

    with db_engine.connect() as conn:
        result = conn.execute(
            query, 
            {"food": food.lower(), "drug": drug.lower()}
        ).fetchone()
        
        print(f"Query result: {result}")
        if result and result[0]:
            print("if is executed!")
            # Convert to string explicitly to handle any type issues
            document_text = str(result[0])
            return f"✅ Found exact interaction:\n\n{document_text}"
        else:
            print("else is executed!")
            return "❌ No exact match found. You should try finding a similar interaction next."

# --- TOOL 2 (WITH THE FIX) ---
@tool
def find_similar_interaction(tool_input: str) -> str:
    """
    Finds the *most semantically similar* interaction from the vector database.
    Only use this if `find_exact_interaction` fails.
    The input MUST be a JSON string with 'food' and 'drug' keys.
    Example input: {{"food": "grapefruit", "drug": "paclitaxel"}}
    """
    print(f"--- Calling Tool: find_similar_interaction ---")
    try:
        input_data = json.loads(tool_input)
        validated_input = InteractionInput(**input_data)
        food = validated_input.food
        drug = validated_input.drug
    except Exception as e:
        return f"❌ Input Error: {e}. Input must be a valid JSON string with 'food' and 'drug' keys."

    print(f"   (Parsed inputs: food='{food}', drug='{drug}')")

    query_text = f"{food} and {drug}"
    k_results = 3
    print(f"... ⚡ Querying vector store for top {k_results} matches for: '{query_text}'")

    if vector_store is None:
        return "❌ Vector store is not available. This may be due to ChromaDB architecture mismatch or missing setup."

    try:
        similar_docs = vector_store.similarity_search_with_score(query=query_text, k=k_results)
        
        if not similar_docs:
            return "❌ No similar interactions found in the vector database."
        
        texts_id_list = []
        metadata_by_id = {}
        for doc, score in similar_docs:
            texts_id_str = doc.metadata.get("texts_ID") # Get ID as string
            if texts_id_str :
                
                # --- THIS IS THE FIX ---
                # Convert the string ID (e.g., "123") to an integer (e.g., 123)
                texts_id = int(texts_id_str)
                # --- END OF FIX ---
                
                texts_id_list.append(texts_id) # Append the int
                metadata_by_id[texts_id] = {   # Use the int as the key
                    "food": doc.metadata.get("food"),
                    "drug": doc.metadata.get("drug"),
                    "score": score
                }

        if not texts_id_list:
            return "❌ Error: Vector search found matches but they had no texts_ID metadata."
        
        # ✅ Corrected query with expanding parameter
        doc_query = text("""
            SELECT texts_ID, document 
            FROM FinalFooDrugs_v4.texts
            WHERE texts_ID IN :texts_ids
        """).bindparams(bindparam("texts_ids", expanding=True))

        documents_by_id = {}
        with db_engine.connect() as conn:
            # texts_id_list is now a list of ints, so tuple() is correct
            doc_results = conn.execute(doc_query, {"texts_ids": tuple(texts_id_list)}).fetchall()
            for id, doc_text in doc_results:
                documents_by_id[id] = doc_text

        response_parts = [
            f"⚠️ No exact match found for '{food} and {drug}'.\n"
            f"Showing the top {len(documents_by_id)} semantic matches found:\n"
        ]
        
        result_num = 3
        for texts_id in texts_id_list:
            doc_text = documents_by_id.get(texts_id) # Get by int key
            meta = metadata_by_id.get(texts_id)       # Get by int key
            
            if doc_text and meta:
                response_parts.append(
                    f"\n--- Result {result_num} ---\n"
                    f"Match: '{meta['food']} and {meta['drug']}' (Similarity Score: {meta['score']:.4f})\n"
                    f"Document: {doc_text}\n"
                )
                result_num += 1
        return "".join(response_parts)
        
    except Exception as e:
        print(f"An error occurred during vector search: {e}")
        return "❌ An error occurred while searching for similar interactions."
