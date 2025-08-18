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
from horizon import HorizonLLMClient
import ast
import zipfile
from io import BytesIO
import re

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
            
            if file_path.endswith(".py"):
                parser = PythonCodeParser(file_path)
                parsed_data = parser.parse()
                all_parsed_data["nodes"].extend(parsed_data["nodes"])
                all_parsed_data["edges"].extend(parsed_data["edges"])
            else:
                all_parsed_data["nodes"].append({"id": uploaded_file.name, "type": "file", "name": uploaded_file.name})
    
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

        st.header("Look for Optimizing Opportunities")

        if st.button("Click to Analyze the Code"):
            try:
                client = HorizonLLMClient()
                st.session_state.modified_files = {}

                for file_name, original_code in st.session_state.code_contents.items():
                    response = client.get_chat_response(
                        user_msg=f"Please analyze the following Python code and suggest optimizations such as parallel computing, reducing time or space complexity:\n\n```python\n{original_code}\n```")
                    full_text = response["model_answer"]

                    # Extract only the Python code block from the response
                    match = re.search(r"```python\n(.*?)```", full_text, re.DOTALL)
                    optimized_code = match.group(1).strip() if match else original_code  # fallback to original if no match

                    st.session_state.modified_files[file_name] = optimized_code

                    st.subheader(f"AI Suggestions for {file_name}:")
                    st.text_area("Full AI Response (Explanation + Code)", full_text, height=300)

                    st.subheader(f"Optimized Code for {file_name}:")
                    st.text_area("Optimized Code Only", optimized_code, height=300)

            except Exception as e:
                st.error(f"An error occurred: {e}")

        # Apply and download section
        if "modified_files" in st.session_state and st.session_state.modified_files:
            if st.button("Apply Optimizations and Update Visualizations"):
                st.session_state.code_contents = st.session_state.modified_files
                st.session_state.modified_files = {}
                st.rerun()

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for file_name, modified_code in st.session_state.modified_files.items():
                    zip_file.writestr(file_name, modified_code)

            st.download_button(
                label="Download All Optimized Files as ZIP",
                data=zip_buffer.getvalue(),
                file_name="optimized_code.zip",
                mime="application/zip",
            )

        st.header("Generate Function Comments")
        if st.button("Generate Comments"):
            try:
                client = HorizonLLMClient()
                st.session_state.modified_files = {}
                
                for file_name, original_code in st.session_state.code_contents.items():
                    tree = ast.parse(original_code)
                    
                    class DocstringAdder(ast.NodeTransformer):
                        def visit_FunctionDef(self, node):
                            function_code = ast.get_source_segment(original_code, node)
                            
                            response = client.get_chat_response(
                                user_msg=f"Explain what the following Python function does:\n\n```python\n{function_code}\n```")
                            comment = response["model_answer"]
                            
                            # Create a new docstring node
                            docstring = ast.Expr(value=ast.Constant(value=comment))
                            
                            # If the function already has a docstring, replace it
                            if (
                                node.body
                                and isinstance(node.body[0], ast.Expr)
                                and isinstance(node.body[0].value, ast.Constant)
                            ):
                                node.body[0] = docstring
                            else:
                                # If there is no docstring, add one
                                node.body.insert(0, docstring)
                            
                            return node

                    new_tree = DocstringAdder().visit(tree)
                    modified_code = ast.unparse(new_tree)
                    
                    st.session_state.modified_files[file_name] = modified_code
                    
                    st.subheader(f"Proposed changes for {file_name}:")
                    st.text_area("Original Code", original_code, height=300)
                    st.text_area("Code with Comments", modified_code, height=300)

            except Exception as e:
                st.error(f"An error occurred: {e}")

        if "modified_files" in st.session_state and st.session_state.modified_files:
            if st.button("Apply Comments and Update Visualizations"):
                st.session_state.code_contents = st.session_state.modified_files
                st.session_state.modified_files = {}
                st.rerun()

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for file_name, modified_code in st.session_state.modified_files.items():
                    zip_file.writestr(file_name, modified_code)
            
            st.download_button(
                label="Download All Modified Files as ZIP",
                data=zip_buffer.getvalue(),
                file_name="commented_code.zip",
                mime="application/zip",
            )

if __name__ == "__main__":
    main()
