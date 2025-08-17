import streamlit as st
import git
import os
import tempfile
from src.graph.graph_builder import GraphBuilder
from src.graph.dot_generator import DotGenerator
from src.parser.python_parser import PythonParser

def main():
    st.title("Code Visualizer")

    repo_url = st.text_input("Enter a Git repository URL:")

    if st.button("Generate Graph"):
        if repo_url:
            with tempfile.TemporaryDirectory() as tmpdir:
                try:
                    st.info(f"Cloning repository from {repo_url}...")
                    git.Repo.clone_from(repo_url, tmpdir)
                    st.success("Repository cloned successfully!")

                    st.info("Parsing code and building graph...")
                    parser = PythonParser()
                    builder = GraphBuilder(parser)
                    graph = builder.build_graph(tmpdir)
                    st.success("Graph built successfully!")

                    st.info("Generating DOT file...")
                    dot_generator = DotGenerator()
                    dot_string = dot_generator.generate_dot(graph)
                    st.success("DOT file generated successfully!")

                    st.graphviz_chart(dot_string)

                    st.download_button(
                        label="Download HTML",
                        data=f"<html><body><pre>{dot_string}</pre></body></html>",
                        file_name="graph.html",
                        mime="text/html",
                    )

                except git.exc.GitCommandError as e:
                    st.error(f"Error cloning repository: {e}")
                except Exception as e:
                    st.error(f"An error occurred: {e}")
        else:
            st.warning("Please enter a repository URL.")

if __name__ == "__main__":
    main()
