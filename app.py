import streamlit as st
import os
from src.graph.graph_builder import GraphBuilder
from src.graph.dot_generator import DotGenerator
from src.parser.python_parser import PythonCodeParser

CODEBASE_PATH = "/data/data/com.termux/files/home/graph_rag_code_understanding/codebase_example"

def main():
    st.title("Code Visualizer")

    if st.button("Generate Graph from Local Code"):
        try:
            st.info("Parsing code and building graph...")
            all_parsed_data = {"nodes": [], "edges": []}
            
            for root, _, files in os.walk(CODEBASE_PATH):
                for file in files:
                    if file.endswith(".py"):
                        file_path = os.path.join(root, file)
                        parser = PythonCodeParser(file_path)
                        parsed_data = parser.parse()
                        all_parsed_data["nodes"].extend(parsed_data["nodes"])
                        all_parsed_data["edges"].extend(parsed_data["edges"])

            graph_builder = GraphBuilder()
            code_graph = graph_builder.build_graph(all_parsed_data)
            st.success("Graph built successfully!")

            st.info("Generating DOT file...")
            dot_generator = DotGenerator()
            dot_string = dot_generator.generate_dot(code_graph)
            st.success("DOT file generated successfully!")

            st.graphviz_chart(dot_string)

            st.download_button(
                label="Download HTML",
                data=f"<html><body><pre>{dot_string}</pre></body></html>",
                file_name="graph.html",
                mime="text/html",
            )

        except Exception as e:
            st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()