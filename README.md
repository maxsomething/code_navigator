# Code_Navigator

**Code_Navigator** is a local, offline-first tool designed to help developers navigate, analyze, and understand complex codebases. It excels with polyglot projects by building interactive dependency graphs and leveraging local Large Language Models (LLMs) to answer high-level questions about your code's architecture and logic, all without your data ever leaving your machine.

It combines robust static analysis with a powerful AI context-retrieval system to provide deep insights into how your project works.

## Features

*   **Multi-Layered Graph Analysis**: Visualize your project from different perspectives:
    *   **File Structure Graph**: A classic tree view of directories and files.
    *   **Logic Dependency Graph**: Maps actual code dependencies (`#include`, `import`, `require`, etc.) to reveal architectural connections.
    *   **Scope Graph**: A detailed view focused only on files you select, showing inter-file dependencies and internal definitions (functions/classes).

*   **Smart Visualization Engine**:
    *   **Interactive Mode**: Dynamic, physics-based graphs for standard analysis.
    *   **Static Rendering**: Automatically generates high-resolution (up to 12k), zoomable static images for massive graphs to ensure performance.
    *   **Smart View**: Automatically switches back to interactive mode for small subsets (≤ 50 nodes) to enable rich tooltips, even if the parent graph is massive.

*   **Rich Scope Analysis**:
    *   **Interactive Tooltips**: Hover over files in the Scope Graph to see a summary of internal functions, classes, and signatures.
    *   **Direct Scope Management**: Instantly search and add files to your active scope using the Quick Scope panel.
    *   **Extrapolation**: Automatically pull in upstream (callers) and downstream (callees) dependencies for any file.

*   **Intelligent AI Chat (RAG)**:
    *   **Context Toggles**: Granular control over what data is sent to the AI (File Content, Logic Map, Scope Definitions) to manage token usage.
    *   **Strict Budgeting**: Intelligent truncation ensures the AI answers quickly without hitting context limits.
    *   **Actionable Responses**: The AI can automatically manipulate your active scope based on the conversation.

*   **Polyglot Parsing**: Uses **Tree-sitter** to accurately parse a wide range of languages: C, C++, Python, Java, Lua, Rust, and JavaScript.

*   **Offline First & Private**: Runs entirely on your local machine using **Ollama**. Your code never leaves your computer.

## Installation

### Prerequisites
*   A Linux-based OS (Arch Linux is the primary target)
*   Python 3.10+
*   An NVIDIA GPU is recommended for AI performance.

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/code_navigator.git
    cd code_navigator
    ```

2.  **Set up the Python Environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Install System Dependencies:**
    This tool relies on a running **Ollama** instance and **Qt6**.
    *   On Arch Linux:
        ```bash
        sudo pacman -S ollama qt6-base qt6-webengine
        ```

4.  **Pull AI Models:**
    Ensure you have the models specified in your `.env` file (default is `mistral`) available in Ollama.
    ```bash
    ollama pull mistral
    # Embedding models (sentence-transformers) will be downloaded automatically on first run.
    ```

## Usage

1.  **Start Ollama:**
    ```bash
    systemctl start ollama
    ```

2.  **Launch the Application:**
    ```bash
    source .venv/bin/activate
    python main.py
    ```

### Recommended Workflow

1.  **Open Project**: Use `File > Open Project...` to select your codebase root.
2.  **Scan & Map**: Click **"1. Scan Files"** then **"2. Map Dependencies"**. This parses your code to build the foundational graphs.
3.  **Explore**: Use the dropdown to switch between "File Tree" and "Dependency (Logic)" modes.
4.  **Define Scope**:
    *   Use the **Quick Scope** panel (bottom right) to search for specific files.
    *   Double-click to add them to your **Active Scope**.
    *   Use **Extrapolate Scope** to grab related dependencies.
5.  **Process Scope**: Click **"3. Process Scope"**. This builds a detailed graph of just your selected files, including function signatures and call links.
    *   *Tip:* Hover over nodes in the Scope graph to see a list of functions inside that file.
6.  **Chat with AI**: Ask questions like "How does the login flow work?". Use the checkboxes (File, Logic, Scope) to control what context the AI sees.

## Project Structure

```text
.
├── .venv/                 # Python Virtual Environment
├── app/                   # Application Source Code
│   ├── gui/               # UI Components (PyQt6)
│   │   ├── chat_widget.py
│   │   ├── graph_widget.py
│   │   ├── main_window.py
│   │   └── ...
│   ├── parsers/           # Tree-sitter Language Adapters
│   ├── services/          # Business Logic & Analysis
│   │   ├── analyzers/     # Graph Builders (File, Logic, Scope)
│   │   ├── llm_interface.py
│   │   ├── project_analyzer.py
│   │   └── ...
│   └── config.py
├── data/                  # Generated Data (GitIgnore this folder)
│   ├── cache/             # Temp files
│   ├── graphs/            # Serialized Graphs (.pkl) & Static Images (.png)
│   ├── logs/              # Application logs
│   ├── models/            # Downloaded Embedding Models
│   └── vector_store/      # RAG Vector Database
├── main.py                # Entry Point
├── requirements.txt
└── .env                   # Configuration