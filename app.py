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

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@st.cache_data
def load_graph_data(uploaded_files):
    all_parsed_data = {"nodes": [], "edges": []}
    with tempfile.TemporaryDirectory() as tmpdir:
        for uploaded_file in uploaded_files:
            file_path = os.path.join(tmpdir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            parser = PythonCodeParser(file_path)
            parsed_data = parser.parse()
            all_parsed_data["nodes"].extend(parsed_data["nodes"])
            all_parsed_data["edges"].extend(parsed_data["edges"])
    
    graph_builder = GraphBuilder()
    code_graph = graph_builder.build_graph(all_parsed_data)
    return code_graph

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
            edges.append({"source": source, "target": target, "label": label})
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

    def build_markmap_tree(node):
        return {
            "content": node["label"],
            "children": [build_markmap_tree(child) for child in node["children"]]
        }

    markmap_children = [build_markmap_tree(root) for root in root_nodes]
    return json.dumps({"content": "Code Graph", "children": markmap_children})

def main():
    st.title("Code Visualizer and Query Engine")

    uploaded_files = st.file_uploader("Upload Python files", accept_multiple_files=True, type="py")

    if uploaded_files:
        code_graph = load_graph_data(uploaded_files)
        query_engine = QueryEngine(code_graph)
        dot_generator = DotGenerator()

        st.header("Code Graph Visualization")
        dot_string = dot_generator.generate_dot(code_graph)
        st.graphviz_chart(dot_string)
        
        st.download_button(
            label="Download Graph as HTML",
            data=f"<html><body><pre>{dot_string}</pre></body></html>",
            file_name="graph.html",
            mime="text/html",
        )

        st.header("Mark Map Visualization")
        markmap_json = convert_dot_to_markmap_json(dot_string)
        markmap_html = f"""
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
        components.html(markmap_html, height=600)

        st.header("Query Your Codebase")
        query = st.text_input("Enter your query:").strip().lower()

        if st.button("Submit Query"):
            if query:
                response = "I couldn't understand your query. Try something like: 'functions in <file_name>', 'callers of <function_name>', 'details of <node_name>'."
                
                if "functions in" in query:
                    file_name = query.split("functions in")[-1].strip().replace(".py", "") + ".py"
                    functions = query_engine.find_functions_in_file(file_name)
                    if functions:
                        response = f"Functions in {file_name}:\n"
                        for func in functions:
                            response += f"- {func['name']} (line {func['line_number']})\n"
                            if func['docstring']:
                                response += f"  Docstring: {func['docstring']}\n"
                    else:
                        response = f"No functions found in {file_name} or file not parsed."
                elif "callers of" in query:
                    function_name = query.split("callers of")[-1].strip()
                    callers = query_engine.find_callers_of_function(function_name)
                    if callers:
                        response = f"Callers of {function_name}:\n"
                        for caller in callers:
                            response += f"- {caller['name']} (type: {caller['type']})\n"
                    else:
                        response = f"No callers found for {function_name}."
                elif "details of" in query:
                    node_name = query.split("details of")[-1].strip()
                    details = query_engine.get_node_details(node_name)
                    if details:
                        response = f"Details for {node_name}:\n"
                        for key, value in details.items():
                            response += f"- {key}: {value}\n"
                    else:
                        response = f"Node '{node_name}' not found."
                
                st.text_area("Query Result", response, height=200)
            else:
                st.warning("Please enter a query.")

if __name__ == "__main__":
    main()
