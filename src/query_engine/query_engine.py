import networkx as nx

class QueryEngine:
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph

    def find_functions_in_file(self, file_name):
        functions = []
        for node_id, data in self.graph.nodes(data=True):
            if data.get("type") == "function" and file_name in node_id:
                functions.append(data)
        return functions

    def find_callers_of_function(self, function_name):
        callers = []
        for source, target, data in self.graph.edges(data=True):
            if data.get("type") == "CALLS" and function_name in target:
                callers.append(self.graph.nodes[source])
        return callers

    def find_functions_called_by(self, function_name):
        called_functions = []
        for source, target, data in self.graph.edges(data=True):
            if data.get("type") == "CALLS" and function_name in source:
                called_functions.append(self.graph.nodes[target])
        return called_functions

    def get_node_details(self, node_name):
        for node_id, data in self.graph.nodes(data=True):
            if node_name in node_id:
                return data
        return None
