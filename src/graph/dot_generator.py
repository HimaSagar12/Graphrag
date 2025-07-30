import networkx as nx

class DotGenerator:
    def __init__(self):
        self.dot_string = "digraph CodeFlow {\n"
        self.dot_string += "  rankdir=LR;\n" # Left to Right layout
        self.dot_string += "  node [shape=box];\n"

    def _add_node_to_dot(self, node_id, node_data):
        node_type = node_data.get("type", "unknown")
        name = node_data.get("name", node_id)
        label = f"{name}"
        shape = "box"
        color = "black"
        style = "filled"
        fillcolor = "white"

        if node_type == "module":
            shape = "folder"
            fillcolor = "#ADD8E6" # LightBlue
        elif node_type == "class":
            shape = "component"
            fillcolor = "#90EE90" # LightGreen
        elif node_type == "function" or node_type == "method":
            shape = "ellipse"
            fillcolor = "#FFD700" # Gold
        elif node_type.startswith("var:") or node_type.startswith("decorator:") or node_type.startswith("exception_at_line:") or node_type.startswith("try_block_at_line:") or node_type.startswith("return_value_at_line:"):
            shape = "note"
            fillcolor = "#FFC0CB" # Pink for auxiliary nodes
            label = node_id.split(":", 1)[1] # Show only the name part
        elif node_type == "external_service":
            shape = "cylinder"
            fillcolor = "#FFB6C1" # LightPink for external services

        # Add docstring if available
        docstring = node_data.get("docstring")
        if docstring:
            label += f"\\n({docstring.strip().splitlines()[0]})"; # First line of docstring

        self.dot_string += f"  \"{node_id}\" [label=\"{label}\", shape={shape}, style={style}, fillcolor=\"{fillcolor}\"];\n"

    def _add_edge_to_dot(self, source_id, target_id, edge_data):
        edge_type = edge_data.get("type", "unknown")
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
        elif edge_type == "READS_VAR":
            color = "orange"
            style = "solid"
        elif edge_type == "WRITES_VAR":
            color = "red"
            style = "solid"
        elif edge_type == "THROWS_EXCEPTION":
            color = "darkred"
            style = "dashed"
        elif edge_type == "HANDLES_EXCEPTION":
            color = "darkgreen"
            style = "dashed"
        elif edge_type == "HAS_DECORATOR":
            color = "brown"
            style = "dotted"
        elif edge_type == "RETURNS_VALUE":
            color = "darkblue"
            style = "solid"
        elif edge_type == "USES_SERVICE":
            color = "magenta"
            style = "bold"

        self.dot_string += f"  \"{source_id}\" -> \"{target_id}\" [label=\"{label}\", color=\"{color}\", style={style}];\n"

    def generate_dot(self, graph: nx.DiGraph) -> str:
        # Add nodes
        for node_id, node_data in graph.nodes(data=True):
            self._add_node_to_dot(node_id, node_data)

        # Add edges
        for source, target, edge_data in graph.edges(data=True):
            self._add_edge_to_dot(source, target, edge_data)

        self.dot_string += "}\n"
        return self.dot_string
