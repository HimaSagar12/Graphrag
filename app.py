import streamlit as st
import os
import sys
import tempfile
import pydot
import json
import base64
import streamlit.components.v1 as components
import ast
import zipfile
from io import BytesIO
from horizon import HorizonLLMClient
from src.parser.python_parser import PythonCodeParser
from src.graph.graph_builder import GraphBuilder
from src.query_engine.query_engine import QueryEngine
from src.graph.dot_generator import DotGenerator


import tempfile
import ast
import yaml
# from src.parser.python_parser import extract_nodes_from_ast
from src.graph.graph_builder import GraphBuilder  # Assuming this is where GraphBuilder is defined


# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@st.cache_data
def load_graph_data(file_contents):
    all_parsed_data = {"nodes": [], "edges": []}
    files = list(file_contents.keys())

    with tempfile.TemporaryDirectory() as tmpdir:
        for file_name, content in file_contents.items():
            file_path = os.path.join(tmpdir, file_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            try:
                if file_name.endswith(".py"):
                    tree = ast.parse(content, filename=file_name)
                    parsed_data = PythonCodeParser.extract_nodes_from_ast(tree, file_name)
                elif file_name.endswith((".yaml", ".yml")):
                    data = yaml.safe_load(content)
                    parsed_data = {"nodes": [{"id": file_name, "type": "file", "name": file_name}], "edges": []}
                elif file_name.endswith(".json"):
                    data = json.loads(content)
                    parsed_data = {"nodes": [{"id": file_name, "type": "file", "name": file_name}], "edges": []}
                else:
                    parsed_data = {"nodes": [{"id": file_name, "type": "file", "name": file_name}], "edges": []}

                all_parsed_data["nodes"].extend(parsed_data["nodes"])
                all_parsed_data["edges"].extend(parsed_data["edges"])

            except Exception as e:
                st.error(f"Error parsing {file_name}: {e}")

    # Add file nodes and containment edges
    for file_name in files:
        all_parsed_data["nodes"].append({"id": file_name, "type": "file", "name": file_name})
        for node in all_parsed_data["nodes"]:
            if node.get("file") == file_name:
                all_parsed_data["edges"].append({"source": file_name, "target": node["id"], "type": "CONTAINS"})

    graph_builder = GraphBuilder()
    code_graph = graph_builder.build_graph(all_parsed_data)
    return code_graph


def convert_graph_to_markmap_json(code_graph):
    def build_markmap_tree(node_id, graph):
        node_data = graph.nodes[node_id]
        node_content = node_data.get("name", node_id)
        markmap_node = {"content": node_content, "children": []}

        for _, target_node_id, edge_data in graph.out_edges(node_id, data=True):
            if edge_data.get("type") == "CONTAINS":
                child_node = build_markmap_tree(target_node_id, graph)
                if child_node:
                    markmap_node["children"].append(child_node)

        return markmap_node

    root_nodes = [node for node, in_degree in code_graph.in_degree() if in_degree == 0]
    
    if not root_nodes:
        root_nodes = [next(iter(code_graph.nodes()))] if code_graph.nodes() else []

    markmap_children = []
    for root_node in root_nodes:
        child = build_markmap_tree(root_node, code_graph)
        if child:
            markmap_children.append(child)

    return json.dumps({"content": "Code Structure", "children": markmap_children})

def generate_graph_html(dot_string):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Graph Visualization</title>
      <script src="https://cdn.jsdelivr.net/npm/viz.js@2.1.2/viz.min.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/viz.js@2.1.2/full.render.js"></script>
    </head>
    <body>
      <div id="graph"></div>
      <script>
        var dot = `{dot_string}`;
        var viz = new Viz();
        viz.renderSVGElement(dot)
          .then(function(element) {{{{
            document.getElementById('graph').appendChild(element);
          }}}})
          .catch(error => {{{{
            viz = new Viz();
            console.error(error);
          }}}});
      </script>
    </body>
    </html>
    """

def generate_markmap_html(markmap_json):
    return f"""
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
        const data = JSON.parse(`{markmap_json}`);
        ((getMarkmap, getOptions, root, jsonOptions) => {{{{
          const markmap = getMarkmap();
          window.mm = markmap.Markmap.create(
            "svg#mindmap",
            (getOptions || markmap.deriveOptions)(jsonOptions),
            data
          );
        }}}})(() => window.markmap, null, null, null);
      </script>
    </body>
    </html>
    """

def main():
    st.title("Code Visualizer and Query Engine")

    if "code_contents" not in st.session_state:
        st.session_state.code_contents = {}

    uploaded_files = st.file_uploader("Upload any files", accept_multiple_files=True)

    if uploaded_files:
        if not st.session_state.code_contents:
            for uploaded_file in uploaded_files:
                try:
                    content = uploaded_file.getvalue().decode("utf-8")
                except UnicodeDecodeError:
                    content = "This file is not a UTF-8 encoded text file."
                
                st.session_state.code_contents[uploaded_file.name] = content

        code_graph = load_graph_data(st.session_state.code_contents)
        dot_generator = DotGenerator()

        st.header("Code Graph Visualization")
        dot_string = dot_generator.generate_dot(code_graph)
        st.graphviz_chart(dot_string)
        
        graph_html = generate_graph_html(dot_string)
        html_b64 = base64.b64encode(graph_html.encode()).decode()
        href = f'<a href="data:text/html;base64,{html_b64}" download="graph.html">Download Graph as HTML</a>'
        st.markdown(href, unsafe_allow_html=True)

        st.header("Mark Map Visualization")
        markmap_json = convert_graph_to_markmap_json(code_graph)
        markmap_html = generate_markmap_html(markmap_json)
        components.html(markmap_html, height=600)

        markmap_b64 = base64.b64encode(markmap_html.encode()).decode()
        href = f'<a href="data:text/html;base64,{markmap_b64}" download="markmap.html">Download as Mark Map</a>'
        st.markdown(href, unsafe_allow_html=True)

if __name__ == "__main__":
    main()