
import difflib
import streamlit.components.v1 as components

class CodeDiffViewer:
    def __init__(self, old_code, new_code):
        self.old_code = old_code
        self.new_code = new_code

    def generate_diff_html(self):
        diff = difflib.HtmlDiff(wrapcolumn=80).make_file(
            self.old_code.splitlines(),
            self.new_code.splitlines(),
            fromdesc="Original Code",
            todesc="Modified Code",
        )
        return diff

    def show_diff(self):
        diff_html = self.generate_diff_html()
        components.html(diff_html, height=600, scrolling=True)
