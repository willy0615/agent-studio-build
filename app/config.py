import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env
load_dotenv(Path(__file__).parent.parent / ".env")

# NVIDIA NIM Config
# Priority: System env > .env file > empty
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")

if not NVIDIA_API_KEY:
    print("WARNING: NVIDIA_API_KEY not set. Please set it in:")
    print("  1. System environment variable: NVIDIA_API_KEY")
    print("  2. .env file (copy .env.example and fill in your key)")

NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "deepseek-ai/deepseek-v4-flash")

# Available models
AVAILABLE_MODELS = {
    "DeepSeek V4 Flash": "deepseek-ai/deepseek-v4-flash",
    "DeepSeek V4 Pro": "deepseek-ai/deepseek-v4-pro",
    "GLM 5.1": "z-ai/glm-5.1",
    "MiniMax M2.7": "minimax/minimax-m2-7b",
    "Gemma 4 31B": "google/gemma-4-31b",
    "Nemotron 3 120B": "nvidia/nemotron-3-120b",
}

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
KNOWLEDGE_BASE_DIR = DATA_DIR / "knowledge_base"
MEMORY_DIR = DATA_DIR / "memory"
CHROMA_DIR = DATA_DIR / "chroma_db"

# Ensure dirs exist
for d in [DATA_DIR, KNOWLEDGE_BASE_DIR, MEMORY_DIR, CHROMA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Code execution config
CODE_EXEC_TIMEOUT = 30  # seconds
