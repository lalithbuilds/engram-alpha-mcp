import ast
import json

with open('src/engram/server.py', 'r') as f:
    tree = ast.parse(f.read())

tools = []
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        for decorator in node.decorator_list:
            if hasattr(decorator, 'func') and hasattr(decorator.func, 'attr'):
                if decorator.func.attr == 'tool':
                    args = [(arg.arg, arg.annotation.id if hasattr(arg.annotation, 'id') else None) for arg in node.args.args]
                    tools.append({'name': node.name, 'args': args, 'doc': ast.get_docstring(node)})

print(json.dumps(tools, indent=2))
