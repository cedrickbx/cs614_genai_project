import sys
import chromadb
from sqlalchemy.sql import text
# This imports the models/DB from your existing utils
import utils 
import config

# --- Configuration ---
BATCH_SIZE = 1000 # Process 1000 records at a time

def main():
    print("--- 🚀 Starting Vector Index Build ---")

    # --- Step 1: Connect to ChromaDB ---
    try:
        client = chromadb.PersistentClient(path=config.CHROMA_PATH)
        collection = client.get_or_create_collection(name=config.COLLECTION_NAME)
        print(f"ChromaDB client connected. Collection '{config.COLLECTION_NAME}' ready.")
    except Exception as e:
        print(f"Error connecting to ChromaDB: {e}")
        sys.exit(1)

    # 2. Connect to MySQL
    print("Connecting to MySQL to fetch records...")
    db = utils.db_engine

    total_rows_query = text("SELECT COUNT(DISTINCT food, drug) FROM FinalFooDrugs_v4.TM_interactions")
    all_pairs_query = text("""
        SELECT T1.food, T1.drug, T1.texts_ID
        FROM FinalFooDrugs_v4.TM_interactions AS T1
        GROUP BY T1.food, T1.drug, T1.texts_ID 
        """) # Using GROUP BY to ensure distinct pairs + their ID
    
    try:
        with db.connect() as conn:
            total_rows_result = conn.execute(total_rows_query).fetchone()
            total_rows = total_rows_result[0]
            print(f"Total distinct (food, drug) pairs to process: {total_rows}")

            # Use a server-side cursor to stream results
            streamed_results = conn.execution_options(stream_results=True).execute(all_pairs_query)

            batch_num = 1
            while True:
                print(f"--- Processing batch {batch_num} ---")
                rows = streamed_results.fetchmany(BATCH_SIZE)
                if not rows:
                    print("All batches processed.")
                    break

                # --- Prepare batch data ---
                documents = []  # The text to be embedded (e.g., "grapefruit and abemaciclib")
                metadatas = []  # Extra info (e.g., the text content ID)
                ids = []        # Unique ID for Chroma (e.g., "grapefruit_abemaciclib_1")

                for row in rows:
                    food, drug, texts_id = row[0], row[1], row[2]
                    doc_text = f"{food} and {drug}"
                    # Create a unique ID
                    unique_id = f"{food}_{drug}_{texts_id}"

                    documents.append(doc_text)
                    metadatas.append({"food": food, "drug": drug, "texts_ID": str(texts_id)})
                    ids.append(unique_id)
    
                # 3. Embed and Add to Chroma
                print(f"Embedding {len(documents)} records...")
                embeddings = utils.embedding_model.embed_documents(documents)

                print(f"Adding {len(documents)} to Chroma collection...")
                try:
                    collection.add(
                        embeddings=embeddings,
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                except chromadb.errors.IDAlreadyExistsError:
                    print("Some IDs already exist, skipping them (upserting).")
                    collection.upsert(
                        embeddings=embeddings,
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )

                batch_num += 1

    except Exception as e:
        print(f"An error occurred during indexing: {e}")

    print("\n--- ✅ Vector Index Build Complete ---")
    print(f"Data is stored in: {config.CHROMA_PATH}")
    print(f"Total items in collection: {collection.count()}")

if __name__ == "__main__":
    # We must import utils first to load the models
    try:
        if not utils.embedding_model:
             raise Exception("Embedding model not loaded.")
    except Exception as e:
        print(f"Failed to initialize components: {e}")
        sys.exit(1)
        
    main()