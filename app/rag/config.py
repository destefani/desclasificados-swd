"""Configuration for the RAG system."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
TRANSCRIPTS_V1_DIR = DATA_DIR / "generated_transcripts_v1"
TRANSCRIPTS_DIR = DATA_DIR / "generated_transcripts"
TRANSCRIPT_TEXT_DIR = DATA_DIR / "transcript_text"
VECTOR_DB_DIR = DATA_DIR / "vector_db"

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_TEST_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o-mini"

# Chunking Configuration
CHUNK_SIZE = 512  # tokens
CHUNK_OVERLAP = 128  # tokens

# Retrieval Configuration
DEFAULT_TOP_K = 5
MAX_CONTEXT_TOKENS = 6000

# Rate Limiting (for embedding generation)
EMBEDDING_BATCH_SIZE = 100
EMBEDDING_RPS = 3  # requests per second
