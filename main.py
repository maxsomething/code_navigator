import sys
import logging
import requests
from PyQt6.QtWidgets import QApplication, QMessageBox
from app.config import Config
from app.gui.main_window import MainWindow

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(Config.LOG_DIR / "app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Main")

def run_diagnostics():
    """
    Performs startup checks and returns a list of results.
    """
    results = []

    # 1. Check Ollama Connection
    try:
        response = requests.get(f"{Config.OLLAMA_HOST}/api/tags", timeout=2)
        if response.status_code == 200:
            results.append({"name": "Ollama Connection", "status": "ok", "message": f"Connected to {Config.OLLAMA_HOST}"})
            
            models = [m['name'] for m in response.json().get('models', [])]
            found_chat = any(Config.MODEL_CHAT in m for m in models)
            
            if found_chat:
                results.append({"name": f"Model: {Config.MODEL_CHAT}", "status": "ok", "message": "Model found."})
            else:
                results.append({"name": f"Model: {Config.MODEL_CHAT}", "status": "warning", 
                                "message": f"Model not found. Try running: ollama pull {Config.MODEL_CHAT}"})
        else:
            results.append({"name": "Ollama Connection", "status": "error", "message": f"API returned {response.status_code}"})
    except Exception as e:
        results.append({"name": "Ollama Connection", "status": "error", "message": f"Could not connect: {e}. Is Ollama running?"})

    # 2. Check Tree-sitter (Relaxed Check)
    try:
        # We only need to ensure the core libraries can be imported.
        # The parser itself will handle API version differences.
        import tree_sitter
        import tree_sitter_c
        results.append({"name": "Tree-Sitter Library", "status": "ok", "message": "Core library loaded."})
    except ImportError as e:
        results.append({"name": "Tree-Sitter Library", "status": "error", "message": f"Missing dependency: {e}. Please run 'pip install -r requirements.txt'."})

    # 3. Check Sentence Transformers
    try:
        import sentence_transformers
        results.append({"name": "Embedding Engine", "status": "ok", "message": "Sentence-transformers loaded."})
    except ImportError:
        results.append({"name": "Embedding Engine", "status": "warning", 
                        "message": "sentence-transformers not found. RAG will be disabled."})

    return results

def main():
    logger.info("Starting Code_Navigator...")
    
    app = QApplication(sys.argv)
    app.setApplicationName("Code_Navigator")
    
    diagnostic_results = run_diagnostics()
    
    has_critical_error = any(check['status'] == 'error' for check in diagnostic_results)

    if has_critical_error:
        logger.critical("Critical error detected during startup diagnostics. Application will not launch.")
        error_messages = "\n".join(
            f"- {check['name']}: {check['message']}" 
            for check in diagnostic_results if check['status'] == 'error'
        )
        QMessageBox.critical(None, "Startup Failed", 
            "A critical error was detected and the application cannot start.\n"
            "Please fix the following issues:\n\n"
            f"{error_messages}"
        )
        sys.exit(1)
    
    for check in diagnostic_results:
        if check['status'] == 'warning':
            logger.warning(f"Startup Check Warning: {check['name']} - {check['message']}")

    window = MainWindow(diagnostics=diagnostic_results)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()