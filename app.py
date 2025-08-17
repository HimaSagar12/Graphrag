import streamlit as st
import os
import sys
import tempfile
import pydot
import json
import base64
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

def convert_graph_to_markmap_json(code_graph):
    
    def build_markmap_tree(node_id, graph, visited):
        if node_id in visited:
            return None
        visited.add(node_id)

        node_data = graph.nodes[node_id]
        node_content = node_data.get("name", node_id)
        markmap_node = {"content": node_content, "children": []}

        # Group children by edge type
        children_by_type = {}
        for _, target_node_id, edge_data in graph.out_edges(node_id, data=True):
            edge_type = edge_data.get("type", "UNKNOWN")
            if edge_type not in children_by_type:
                children_by_type[edge_type] = []
            
            child_node = build_markmap_tree(target_node_id, graph, visited)
            if child_node:
                children_by_type[edge_type].append(child_node)

        for edge_type, children in children_by_type.items():
            if children:
                markmap_node["children"].append({
                    "content": edge_type,
                    "children": children
                })

        return markmap_node

    root_nodes = [node for node, in_degree in code_graph.in_degree() if in_degree == 0]
    
    if not root_nodes:
        root_nodes = [next(iter(code_graph.nodes()))] if code_graph.nodes() else []

    markmap_children = []
    visited_nodes = set()
    for root_node in root_nodes:
        child = build_markmap_tree(root_node, code_graph, visited_nodes)
        if child:
            markmap_children.append(child)

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
        
        html_template = f"""
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
        html_b64 = base64.b64encode(html_template.encode()).decode()
        href = f'<a href="data:text/html;base64,{html_b64}" download="graph.html">Download Graph as HTML</a>'
        st.markdown(href, unsafe_allow_html=True)


        markmap_json = convert_graph_to_markmap_json(code_graph)
        markmap_html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <title>Markmap</title>
          <script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
          <script src="https://cdn.jsdelivr.net/npm/markmap-view@0.18.12/dist/browser/index.js"></script>
        </head>
        <body>
          <svg id="mindmap" style="width: 100%; height: 100vh;"></svg>
          <script>
            ((getMarkmap, getOptions, root, jsonOptions) => {{{{ 
              const markmap = getMarkmap();
              window.mm = markmap.Markmap.create(
                "svg#mindmap",
                (getOptions || markmap.deriveOptions)(jsonOptions),
                JSON.parse('{markmap_json}')
              );
            }}}})(() => window.markmap, null, null, null);
          </script>
        </body>
        </html>
        """
        markmap_b64 = base64.b64encode(markmap_html_template.encode()).decode()
        href = f'<a href="data:text/html;base64,{markmap_b64}" download="markmap.html">Download as Mark Map</a>'
        st.markdown(href, unsafe_allow_html=True)


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
                elif "called by" in query:
                    function_name = query.split("called by")[-1].strip()
                    called_functions = query_engine.find_functions_called_by(function_name)
                    if called_functions:
                        response = f"Functions called by {function_name}:\n"
                        for func in called_functions:
                            response += f"- {func['name']} (type: {func['type']})\n"
                    else:
                        response = f"No functions called by {function_name}."
                elif "readers of" in query:
                    var_name = query.split("readers of")[-1].strip()
                    readers = query_engine.find_nodes_reading_var(var_name)
                    if readers:
                        response = f"Nodes reading variable '{var_name}':\n"
                        for reader in readers:
                            response += f"- {reader['name']} (type: {reader['type']})\n"
                    else:
                        response = f"No nodes found reading variable '{var_name}'."
                elif "writers of" in query:
                    var_name = query.split("writers of")[-1].strip()
                    writers = query_engine.find_nodes_writing_var(var_name)
                    if writers:
                        response = f"Nodes writing to variable '{var_name}':\n"
                        for writer in writers:
                            response += f"- {writer['name']} (type: {writer['type']})\n"
                    else:
                        response = f"No nodes found writing to variable '{var_name}'."
                elif "throwers" in query:
                    throwers = query_engine.find_nodes_throwing_exception()
                    if throwers:
                        response = f"Nodes throwing exceptions:\n"
                        for thrower in throwers:
                            response += f"- {thrower['name']} (type: {thrower['type']})\n"
                    else:
                        response = f"No nodes found throwing exceptions."
                elif "handlers" in query:
                    handlers = query_engine.find_nodes_handling_exception()
                    if handlers:
                        response = f"Nodes handling exceptions:\n"
                        for handler in handlers:
                            response += f"- {handler['name']} (type: {handler['type']})\n"
                    else:
                        response = f"No nodes found handling exceptions."
                elif "decorated by" in query:
                    decorator_name = query.split("decorated by")[-1].strip()
                    decorated_nodes = query_engine.find_nodes_with_decorator(decorator_name)
                    if decorated_nodes:
                        response = f"Nodes decorated by '{decorator_name}':\n"
                        for node in decorated_nodes:
                            response += f"- {node['name']} (type: {node['type']})\n"
                    else:
                        response = f"No nodes found decorated by '{decorator_name}'."
                elif "returners" in query:
                    returners = query_engine.find_nodes_returning_value()
                    if returners:
                        response = f"Nodes returning values:\n"
                        for returner in returners:
                            response += f"- {returner['name']} (type: {returner['type']})\n"
                    else:
                        response = f"No nodes found returning values."
                elif "uses" in query:
                    service_name = query.split("uses")[-1].strip()
                    users = query_engine.find_nodes_using_service(service_name)
                    if users:
                        response = f"Nodes using service '{service_name}':\n"
                        for user in users:
                            response += f"- {user['name']} (type: {user['type']})\n"
                    else:
                        response = f"No nodes found using service '{service_name}'."
                
                st.text_area("Query Result", response, height=200)
            else:
                st.warning("Please enter a query.")

if __name__ == "__main__":
    main()
