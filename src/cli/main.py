import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.parser.python_parser import PythonCodeParser
from src.graph.graph_builder import GraphBuilder
from src.query_engine.query_engine import QueryEngine
from src.graph.dot_generator import DotGenerator

CODEBASE_PATH = "/data/data/com.termux/files/home/graph_rag_code_understanding/codebase_example"

# Placeholder for Groq API Key - Replace with your actual key
GROQ_API_KEY = "YOUR_GROQ_API_KEY_HERE"

def main():
    print("Building code graph...")
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
    query_engine = QueryEngine(code_graph)
    dot_generator = DotGenerator()
    print(f"Graph built with {len(code_graph.nodes)} nodes and {len(code_graph.edges)} edges.")

    print("\nAsk questions about the codebase (e.g., 'functions in example_module.py', 'callers of main', 'details of greet'):")
    print("New queries: 'readers of <var_name>', 'writers of <var_name>', 'throwers', 'handlers', 'decorated by <decorator_name>', 'returners', 'uses <service_name>'.")
    print("Type 'generate dot' to create a DOT file for visualization.")
    print("Type 'exit' to quit.")

    while True:
        query = input("> ").strip().lower()
        if query == "exit":
            break
        elif query == "generate dot":
            dot_string = dot_generator.generate_dot(code_graph)
            dot_file_path = os.path.join(os.getcwd(), "code_flow.dot")
            with open(dot_file_path, "w") as f:
                f.write(dot_string)
            print(f"DOT file generated at: {dot_file_path}")
            print("To visualize, install Graphviz (e.g., `sudo apt-get install graphviz` or `brew install graphviz`) and run:")
            print(f"  dot -Tpng {dot_file_path} -o code_flow.png")
            continue

        response = "I couldn't understand your query. Try something like: 'functions in <file_name>', 'callers of <function_name>', 'details of <node_name>'."
        retrieved_context = ""

        if "functions in" in query:
            file_name = query.split("functions in")[-1].strip().replace(".py", "") + ".py"
            functions = query_engine.find_functions_in_file(file_name)
            if functions:
                response = f"Functions in {file_name}:\n"
                for func in functions:
                    response += f"- {func['name']} (line {func['line_number']})\n"
                    if func['docstring']:
                        response += f"  Docstring: {func['docstring']}\n"
                retrieved_context = str(functions)
            else:
                response = f"No functions found in {file_name} or file not parsed."
        elif "callers of" in query:
            function_name = query.split("callers of")[-1].strip()
            callers = query_engine.find_callers_of_function(function_name)
            if callers:
                response = f"Callers of {function_name}:\n"
                for caller in callers:
                    response += f"- {caller['name']} (type: {caller['type']})\n"
                retrieved_context = str(callers)
            else:
                response = f"No callers found for {function_name}."
        elif "details of" in query:
            node_name = query.split("details of")[-1].strip()
            details = query_engine.get_node_details(node_name)
            if details:
                response = f"Details for {node_name}:\n"
                for key, value in details.items():
                    response += f"- {key}: {value}\n"
                retrieved_context = str(details)
            else:
                response = f"Node '{node_name}' not found."
        elif "called by" in query:
            function_name = query.split("called by")[-1].strip()
            called_functions = query_engine.find_functions_called_by(function_name)
            if called_functions:
                response = f"Functions called by {function_name}:\n"
                for func in called_functions:
                    response += f"- {func['name']} (type: {func['type']})\n"
                retrieved_context = str(called_functions)
            else:
                response = f"No functions called by {function_name}."
        elif "readers of" in query:
            var_name = query.split("readers of")[-1].strip()
            readers = query_engine.find_nodes_reading_var(var_name)
            if readers:
                response = f"Nodes reading variable '{var_name}':\n"
                for reader in readers:
                    response += f"- {reader['name']} (type: {reader['type']})\n"
                retrieved_context = str(readers)
            else:
                response = f"No nodes found reading variable '{var_name}'."
        elif "writers of" in query:
            var_name = query.split("writers of")[-1].strip()
            writers = query_engine.find_nodes_writing_var(var_name)
            if writers:
                response = f"Nodes writing to variable '{var_name}':\n"
                for writer in writers:
                    response += f"- {writer['name']} (type: {writer['type']})\n"
                retrieved_context = str(writers)
            else:
                response = f"No nodes found writing to variable '{var_name}'."
        elif "throwers" in query:
            throwers = query_engine.find_nodes_throwing_exception()
            if throwers:
                response = f"Nodes throwing exceptions:\n"
                for thrower in throwers:
                    response += f"- {thrower['name']} (type: {thrower['type']})\n"
                retrieved_context = str(throwers)
            else:
                response = f"No nodes found throwing exceptions."
        elif "handlers" in query:
            handlers = query_engine.find_nodes_handling_exception()
            if handlers:
                response = f"Nodes handling exceptions:\n"
                for handler in handlers:
                    response += f"- {handler['name']} (type: {handler['type']})\n"
                retrieved_context = str(handlers)
            else:
                response = f"No nodes found handling exceptions."
        elif "decorated by" in query:
            decorator_name = query.split("decorated by")[-1].strip()
            decorated_nodes = query_engine.find_nodes_with_decorator(decorator_name)
            if decorated_nodes:
                response = f"Nodes decorated by '{decorator_name}':\n"
                for node in decorated_nodes:
                    response += f"- {node['name']} (type: {node['type']})\n"
                retrieved_context = str(decorated_nodes)
            else:
                response = f"No nodes found decorated by '{decorator_name}'."
        elif "returners" in query:
            returners = query_engine.find_nodes_returning_value()
            if returners:
                response = f"Nodes returning values:\n"
                for returner in returners:
                    response += f"- {returner['name']} (type: {returner['type']})\n"
                retrieved_context = str(returners)
            else:
                response = f"No nodes found returning values."
        elif "uses" in query:
            service_name = query.split("uses")[-1].strip()
            users = query_engine.find_nodes_using_service(service_name)
            if users:
                response = f"Nodes using service '{service_name}':\n"
                for user in users:
                    response += f"- {user['name']} (type: {user['type']})\n"
                retrieved_context = str(users)
            else:
                response = f"No nodes found using service '{service_name}'." # Corrected the trailing quote here

        print(response)
        if retrieved_context:
            print(f"\n--- Context for LLM (would be sent to Groq) ---\n{retrieved_context}\n--------------------------------------------------")

if __name__ == "__main__":
    main()

