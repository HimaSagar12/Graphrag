# How to Use the GraphRAG Code Understanding Project

This document provides instructions on how to set up and run the local GraphRAG system for code understanding.

## Project Overview

This project demonstrates a basic GraphRAG (Graph-based Retrieval Augmented Generation) system for code understanding. It parses Python code, builds an in-memory graph using NetworkX, and allows you to ask natural language-like questions about the codebase structure and relationships. The system then retrieves relevant context from the graph, which can be used to augment an LLM (like Groq) for generating answers.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

*   **Python 3.8+** and `pip`

## Setup Instructions

1.  **Navigate to the project directory:**

    Open your terminal or command prompt and change to the `graph_rag_code_understanding` directory:
    ```bash
    cd /data/data/com.termux/files/home/graph_rag_code_understanding
    ```

2.  **Install Python dependencies:**

    Install the required Python packages using `pip`:
    ```bash
    pip install -r requirements.txt
    ```

3.  **(Optional) Configure Groq API Key:**

    If you plan to integrate with Groq, open the `src/cli/main.py` file and replace the placeholder with your actual Groq API Key:
    ```python
    # src/cli/main.py
    GROQ_API_KEY = "YOUR_GROQ_API_KEY_HERE" # Replace this with your actual key
    ```

## Running the Project

Once the setup is complete, you can run the command-line interface (CLI) application:

```bash
python src/cli/main.py
```

## Interacting with the CLI

After running the `main.py` script, the system will build the code graph and then prompt you to ask questions. You can type queries like:

*   `functions in example_module.py`
*   `callers of main`
*   `details of greet`
*   `called by main`

The system will respond with retrieved information from the graph. It will also show you the `retrieved_context` that would typically be sent to an LLM for further processing.

To exit the application, type `exit` and press Enter.

## Codebase Example

The project includes a small example Python codebase in the `codebase_example/` directory (`example_module.py`) that the system will parse and analyze by default. You can modify this file or add more Python files to the `codebase_example/` directory to test the system with different code structures.
