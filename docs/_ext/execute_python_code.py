"""
A Sphinx extension to execute Python code blocks and insert their output into the documentation.

Usage in conf.py:
    extensions = [
        ...
        'execute_python_code',
        ...
    ]
Usage in .rst files:
    .. exec::
        print("Hello, World!")
        for i in range(3):
            print(f"Line {i}")

With tab width option, defining how many spaces a tab character represents:
    .. exec::
        :tab-width: 4

        print("Hello, World!")
        for i in range(3):
            print(f"Line {i}")
"""
import io
import sys
from os.path import basename

from docutils import nodes, statemachine

# Configuration file for the Sphinx documentation builder.
from docutils.parsers.rst import Directive


class ExecPythonCodeDirective(Directive):
    """Directive to execute the specified python code and insert the output into the document"""

    has_content = True

    def run(self):
        oldStdout, sys.stdout = sys.stdout, io.StringIO()

        tab_width = self.options.get(
            "tab-width", self.state.document.settings.tab_width
        )
        source = self.state_machine.input_lines.source(
            self.lineno - self.state_machine.input_offset - 1
        )

        try:
            exec("\n".join(self.content))
            text = sys.stdout.getvalue()
            lines = statemachine.string2lines(text, tab_width, convert_whitespace=True)
            self.state_machine.insert_input(lines, source)
            return []
        except Exception:
            return [
                nodes.error(
                    None,
                    nodes.paragraph(
                        text="Unable to execute python code at %s:%d:"
                        % (basename(source), self.lineno)
                    ),
                    nodes.paragraph(text=str(sys.exc_info()[1])),
                )
            ]
        finally:
            sys.stdout = oldStdout


def setup(app):
    app.add_directive("exec", ExecPythonCodeDirective)
    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
