"""Configuration for the RAG system."""

import os
import re
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
TRANSCRIPTS_V1_DIR = DATA_DIR / "generated_transcripts_v1"
TRANSCRIPTS_DIR = DATA_DIR / "generated_transcripts"
TRANSCRIPT_TEXT_DIR = DATA_DIR / "transcript_text"
VECTOR_DB_DIR = DATA_DIR / "vector_db"  # Legacy unversioned directory

# RAG Versioning Configuration
RAG_VERSION = "1.0.0"

# Regex for valid semver RAG directories (rag-v{major}.{minor}.{patch})
RAG_VERSION_PATTERN = re.compile(r"^rag-v(\d+)\.(\d+)\.(\d+)$")


def _parse_version(dirname: str) -> Optional[Tuple[int, int, int]]:
    """Parse directory name into semver tuple for sorting.

    Returns:
        Tuple of (major, minor, patch) or None if not a valid version.
    """
    match = RAG_VERSION_PATTERN.match(dirname)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None


def get_rag_dir(version: Optional[str] = None) -> Path:
    """Get the RAG index directory for a given version.

    Args:
        version: RAG version string (e.g., "1.0.0") or "legacy" for unversioned.
                 If None, returns latest version or falls back to legacy.

    Returns:
        Path to the RAG index directory
    """
    # Special case: explicit legacy request
    if version == "legacy":
        return VECTOR_DB_DIR

    if version:
        return DATA_DIR / f"rag-v{version}"

    # Find latest versioned index (only valid semver directories)
    versioned_dirs = []
    for d in DATA_DIR.glob("rag-v*"):
        parsed = _parse_version(d.name)
        if parsed:
            versioned_dirs.append((parsed, d))

    # Sort by semver (descending) and return the latest
    if versioned_dirs:
        versioned_dirs.sort(key=lambda x: x[0], reverse=True)
        return versioned_dirs[0][1]

    # Fallback to legacy unversioned directory
    return VECTOR_DB_DIR


# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_TEST_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o-mini"

# Anthropic Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = "claude-3-5-haiku-20241022"  # Default Claude model
CLAUDE_MODEL_SONNET = "claude-3-5-sonnet-20241022"  # For complex queries

# Chunking Configuration
CHUNK_SIZE = 512  # tokens
CHUNK_OVERLAP = 128  # tokens

# Retrieval Configuration
DEFAULT_TOP_K = 5
MAX_CONTEXT_TOKENS = 6000

# Rate Limiting (for embedding generation)
EMBEDDING_BATCH_SIZE = 100
EMBEDDING_RPS = 3  # requests per second
