
import json

def markdown_to_json_structure(markdown_string):
    """
    Parses a markdown string with nested lists (using '-') into a JSON structure for Markmap.
    """
    lines = markdown_string.strip().split('\n')
    
    if not lines:
        return {}

    # The first line is the title
    root_content = lines[0].strip().replace("# ", "")
    root = {'content': root_content, 'children': []}
    
    # This stack will store tuples of (node, indentation_level)
    # We start with the root at a conceptual indentation level of -1
    stack = [(root, -1)]

    for line in lines[1:]:
        stripped_line = line.strip()
        if not stripped_line:
            continue

        # Calculate indentation based on leading spaces
        indentation = len(line) - len(line.lstrip(' '))
        
        # Remove the list marker (e.g., '- ')
        content = stripped_line.lstrip('- ').strip()
        new_node = {'content': content, 'children': []}

        # Find the correct parent for the new node based on indentation
        while stack and stack[-1][1] >= indentation:
            stack.pop()

        # The top of the stack is the parent
        parent_node, _ = stack[-1]
        parent_node['children'].append(new_node)

        # Push the new node onto the stack
        stack.append((new_node, indentation))

    return root

def create_markmap_html(markdown_string):
    """
    Generates a self-contained HTML file with a Markmap from a markdown string.
    """
    markmap_json = markdown_to_json_structure(markdown_string)
    json_data = json.dumps(markmap_json, indent=2)

    html_template = f"""
<!doctype html>
<html>
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="X-UA-Compatible" content="ie=edge" />
  <title>Markmap</title>
  <style>
    * {{
      margin: 0;
      padding: 0;
    }}
    html {{
      font-family: ui-sans-serif, system-ui, sans-serif, 'Apple Color Emoji',
        'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji';
    }}
    #mindmap {{
      display: block;
      width: 100vw;
      height: 100vh;
    }}
    .markmap-dark {{
      background: #27272a;
      color: white;
    }}
  </style>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/markmap-toolbar@0.18.12/dist/style.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11.11.1/styles/default.min.css">
</head>
<body>
  <svg id="mindmap"></svg>

  <script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/markmap-view@0.18.12/dist/browser/index.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/markmap-toolbar@0.18.12/dist/index.js"></script>

  <script>
    (r => {{ setTimeout(r); }})(function renderToolbar() {{
      const {{ markmap, mm }} = window;
      const {{ el }} = markmap.Toolbar.create(mm);
      el.setAttribute('style', 'position:absolute;bottom:20px;right:20px');
      document.body.append(el);
    }});
  </script>

  <script>
    ((getMarkmap, getOptions, root, jsonOptions) => {{
      const markmap = getMarkmap();
      window.mm = markmap.Markmap.create(
        "svg#mindmap",
        (getOptions || markmap.deriveOptions)(jsonOptions),
        root
      );
      if (window.matchMedia("(prefers-color-scheme: dark)").matches) {{
        document.documentElement.classList.add("markmap-dark");
      }}
    }}) pretence() => window.markmap, null, {json_data});
  </script>
</body>
</html>
"
    return html_template

if __name__ == '__main__':
    markdown_input = """
# My Awesome Project
- ## Backend
  - Python
  - FastAPI
- ## Frontend
  - React
  - TypeScript
- ## Database
  - PostgreSQL
"""
    html_output = create_markmap_html(markdown_input)
    
    with open('markmap_output.html', 'w') as f:
        f.write(html_output)
        
    print("Successfully generated markmap_output.html")
