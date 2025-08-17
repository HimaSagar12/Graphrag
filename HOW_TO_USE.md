# How to Use the GraphRAG Code Understanding Project

This document provides instructions on how to set up and run the local GraphRAG system for code understanding.

## Project Overview

This project demonstrates a basic GraphRAG (Graph-based Retrieval Augmented Generation) system for code understanding. It parses Python code, builds an in-memory graph using NetworkX, and allows you to ask natural language-like questions about the codebase structure and relationships. The system then retrieves relevant context from the graph, which can be used to augment an LLM for generating answers.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

*   **Python 3.8+** and `pip`
*   **Graphviz** (for visualizing the code flow graph). You can download it from [graphviz.org/download/](https://graphviz.org/download/) or install via your system's package manager (e.g., `sudo apt-get install graphviz` on Debian/Ubuntu, `brew install graphviz` on macOS).
*   **In-house `horizon` library:** This project uses an in-house library called `horizon` to interact with the LLM. Please ensure that this library is installed in your environment.

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

## Running the Project

This project has two main interfaces: a command-line interface (CLI) and a Streamlit web UI. The Streamlit UI provides all the functionality of the CLI in a more interactive way.

### Running the Streamlit Web UI (Recommended)

The Streamlit UI is the recommended way to interact with this project. It provides a visual representation of the code graph and allows you to query the codebase using natural language.

1.  **Run the Streamlit app:**

    To start the web application, run the following command in your terminal:
    ```bash
    streamlit run app.py
    ```

    This will open a new tab in your web browser with the application.

2.  **Using the App:**

    -   Click on the "Browse files" button to upload one or more Python files from your local system.
    -   Once the files are uploaded, the app will automatically analyze the code and display the code graph and a mark map.
    -   You can enter your questions about the code in the text box and click "Submit Query".
    -   The results of your query will be displayed below the input box.
    -   You can download the graph as a standard HTML file using the "Download Graph as HTML" button.
    -   You can also download the graph as an interactive mind map using the "Download as Mark Map" button.

### Generate Function Comments

The Streamlit UI also includes a feature to automatically generate comments for your functions using your in-house LLM.

1.  **Generate Comments:**

    Click the "Generate Comments" button. The application will then:
    -   Read the functions from your uploaded code.
    -   Use the `HorizonLLMClient` to generate a comment for each function.
    -   Display the original code and the code with the new comments side-by-side for you to review.

2.  **Apply Comments and Update Visualizations:**

    If you are satisfied with the generated comments, click the "Apply Comments and Update Visualizations" button. This will update the code with the new comments and regenerate the code graph and mark map visualizations.

3.  **Download Modified Files:**

    After applying the comments, you can download all the modified files as a single zip archive by clicking the "Download All Modified Files as ZIP" button.

### Running the Command-Line Interface (CLI)

The CLI provides a way to interact with the query engine from your terminal.

1.  **Run the CLI application:**
    ```bash
    python src/cli/main.py
    ```

2.  **Interacting with the CLI:**

    After running the `main.py` script, the system will build the code graph and then prompt you to ask questions. You can type queries like:

    *   `functions in example_module.py`
    *   `callers of main`
    *   `details of greet`
    *   `called by main`
    *   `readers of <variable_name>`
    *   `writers of <variable_name>`
    *   `throwers`
    *   `handlers`
    *   `decorated by <decorator_name>`
    *   `returners`
    *   `uses <service_name>` (e.g., `uses snowflake`)

    The system will respond with retrieved information from the graph. It will also show you the `retrieved_context` that would typically be sent to an LLM for further processing.

    To exit the application, type `exit` and press Enter.

## Generating Code Flow Visualizations (DOT Graph)

To generate a visual representation of the code's flow and dependencies:

1.  **Run the CLI application** as described above.
2.  At the prompt, type:
    ```
    generate dot
    ```
    This will create a file named `code_flow.dot` in the root of your project directory.

3.  **Render the DOT file to an image** using Graphviz. Open your terminal in the project's root directory and run:
    ```bash
    dot -Tpng code_flow.dot -o code_flow.png
    ```
    This command will generate a PNG image (`code_flow.png`) showing the code's structure and call relationships. You can change `-Tpng` to other formats like `-Tsvg` for SVG output.

## Codebase Example

The project includes small example Python codebases in the `codebase_example/` directory (`example_module.py`, `snowflake_example.py`) that the system will parse and analyze by default. You can modify these files or add more Python files to the `codebase_example/` directory to test the system with different code structures.