import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

# Model CONFIGURATION
LLM_MODEL_ID = "qwen3:8b"
EMBEDDING_MODEL_ID = "nomic-embed-text"

# Database CONFIGURATION
DB_USER = "root"
DB_HOST = "localhost"
DB_PORT = "3306"
DB_NAME = "FinalFooDrugs_v4" # From your first set of images
DB_PASSWORD = os.getenv("MYSQL_PASSWORD")

# Retrieve password securely
DB_PASSWORD = os.getenv("MYSQL_PASSWORD")
if not DB_PASSWORD:
    raise ValueError("❌ MYSQL_PASSWORD not set in .env file. Please add it to your .env.")

# ✅ URL-encode the password to handle '@', '#', etc.
DB_PASSWORD_ENCODED = quote_plus(DB_PASSWORD)

# ✅ Build SQLAlchemy connection string
DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD_ENCODED}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- Vector Store Configuration ---
CHROMA_PATH = "./chroma_db_store"
COLLECTION_NAME = "food_drug_interactions"