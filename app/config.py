import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import multiprocessing

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

class Config:
    # --- Base Paths ---
    ROOT_DIR = ROOT_DIR
    DATA_DIR = ROOT_DIR / "data"
    
    # --- Storage ---
    GRAPHS_DIR = DATA_DIR / "graphs" 
    VECTOR_DIR = DATA_DIR / "vector_store"
    OUTPUTS_DIR = DATA_DIR / "outputs"
    LOG_DIR = DATA_DIR / "logs"
    
    # --- Models & Cache ---
    CACHE_DIR = DATA_DIR / "cache"
    MODELS_DIR = DATA_DIR / "models"
    os.environ["HF_HOME"] = str(MODELS_DIR)
    
    # --- AI Settings ---
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    MODEL_CHAT = os.getenv("OLLAMA_MODEL_CHAT", "mistral")
    EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
    
    # --- Performance & Limits ---
    # Use 75% of available cores, minimum 1
    NUM_WORKERS = max(1, int(multiprocessing.cpu_count() * 0.75))
    STATIC_RENDER_THRESHOLD = 2000 # <<< NEW: Threshold to trigger static image rendering
    
    # Directories to ignore completely to save time
    IGNORE_DIRS = {
        '.git', '.svn', '.hg', '.idea', '.vscode', 
        'node_modules', 'venv', '.venv', 'env', 
        'dist', 'build', 'target', 'bin', 'obj',
        'vendor', 'third_party', 'cmake-build-debug',
        '__pycache__'
    }
    
    # Extensions to analyze
    ALLOWED_EXTENSIONS = {
        '.c', '.h', '.cpp', '.hpp', '.cc', '.cxx', 
        '.py', '.pyw', 
        '.js', '.ts', '.jsx', '.tsx', 
        '.java', '.kt', 
        '.rs', '.go', 
        '.lua'
    }

    try:
        OLLAMA_NUM_GPU = int(os.getenv("OLLAMA_NUM_GPU", "0"))
        OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "4096"))
    except ValueError:
        OLLAMA_NUM_GPU = 0
        OLLAMA_NUM_CTX = 4096

    @classmethod
    def ensure_dirs(cls):
        for d in [cls.DATA_DIR, cls.GRAPHS_DIR, cls.VECTOR_DIR, cls.OUTPUTS_DIR, cls.LOG_DIR, cls.CACHE_DIR, cls.MODELS_DIR]:
            d.mkdir(parents=True, exist_ok=True)

Config.ensure_dirs()
