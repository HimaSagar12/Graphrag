import ast
import os
import yaml

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

    # def extract_nodes_from_ast(tree):
    #     nodes = []
    #     for node in ast.walk(tree):
    #         if isinstance(node, ast.FunctionDef):
    #             nodes.append({
    #                 "type": "function",
    #                 "name": node.name,
    #                 "lineno": node.lineno
    #             })
    #     return {"nodes": nodes, "edges": []}

    def extract_nodes_from_ast(tree):
        nodes = []
        for i, node in enumerate(ast.walk(tree)):
            if isinstance(node, ast.FunctionDef):
                nodes.append({
                    "id": f"func_{i}",  # ✅ Unique ID
                    "type": "function",
                    "name": node.name,
                    "lineno": node.lineno
                })
        return {"nodes": nodes, "edges": []}



    def _add_node(self, node_type, name, line_number, parent_id=None, docstring=None):
        node_id = f"{self.current_module_id}:{name}"
        # Ensure node is unique before adding
        if not any(n["id"] == node_id for n in self.nodes):
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
        # Ensure edge is unique before adding
        edge_tuple = (source_id, target_id, edge_type)
        if not any(e["source"] == source_id and e["target"] == target_id and e["type"] == edge_type for e in self.edges):
            self.edges.append({
                "source": source_id,
                "target": target_id,
                "type": edge_type,
                "line_number": line_number
            })

    def parse(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=self.file_path)
        
        # Add a global node for Snowflake connection if detected
        snowflake_detected = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if (isinstance(node, ast.Import) and any(alias.name == "snowflake.connector" for alias in node.names)) or \
                   (isinstance(node, ast.ImportFrom) and node.module == "snowflake" and any(alias.name == "connector" for alias in node.names)):
                    snowflake_detected = True
                    break
        
        if snowflake_detected:
            self.nodes.append({
                "id": "external_service:snowflake_connection",
                "type": "external_service",
                "name": "Snowflake Connection",
                "file_path": None,
                "line_number": None,
                "docstring": "Represents a connection to Snowflake database."
            })

        for node in ast.walk(tree):
            current_scope_id = self.current_module_id

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                node_id = self._add_node("function", node.name, node.lineno, current_scope_id, ast.get_docstring(node))
                current_scope_id = node_id

                # Decorators
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name):
                        self._add_edge(node_id, f"decorator:{decorator.id}", "HAS_DECORATOR", decorator.lineno)

                # Returns
                for sub_node in ast.walk(node):
                    if isinstance(sub_node, ast.Return):
                        self._add_edge(node_id, f"return_value_at_line:{sub_node.lineno}", "RETURNS_VALUE", sub_node.lineno)

            elif isinstance(node, ast.ClassDef):
                class_id = self._add_node("class", node.name, node.lineno, current_scope_id, ast.get_docstring(node))
                current_scope_id = class_id

                # Decorators
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name):
                        self._add_edge(class_id, f"decorator:{decorator.id}", "HAS_DECORATOR", decorator.lineno)

                for base in node.bases:
                    if isinstance(base, ast.Name):
                        self._add_edge(class_id, f"{self.current_module_id}:{base.id}", "INHERITS", node.lineno)

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self._add_edge(self.current_module_id, alias.name, "IMPORTS", node.lineno)
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module if node.module else ""
                for alias in node.names:
                    self._add_edge(self.current_module_id, f"{module_name}.{alias.name}", "IMPORTS", node.lineno)

            # Process nodes within functions/methods/classes for calls, reads, writes, exceptions, and external service usage
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                for sub_node in ast.iter_child_nodes(node):
                    if isinstance(sub_node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        # Skip nested definitions, handled by outer loop
                        continue

                    for item in ast.walk(sub_node):
                        if isinstance(item, ast.Call):
                            if isinstance(item.func, ast.Name):
                                self._add_edge(current_scope_id, f"{self.current_module_id}:{item.func.id}", "CALLS", item.lineno)
                            elif isinstance(item.func, ast.Attribute):
                                # Handle method calls (e.g., obj.method()) - simplified for now
                                self._add_edge(current_scope_id, f"{self.current_module_id}:{item.func.attr}", "CALLS", item.lineno)
                                
                                # Detect Snowflake connection usage
                                if isinstance(item.func.value, ast.Name) and item.func.value.id == "snowflake" and item.func.attr == "connector":
                                    self._add_edge(current_scope_id, "external_service:snowflake_connection", "USES_SERVICE", item.lineno)
                                elif isinstance(item.func.value, ast.Attribute) and item.func.value.attr == "connector" and item.func.attr == "connect":
                                    self._add_edge(current_scope_id, "external_service:snowflake_connection", "USES_SERVICE", item.lineno)

                        elif isinstance(item, ast.Name):
                            if isinstance(item.ctx, ast.Load):
                                # Variable read
                                var_id = f"var:{item.id}"
                                if not any(n["id"] == var_id for n in self.nodes):
                                    self.nodes.append({"id": var_id, "type": "variable", "name": item.id, "file_path": self.file_path, "line_number": item.lineno})
                                self._add_edge(current_scope_id, var_id, "READS_VAR", item.lineno)
                            elif isinstance(item.ctx, ast.Store):
                                # Variable write
                                var_id = f"var:{item.id}"
                                if not any(n["id"] == var_id for n in self.nodes):
                                    self.nodes.append({"id": var_id, "type": "variable", "name": item.id, "file_path": self.file_path, "line_number": item.lineno})
                                self._add_edge(current_scope_id, var_id, "WRITES_VAR", item.lineno)
                        elif isinstance(item, ast.Raise):
                            self._add_edge(current_scope_id, f"exception_at_line:{item.lineno}", "THROWS_EXCEPTION", item.lineno)
                        elif isinstance(item, ast.Try):
                            self._add_edge(current_scope_id, f"try_block_at_line:{item.lineno}", "HANDLES_EXCEPTION", item.lineno)

        return {"nodes": self.nodes, "edges": self.edges}