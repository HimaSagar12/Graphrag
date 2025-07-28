import ast
import os

class PythonCodeParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.nodes = []
        self.edges = []
        self.current_module_id = os.path.basename(file_path)
        self.nodes.append({
            "id": self.current_module_id,
            "type": "module",
            "name": os.path.basename(file_path).replace(".py", ""),
            "file_path": file_path,
            "line_number": 1,
            "docstring": None
        })

    def _add_node(self, node_type, name, line_number, parent_id=None, docstring=None):
        node_id = f"{self.current_module_id}:{name}"
        self.nodes.append({
            "id": node_id,
            "type": node_type,
            "name": name,
            "file_path": self.file_path,
            "line_number": line_number,
            "docstring": docstring
        })
        if parent_id:
            self._add_edge(parent_id, node_id, "CONTAINS", line_number)
        return node_id

    def _add_edge(self, source_id, target_id, edge_type, line_number=None):
        self.edges.append({
            "source": source_id,
            "target": target_id,
            "type": edge_type,
            "line_number": line_number
        })

    def parse(self):
        with open(self.file_path, "r") as f:
            tree = ast.parse(f.read(), filename=self.file_path)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                node_id = self._add_node("function", node.name, node.lineno, self.current_module_id, ast.get_docstring(node))
                for sub_node in ast.walk(node):
                    if isinstance(sub_node, ast.Call):
                        if isinstance(sub_node.func, ast.Name):
                            self._add_edge(node_id, f"{self.current_module_id}:{sub_node.func.id}", "CALLS", sub_node.lineno)
                        elif isinstance(sub_node.func, ast.Attribute):
                            # Handle method calls (e.g., obj.method()) - simplified for now
                            self._add_edge(node_id, f"{self.current_module_id}:{sub_node.func.attr}", "CALLS", sub_node.lineno)
            elif isinstance(node, ast.ClassDef):
                class_id = self._add_node("class", node.name, node.lineno, self.current_module_id, ast.get_docstring(node))
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        self._add_edge(class_id, f"{self.current_module_id}:{base.id}", "INHERITS", node.lineno)
                for sub_node in ast.walk(node):
                    if isinstance(sub_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_id = self._add_node("method", sub_node.name, sub_node.lineno, class_id, ast.get_docstring(sub_node))
                        for call_node in ast.walk(sub_node):
                            if isinstance(call_node, ast.Call):
                                if isinstance(call_node.func, ast.Name):
                                    self._add_edge(method_id, f"{self.current_module_id}:{call_node.func.id}", "CALLS", call_node.lineno)
                                elif isinstance(call_node.func, ast.Attribute):
                                    self._add_edge(method_id, f"{self.current_module_id}:{call_node.func.attr}", "CALLS", call_node.lineno)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self._add_edge(self.current_module_id, alias.name, "IMPORTS", node.lineno)
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module if node.module else ""
                for alias in node.names:
                    self._add_edge(self.current_module_id, f"{module_name}.{alias.name}", "IMPORTS", node.lineno)

        return {"nodes": self.nodes, "edges": self.edges}
