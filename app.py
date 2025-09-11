import streamlit as st
import os
import sys
import tempfile
import json
import streamlit.components.v1 as components
from src.parser.python_parser import PythonCodeParser
from src.graph.graph_builder import GraphBuilder
from src.query_engine.query_engine import QueryEngine
from src.graph.dot_generator import DotGenerator
from src.diff_viewer.diff_viewer import CodeDiffViewer
from horizon import HorizonLLMClient
import ast
import zipfile
from io import BytesIO
import re
import networkx as nx

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@st.cache_data
def load_graph_data(uploaded_files):
    all_parsed_data = {"nodes": [], "edges": []}
    ignored_extensions = [".ckpt", ".ipynb_checkpoints", "-checkpoint.py"]
    with tempfile.TemporaryDirectory() as tmpdir:
        for uploaded_file in uploaded_files:
            if any(uploaded_file.name.endswith(ext) for ext in ignored_extensions):
                continue

            file_path = os.path.join(tmpdir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if file_path.endswith(".py"):
                    parser = PythonCodeParser(file_path)
                    parsed_data = parser.parse()
                    all_parsed_data["nodes"].extend(parsed_data["nodes"])
                    all_parsed_data["edges"].extend(parsed_data["edges"])
                else:
                    all_parsed_data["nodes"].append({"id": uploaded_file.name, "type": "file", "name": uploaded_file.name})
            except UnicodeDecodeError:
                all_parsed_data["nodes"].append({"id": uploaded_file.name, "type": "file", "name": uploaded_file.name})
    
    graph_builder = GraphBuilder()
    code_graph = graph_builder.build_graph(all_parsed_data)
    return code_graph

def generate_interactive_html(dot_string, node_types, edge_types):
    # Properly escape the dot string for JavaScript
    js_dot_string = json.dumps(dot_string)

    node_filters_html = ''.join(f'<label><input type="checkbox" class="node-filter" value="{nt}" checked> {nt}</label>' for nt in node_types)
    edge_filters_html = ''.join(f'<label><input type="checkbox" class="edge-filter" value="{et}" checked> {et}</label>' for et in edge_types)

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
      <title>Interactive Code Graph</title>
      <script src="https://d3js.org/d3.v5.min.js"></script>
      <script src="https://unpkg.com/@hpcc-js/wasm@0.3.11/dist/index.min.js"></script>
      <script src="https://unpkg.com/d3-graphviz@3.0.5/build/d3-graphviz.js"></script>
      <style>
        #graph-container {{
          border: 1px solid black;
          width: 100%;
          height: 80vh;
        }}
        .filters {{
          margin-bottom: 10px;
        }}
      </style>
    </head>
    <body>
      <div class="filters">
        <strong>Node Types:</strong>
        {node_filters_html}
        <br>
        <strong>Edge Types:</strong>
        {edge_filters_html}
      </div>
      <div id="graph-container"></div>

      <script>
        const dotString = {js_dot_string};
        const graphviz = d3.select("#graph-container").graphviz();

        function renderGraph() {{
          const nodeFilters = Array.from(document.querySelectorAll('.node-filter:checked')).map(el => el.value);
          const edgeFilters = Array.from(document.querySelectorAll('.edge-filter:checked')).map(el => el.value);

          const filteredDot = dotString.split('\n').filter(line => {{
            if (line.includes('->')) {{
              const match = line.match(/type=\"(.*?)\"/);
              if (match) {{
                return edgeFilters.includes(match[1]);
              }}
              return true;
            }} else if (line.includes('shape')) {{
                const match = line.match(/type=\"(.*?)\"/);
                if(match){{
                    return nodeFilters.includes(match[1]);
                }}
                return true;
            }}
            return true;
          }}).join('\n');

          graphviz.renderDot(filteredDot);
        }}

        d3.selectAll('.node-filter, .edge-filter').on('change', renderGraph);

        renderGraph();
      </script>
    </body>
    </html>
    '''

def convert_dot_to_markmap_json(dot_string):
    nodes = {}
    edges = []

    for line in dot_string.strip().split('\n'):
        if '->' in line:
            source, target_part = line.split('->')
            source = source.strip().replace('"', '')
            target, attrs = target_part.split('[')
            target = target.strip().replace('"', '')
            attrs = attrs.strip()[:-1]
            label = ''
            if 'label=' in attrs:
                label = attrs.split('label=')[-1].split(',')[0].replace('"', '')
            edges.append({{"source": source, "target": target, "label": label}})
        elif 'label=' in line:
            node_id, attrs = line.split('[')
            node_id = node_id.strip().replace('"', '')
            label = ''
            if 'label=' in attrs:
                label = attrs.split('label=')[-1].split(',')[0].replace('"', '')
            nodes[node_id] = {"id": node_id, "label": label, "children": []}

    for edge in edges:
        source_node = nodes.get(edge["source"])
        target_node = nodes.get(edge["target"])
        if source_node and target_node:
            source_node["children"].append(target_node)

    root_nodes = [node for node in nodes.values() if not any(edge["target"] == node["id"] for edge in edges)]
    
    if not root_nodes and nodes:
        root_nodes = [next(iter(nodes.values()))]

    def build_markmap_tree(node, visited):
        if node['id'] in visited:
            return None
        visited.add(node['id'])
        children = [build_markmap_tree(child, visited.copy()) for child in node["children"]]
        return {{
            "content": node["label"],
            "children": [child for child in children if child is not None]
        }}

    markmap_children = [build_markmap_tree(root, set()) for root in root_nodes]
    return json.dumps({{"content": "Code Graph", "children": markmap_children}})

def main():
    st.title("Code Visualizer and Query Engine")

    # --- Log File Analysis Section ---
    st.header("Log File Analysis")
    uploaded_files_log = st.file_uploader("Upload your codebase (zip file or individual files) for log analysis", accept_multiple_files=True, key="log_codebase")
    uploaded_log_file = st.file_uploader("Upload a log file", accept_multiple_files=False, key="log_file")

    if uploaded_log_file and uploaded_files_log:
        if st.button("Analyze Log File"):
            log_contents = uploaded_log_file.getvalue().decode("utf-8")
            
            with tempfile.TemporaryDirectory() as tmpdir:
                for uploaded_file in uploaded_files_log:
                    file_path = os.path.join(tmpdir, uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                problem, solution = analyze_log_file(log_contents, tmpdir)
                st.header("Log Analysis Results")
                st.error(f"Problem: {problem}")
                st.success(f"Solution: {solution}")

    # --- Code Visualization and other features ---
    st.header("Code Visualization and Analysis")
    uploaded_files_main = st.file_uploader("Upload any files for visualization and analysis", accept_multiple_files=True, key="main_codebase")

    if uploaded_files_main:
        # Initialize session state variables
        if "code_contents" not in st.session_state:
            st.session_state.code_contents = {}
        if "optimized_code" not in st.session_state:
            st.session_state.optimized_code = {}
        if "commented_code" not in st.session_state:
            st.session_state.commented_code = {}
        if "show_diff_opt" not in st.session_state:
            st.session_state.show_diff_opt = {}
        if "show_diff_comment" not in st.session_state:
            st.session_state.show_diff_comment = {}

        if not st.session_state.code_contents:
            for uploaded_file in uploaded_files_main:
                try:
                    content = uploaded_file.getvalue().decode("utf-8")
                    st.session_state.code_contents[uploaded_file.name] = content
                except UnicodeDecodeError:
                    st.session_state.code_contents[uploaded_file.name] = "This file is not a UTF-8 encoded text file."

        st.sidebar.header("Graph Options")
        
        # Node filter options
        st.sidebar.subheader("Filter Nodes")
        node_types = ["module", "class", "function", "method", "variable"]
        selected_node_types = [nt for nt in node_types if st.sidebar.checkbox(f"Show {nt}s", True)]

        # Edge filter options
        st.sidebar.subheader("Filter Edges")
        edge_types = ["IMPORTS", "CALLS", "CONTAINS", "INHERITS"]
        selected_edge_types = [et for et in edge_types if st.sidebar.checkbox(f"Show {et} edges", True)]

        # Clustering option
        st.sidebar.subheader("Layout Options")
        cluster_modules = st.sidebar.checkbox("Cluster Modules", False)

        code_graph = load_graph_data(uploaded_files_main)

        query_engine = QueryEngine(code_graph)
        dot_generator = DotGenerator()

        st.header("Code Graph Visualization")
        dot_string = dot_generator.generate_dot(code_graph, node_filter=selected_node_types, edge_filter=selected_edge_types, cluster_modules=cluster_modules)
        st.graphviz_chart(dot_string)
        
        interactive_html = generate_interactive_html(dot_string, selected_node_types, selected_edge_types)
        st.download_button(
            label="Download Graph as Interactive HTML",
            data=interactive_html,
            file_name="interactive_graph.html",
            mime="text/html",
        )

        st.header("Mark Map Visualization")
        markmap_json = convert_dot_to_markmap_json(dot_string)
        markmap_html = f'''
        <!DOCTYPE html>
        <html>
        <head>
          <title>Markmap</title>
          <script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
          <script src="https://cdn.jsdelivr.net/npm/markmap-view@0.18.12/dist/browser/index.js"></script>
        </head>
        <body>
          <svg id="mindmap" style="width: 100%; height: 600px;"></svg>
          <script>
            const data = JSON.parse(`{{markmap_json}}`);
            ((getMarkmap, getOptions, root, jsonOptions) => {{
              const markmap = getMarkmap();
              window.mm = markmap.Markmap.create(
                "svg#mindmap",
                (getOptions || markmap.deriveOptions)(jsonOptions),
                data
              );
            }})(() => window.markmap, null, null, null);
          </script>
        </body>
        </html>
        '''
        components.html(markmap_html, height=600)
        st.download_button(
            label="Download Markmap as HTML",
            data=markmap_html,
            file_name="markmap.html",
            mime="text/html",
        )

        # --- Optimization Section ---
        st.header("Look for Optimizing Opportunities")
        if st.button("Click to Analyze the Code"):
            with st.spinner("Analyzing code for optimizations..."):
                client = HorizonLLMClient()
                st.session_state.optimized_code = {{}}
                for file_name, original_code in st.session_state.code_contents.items():
                    response = client.get_chat_response(
                        user_msg=f"Please analyze the following Python code and suggest optimizations such as parallel computing, reducing time or space complexity:\n\n```python\n{{original_code}}\n```")
                    full_text = response["model_answer"]

                    match = re.search(r"```python\n(.*?)\n```", full_text, re.DOTALL)
                    optimized_code = match.group(1).strip() if match else original_code
                    st.session_state.optimized_code[file_name] = optimized_code

        if st.session_state.optimized_code:
            for file_name, optimized_code in st.session_state.optimized_code.items():
                st.subheader(f"Optimized Code for {{file_name}}:")
                st.text_area("Original Code", st.session_state.code_contents[file_name], height=300, key=f"original_opt_{{file_name}}")
                st.text_area("Optimized Code", optimized_code, height=300, key=f"optimized_{{file_name}}")
                if st.button(f"Show Diff for {{file_name}}", key=f"opt_{{file_name}}"):
                    st.session_state.show_diff_opt[file_name] = not st.session_state.show_diff_opt.get(file_name, False)
                
                if st.session_state.show_diff_opt.get(file_name, False):
                    original_code = st.session_state.code_contents[file_name]
                    diff_viewer = CodeDiffViewer(original_code, optimized_code)
                    diff_viewer.show_diff()

            if st.button("Apply Optimizations"):
                st.session_state.code_contents.update(st.session_state.optimized_code)
                st.session_state.optimized_code = {{}}
                st.rerun()

        # --- Commenting Section ---
        st.header("Generate Function Comments")
        if st.button("Generate Comments"):
            with st.spinner("Generating comments..."):
                client = HorizonLLMClient()
                st.session_state.commented_code = {{}}
                all_generated_docstrings = []

                class DocstringAdder(ast.NodeTransformer):
                    def __init__(self):
                        self.generated_docstrings = []

                    def visit_FunctionDef(self, node):
                        function_code = ast.get_source_segment(original_code, node)
                        
                        response = client.get_chat_response(
                            user_msg=f"Explain what the following Python function does:\n\n```python\n{{function_code}}\n```")
                        comment = response["model_answer"]
                        
                        self.generated_docstrings.append({{"function": node.name, "docstring": comment}})

                        docstring = ast.Expr(value=ast.Constant(value=comment))
                        
                        if (
                            node.body
                            and isinstance(node.body[0], ast.Expr)
                            and isinstance(node.body[0].value, ast.Constant)
                        ):
                            node.body[0] = docstring
                        else:
                            node.body.insert(0, docstring)
                        
                        return node

                for file_name, original_code in st.session_state.code_contents.items():
                    if not file_name.endswith(".py"):
                        continue
                    try:
                        tree = ast.parse(original_code)
                    except SyntaxError:
                        st.warning(f"Could not parse {{file_name}}. Skipping.")
                        continue
                    
                    adder = DocstringAdder()
                    new_tree = adder.visit(tree)
                    all_generated_docstrings.extend(adder.generated_docstrings)
                    modified_code = ast.unparse(new_tree)
                    st.session_state.commented_code[file_name] = modified_code

                if all_generated_docstrings:
                    markmap_html = f'''<!DOCTYPE html>
<html>
<head>
<title>Markmap of Generated Docstrings</title>
<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/markmap-view@0.18.12/dist/browser/index.js"></script>
</head>
<body>
<h1>Generated Docstrings</h1>
<div id="markmap-container"></div>

<script>
document.addEventListener('DOMContentLoaded', () => {{
  const docstrings = {json.dumps(all_generated_docstrings)};
  const container = document.getElementById('markmap-container');
  const {{ Markmap, transform }} = window.markmap;

  docstrings.forEach((item, index) => {{
    const div = document.createElement('div');
    div.innerHTML = `<h2>${{item.function}}</h2>`;
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.id = `mindmap-${{index}}`;
    svg.style.width = "100%";
    svg.style.height = "400px";
    div.appendChild(svg);
    container.appendChild(div);

    const data = transform(item.docstring);
    Markmap.create(`svg#mindmap-${{index}}`, null, data);
  }});
}});
</script>
</body>
</html>'''
                    st.download_button(
                        label="Download Docstring Markmaps",
                        data=markmap_html,
                        file_name="docstring_markmaps.html",
                        mime="text/html",
                    )

        if st.session_state.commented_code:
            for file_name, commented_code in st.session_state.commented_code.items():
                st.subheader(f"Proposed changes for {{file_name}}:")
                st.text_area("Original Code", st.session_state.code_contents[file_name], height=300, key=f"original_comment_{{file_name}}")
                st.text_area("Code with Comments", commented_code, height=300, key=f"commented_{{file_name}}")
                if st.button(f"Show Diff for {{file_name}}", key=f"comment_{{file_name}}"):
                    st.session_state.show_diff_comment[file_name] = not st.session_state.show_diff_comment.get(file_name, False)

                if st.session_state.show_diff_comment.get(file_name, False):
                    original_code = st.session_state.code_contents[file_name]
                    diff_viewer = CodeDiffViewer(original_code, commented_code)
                    diff_viewer.show_diff()

            if st.button("Apply Comments"):
                st.session_state.code_contents.update(st.session_state.commented_code)
                st.session_state.commented_code = {{}}
                st.rerun()

        # --- Download Section ---
        if st.session_state.optimized_code or st.session_state.commented_code:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                if st.session_state.optimized_code:
                    for file_name, modified_code in st.session_state.optimized_code.items():
                        zip_file.writestr(file_name, modified_code)
                if st.session_state.commented_code:
                    for file_name, modified_code in st.session_state.commented_code.items():
                        zip_file.writestr(file_name, modified_code)

            st.download_button(
                label="Download All Modified Files as ZIP",
                data=zip_buffer.getvalue(),
                file_name="modified_code.zip",
                mime="application/zip",
            )

def analyze_log_file(log_contents, codebase_path):
    if "traceback" in log_contents.lower():
        traceback_lines = []
        in_traceback = False
        for line in log_contents.splitlines():
            if "traceback (most recent call last)" in line.lower():
                traceback_lines = [line]
                in_traceback = True
            elif in_traceback:
                traceback_lines.append(line)

        problem = "\n".join(traceback_lines)

        # Extract file and line number from traceback
        file_path_match = re.search(r'file \"(.*?)\", line', problem, re.IGNORECASE)
        line_number_match = re.search(r'line (\d+)', problem, re.IGNORECASE)

        if file_path_match and line_number_match:
            file_path = file_path_match.group(1)
            line_number = int(line_number_match.group(1))
            
            # Construct the full path to the file
            full_file_path = os.path.join(codebase_path, file_path)

            if os.path.exists(full_file_path):
                with open(full_file_path, 'r') as f:
                    code_lines = f.readlines()
                
                # Extract the relevant code snippet
                start = max(0, line_number - 5)
                end = min(len(code_lines), line_number + 5)
                code_snippet = "".join(code_lines[start:end])

                # Use HorizonLLMClient for analysis
                client = HorizonLLMClient()
                response = client.get_chat_response(
                    user_msg=f"The following traceback was found in a log file:\n\n```\n{{problem}}\n```\n\nThe error occurred in the following code snippet\n\n```python\n{{code_snippet}}\n```\n\nPlease explain the error and suggest a solution.")
                solution = response["model_answer"]
            else:
                solution = "The file mentioned in the traceback was not found in the uploaded codebase."
        else:
            solution = "A traceback was found, but the file path and line number could not be extracted. A manual review is required."
    else:
        if "error" in log_contents.lower():
            problem = "The log file contains the word 'error', but no traceback was found. Look for lines containing 'error' to identify the problem."
            solution = "Review the lines containing the word 'error' to understand the context of the problem."
        elif "warning" in log_contents.lower():
            problem = "The log file contains warnings. While not always critical, they might indicate potential issues."
            solution = "Review the warnings in the log file to see if they are relevant to the problem you are facing."
        else:
            problem = "No traceback or error keywords found in the log file."
            solution = "The log file does not seem to contain any obvious errors. The problem might be more subtle. A manual review of the log file is recommended."
            
    return problem, solution

if __name__ == "__main__":
    main()