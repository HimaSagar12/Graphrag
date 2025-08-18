import networkx as nx

class DotGenerator:
    def __init__(self):
        self.dot_string = "digraph CodeFlow {\n"
        self.dot_string += "  rankdir=TB;\n"  # Top to Bottom layout
        self.dot_string += "  splines=ortho;\n"  # Use orthogonal lines for edges
        self.dot_string += "  node [shape=box, style=rounded];\n"

    def _add_node_to_dot(self, node_id, node_data):
        node_type = node_data.get("type", "unknown")
        name = node_data.get("name", node_id)
        label = f"<b>{name}</b>\n<font point-size='10'>{node_type}</font>"
        shape = "box"
        color = "#3498db"  # Blue
        style = "filled,rounded"
        fillcolor = "#ecf0f1"  # Light Gray

        if node_type == "module":
            shape = "tab"
            fillcolor = "#9b59b6"  # Purple
            color = "#8e44ad"
        elif node_type == "class":
            shape = "component"
            fillcolor = "#2ecc71"  # Green
            color = "#27ae60"
        elif node_type == "function" or node_type == "method":
            shape = "ellipse"
            fillcolor = "#f1c40f"  # Yellow
            color = "#f39c12"
        elif node_type.startswith("var:"):
            shape = "note"
            fillcolor = "#e67e22"  # Orange
            color = "#d35400"
            label = f"<b>{node_id.split(':', 1)[1]}</b>\n<font point-size='10'>Variable</font>"
        elif node_type == "external_service":
            shape = "cylinder"
            fillcolor = "#e74c3c"  # Red
            color = "#c0392b"
        
        docstring = node_data.get("docstring")
        if docstring:
            label += f"\n<font point-size='8'>{docstring.strip().splitlines()[0]}</font>"

        self.dot_string += f'  "{node_id}" [label=<{label}>, shape={shape}, style="{style}", fillcolor="{fillcolor}", color="{color}"];\n'

    def _add_edge_to_dot(self, source_id, target_id, edge_data):
        edge_type = edge_data.get("type", "unknown")
        label = edge_type
        color = "#7f8c8d"  # Gray
        style = "solid"
        arrowhead = "normal"

        if edge_type == "CALLS":
            color = "#2980b9"  # Dark Blue
            style = "bold"
        elif edge_type == "IMPORTS":
            color = "#16a085"  # Dark Green
            style = "dashed"
        elif edge_type == "CONTAINS":
            color = "#bdc3c7"  # Light Gray
            style = "dotted"
            arrowhead = "none"
        elif edge_type == "INHERITS":
            color = "#8e44ad"  # Dark Purple
            style = "solid"
            arrowhead = "empty"
        elif edge_type == "READS_VAR" or edge_type == "WRITES_VAR":
            color = "#d35400"  # Dark Orange
            style = "dashed"
        
        self.dot_string += f'  "{source_id}" -> "{target_id}" [label="{label}", color="{color}", style={style}, arrowhead={arrowhead}];\n'

    def generate_dot(self, graph: nx.DiGraph) -> str:
        # Add nodes
        for node_id, node_data in graph.nodes(data=True):
            self._add_node_to_dot(node_id, node_data)

        # Add edges
        for source, target, edge_data in graph.edges(data=True):
            self._add_edge_to_dot(source, target, edge_data)

        self.dot_string += "}\n"
        return self.dot_string

