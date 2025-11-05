import sys
# torch import moved to lazy loading in _create_embedding_model() to handle architecture mismatches
from sqlalchemy import create_engine, text
from langchain_ollama import ChatOllama, OllamaEmbeddings
from food_drug_interaction_agent import config
import chromadb
from langchain_chroma import Chroma

# 3. THIS IS THE NEW LLM FUNCTION
def _create_llm():
    """Loads the llama3.1:8b model from Ollama using ChatOllama."""
    model_name = "qwen3:8b"
    print(f"Loading LLM from Ollama: {model_name}...")
    print("Make sure the Ollama application is running!")
    
    try:
        # # Use ChatOllama for tool/function calling support
        llm = ChatOllama(
            model=model_name,
            temperature=0,  # Low temp for more consistent tool calling
            num_ctx=12000,      # bigger context window
            num_predict=1500,   # allow long answers
        )
   
        # Test the connection and model
        response = llm.invoke("Hello")
        print(f"✅ LLM loaded successfully: {model_name}")
        print(f"   Test response: {response.content[:50]}...")
        return llm
    
    except Exception as e:
        print(f"❌ Error loading LLM from Ollama: {e}")
        print(f"Please make sure Ollama is running and you have pulled the model.")
        print(f"Install the model with: ollama pull {model_name}")
        print(f"\nIf you're getting 'No module named langchain_ollama', install it with:")
        print(f"  pip install langchain-ollama")
        sys.exit(1)

def _create_embedding_model():
    """
    Loads Ollama embeddings (nomic-embed-text) - No PyTorch required.
    Works with Python 3.13 and doesn't need PyTorch.
    """
    print(f"Loading embedding model: nomic-embed-text (Ollama)...")
    print("Make sure Ollama is running!")
    
    try:
        embeddings = OllamaEmbeddings(
            model="nomic-embed-text",
            # num_predict=512,  # Optional: limit output tokens
        )
        
        # Test the embedding model
        test_text = "test embedding"
        test_embedding = embeddings.embed_query(test_text)
        print(f"✅ Embedding model loaded successfully")
        print(f"   Model: nomic-embed-text (Ollama)")
        print(f"   Backend: Ollama (no PyTorch required)")
        print(f"   Embedding dimension: {len(test_embedding)}")
        print(f"   ✅ Works on any Python version (3.10+)")
        return embeddings
    except Exception as e:
        print(f"\n❌ ERROR: Failed to load Ollama embeddings: {e}")
        print(f"\n   Please ensure:")
        print(f"   1. Ollama is installed and running")
        print(f"   2. The model is available: ollama pull nomic-embed-text")
        print(f"   3. langchain-ollama is installed: pip install langchain-ollama\n")
        sys.exit(1)

def _create_db_engine():
    """Creates and returns a SQLAlchemy engine."""
    print("Connecting to database...")
    try:
        engine = create_engine(config.DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database connection successful.")
        return engine
    except Exception as e:
        print(f"Error connecting to database at {config.DATABASE_URL}: {e}")
        print("Please check your .env file, password, and MySQL server status.")
        sys.exit(1)

def _create_vector_store():
    """Loads the persistent Chroma vector store."""
    print(f"Loading vector store from: {config.CHROMA_PATH}")
    try:
        # Connect to the persistent Chroma client
        client = chromadb.PersistentClient(path=config.CHROMA_PATH)
        
        # Wrap it with the LangChain adapter, using our embedding model
        vector_store = Chroma(
            client=client,
            collection_name=config.COLLECTION_NAME,
            embedding_function=embedding_model # Use the model we already loaded
        )
        count = vector_store._collection.count()
        print(f"✅ Vector store loaded successfully")
        print(f"   Collection: {config.COLLECTION_NAME}")
        print(f"   Items in store: {count}")
        return vector_store
    except (OSError, ImportError) as e:
        # Handle architecture mismatch or missing chromadb dependencies
        error_str = str(e)
        if "incompatible architecture" in error_str or "chromadb" in error_str.lower():
            print(f"⚠️  Warning: ChromaDB has architecture mismatch: {error_str[:150]}...")
            print("   Vector search features will be unavailable.")
            print("   To fix: Reinstall chromadb for x86_64 architecture or use ARM64 Python.")
            return None
        raise
    except Exception as e:
        print(f"Error loading vector store: {e}")
        print("🚨 IMPORTANT: Did you run the `build_index.py` script first?")
        print("   Vector search features will be unavailable.")
        return None  # Return None instead of sys.exit() to allow graceful degradation

# These are loaded once when the first import happens
print("\n" + "="*60)
print("Initializing Food-Drug Interaction Agent Components")
print("="*60 + "\n")

llm = _create_llm()
print()
embedding_model = _create_embedding_model()
print()
db_engine = _create_db_engine()
print()
# Only create vector store if embedding model is available
vector_store = _create_vector_store() if embedding_model is not None else None
if vector_store:
    print()

print("="*60)
print("✅ All components initialized successfully!")
print("="*60 + "\n")
