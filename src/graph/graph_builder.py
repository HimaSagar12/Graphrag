import networkx as nx

class GraphBuilder:
    def __init__(self):
        self.graph = nx.DiGraph()

    def build_graph(self, parsed_data):
        # Add nodes
        for node_data in parsed_data["nodes"]:
            node_id = node_data.pop("id")
            self.graph.add_node(node_id, **node_data)

        # Add edges
        for edge_data in parsed_data["edges"]:
            source = edge_data.pop("source")
            target = edge_data.pop("target")
            self.graph.add_edge(source, target, **edge_data)
        
        return self.graph
