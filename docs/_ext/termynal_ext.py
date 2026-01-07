"""
Sphinx extension for Termynal animated terminal windows.

This extension adds support for animated terminal windows in Sphinx documentation,
similar to what's used in Typer and FastAPI documentation.

Usage in conf.py:
    extensions = ['sphinx_termynal']

Usage in RST:
    .. termynal::

        $ pip install mypackage
        Successfully installed mypackage
        $ python
        Python 3.9.0
        >>> import mypackage

Or with a custom class:
    .. code-block:: bash
        :class: termy

        $ pip install mypackage
"""

import os
from pathlib import Path
from docutils import nodes
from docutils.parsers.rst import Directive, directives
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective


class TermynalNode(nodes.General, nodes.Element):
    """Node for termynal animated terminal."""
    pass


class TermynalDirective(SphinxDirective):
    """
    Directive for creating animated terminal windows.
    
    Example:
        .. termynal::
        
            $ echo "Hello World"
            Hello World
            $ python script.py
            ---> 100%
            Done!
    """
    has_content = True
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {
        'start-delay': directives.nonnegative_int,
        'type-delay': directives.nonnegative_int,
        'line-delay': directives.nonnegative_int,
    }

    def run(self):
        node = TermynalNode()
        node['content'] = '\n'.join(self.content)
        node['options'] = self.options
        return [node]


def visit_termynal_node_html(self, node):
    """Render termynal node as HTML."""
    content = node['content']
    options = node.get('options', {})
    
    # Build data attributes for options
    attrs = []
    if 'start-delay' in options:
        attrs.append(f'data-ty-startDelay="{options["start-delay"]}"')
    if 'type-delay' in options:
        attrs.append(f'data-ty-typeDelay="{options["type-delay"]}"')
    if 'line-delay' in options:
        attrs.append(f'data-ty-lineDelay="{options["line-delay"]}"')
    
    attrs_str = ' '.join(attrs)
    
    # Wrap in termynal container
    self.body.append(
        f'<div class="termy">'
        f'<div class="highlight">'
        f'<code>{self.encode(content)}</code>'
        f'</div>'
        f'</div>'
    )


def depart_termynal_node_html(self, node):
    """Close termynal node HTML."""
    pass


def add_termynal_files(app, pagename, templatename, context, doctree):
    """Add termynal CSS and JS files to the page."""
    # These will be added via app.add_css_file and app.add_js_file in setup
    pass




def setup(app: Sphinx):
    """Setup the Sphinx extension."""
    
    # Add the termynal directive
    app.add_directive('termynal', TermynalDirective)
    
    # Add node visit/depart functions
    app.add_node(
        TermynalNode,
        html=(visit_termynal_node_html, depart_termynal_node_html)
    )
    
    # Add CSS files
    app.add_css_file('css/termynal.css')
    app.add_css_file('css/custom.css')
    
    # Add JS files (termynal.js must be loaded before custom.js)
    app.add_js_file('js/termynal.js')
    app.add_js_file('js/custom.js')
    
    
    # Also support the 'termy' class on code-block directives
    # This is handled by the custom.js automatically
    
    return {
        'version': '0.1.0',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
