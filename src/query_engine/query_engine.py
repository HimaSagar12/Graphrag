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

    def find_nodes_reading_var(self, var_name):
        readers = []
        for source, target, data in self.graph.edges(data=True):
            if data.get("type") == "READS_VAR" and f"var:{var_name}" == target:
                readers.append(self.graph.nodes[source])
        return readers

    def find_nodes_writing_var(self, var_name):
        writers = []
        for source, target, data in self.graph.edges(data=True):
            if data.get("type") == "WRITES_VAR" and f"var:{var_name}" == target:
                writers.append(self.graph.nodes[source])
        return writers

    def find_nodes_throwing_exception(self):
        throwers = []
        for source, target, data in self.graph.edges(data=True):
            if data.get("type") == "THROWS_EXCEPTION":
                throwers.append(self.graph.nodes[source])
        return throwers

    def find_nodes_handling_exception(self):
        handlers = []
        for source, target, data in self.graph.edges(data=True):
            if data.get("type") == "HANDLES_EXCEPTION":
                handlers.append(self.graph.nodes[source])
        return handlers

    def find_nodes_with_decorator(self, decorator_name):
        decorated_nodes = []
        for source, target, data in self.graph.edges(data=True):
            if data.get("type") == "HAS_DECORATOR" and f"decorator:{decorator_name}" == target:
                decorated_nodes.append(self.graph.nodes[source])
        return decorated_nodes

    def find_nodes_returning_value(self):
        returners = []
        for source, target, data in self.graph.edges(data=True):
            if data.get("type") == "RETURNS_VALUE":
                returners.append(self.graph.nodes[source])
        return returners

    def find_nodes_using_service(self, service_name):
        users = []
        for source, target, data in self.graph.edges(data=True):
            if data.get("type") == "USES_SERVICE" and f"external_service:{service_name}" == target:
                users.append(self.graph.nodes[source])
        return users
