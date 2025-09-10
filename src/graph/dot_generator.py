import networkx as nx
from collections import defaultdict

class DotGenerator:
    def __init__(self):
        self.dot_string = ""
        self.node_filter = None
        self.edge_filter = None

    def _add_node_to_dot(self, node_id, node_data):
        node_type = node_data.get("type", "unknown")
        if self.node_filter and node_type not in self.node_filter:
            return

        name = node_data.get("name", node_id)
        label = f"{name}"
        shape = "box"
        color = "black"
        style = "filled"
        fillcolor = "white"

        if node_type == "module":
            shape = "folder"
            fillcolor = "#ADD8E6"  # LightBlue
        elif node_type == "class":
            shape = "component"
            fillcolor = "#90EE90"  # LightGreen
        elif node_type == "function" or node_type == "method":
            shape = "ellipse"
            fillcolor = "#FFD700"  # Gold

        docstring = node_data.get("docstring")
        if docstring and docstring.strip():
            label += f"\n({docstring.strip().splitlines()[0]})"

        self.dot_string += f'  "{node_id}" [label="{label}", shape={shape}, style={style}, fillcolor="{fillcolor}", type="{node_type}"];\n'

    def _add_edge_to_dot(self, source_id, target_id, edge_data):
        edge_type = edge_data.get("type", "unknown")
        if self.edge_filter and edge_type not in self.edge_filter:
            return

        label = edge_type
        color = "black"
        style = "solid"

        if edge_type == "CALLS":
            color = "blue"
            style = "bold"
        elif edge_type == "IMPORTS":
            color = "green"
            style = "dashed"
        elif edge_type == "CONTAINS":
            color = "gray"
            style = "dotted"
            label = ""
        elif edge_type == "INHERITS":
            color = "purple"
            style = "solid"

        self.dot_string += f'  "{source_id}" -> "{target_id}" [label="{label}", color="{color}", style={style}, type="{edge_type}"];\n'

    def _add_clustered_nodes_to_dot(self, graph: nx.DiGraph):
        modules = defaultdict(list)
        for node_id, node_data in graph.nodes(data=True):
            if node_data.get("type") == "module":
                continue
            
            module_name = node_id.split(".")[0]
            modules[module_name].append((node_id, node_data))

        for module_name, nodes in modules.items():
            self.dot_string += f'  subgraph "cluster_{module_name}" {{\n
            self.dot_string += f'    label = "{module_name}";\n
            self.dot_string += '    style = "filled";\n
            self.dot_string += '    color = "lightgrey";\n
            

            for node_id, node_data in nodes:
                self._add_node_to_dot(node_id, node_data)
            

            self.dot_string += '  }}\n'

    def generate_dot(self, graph: nx.DiGraph, node_filter: list = None, edge_filter: list = None, cluster_modules: bool = False) -> str:
        self.dot_string = "digraph CodeFlow {\n"
        self.dot_string += "  rankdir=LR;\n"
        self.dot_string += "  node [shape=box];\n"
        
        self.node_filter = node_filter
        self.edge_filter = edge_filter

        if cluster_modules:
            self._add_clustered_nodes_to_dot(graph)
            # Add module nodes separately if they are in the filter
            if self.node_filter and "module" in self.node_filter:
                 for node_id, node_data in graph.nodes(data=True):
                    if node_data.get("type") == "module":
                        self._add_node_to_dot(node_id, node_data)
        else:
            for node_id, node_data in graph.nodes(data=True):
                self._add_node_to_dot(node_id, node_data)

        for source, target, edge_data in graph.edges(data=True):
            self._add_edge_to_dot(source, target, edge_data)

        self.dot_string += "}\n"
        return self.dot_string