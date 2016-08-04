# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Generates Sphinx documentation extracted from configman things.

It'll pull out the class docstring as well as configuration requirements, throw
it all in a blender and spit it out.

To configure Sphinx, add ``'configmandoc'`` to the ``extensions`` in
``conf.py``::

    extensions = [
        ...
        'configmandoc'
    ]


Can be used in an ``.rst`` file to document a specific class. For example::

    .. autoconfigman:: collector.external.boto.crashstorage.BotoS3CrashStorage

"""
import sys

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import ViewList
from sphinx.util.docstrings import prepare_docstring

from configman.namespace import Namespace, Option, Aggregation


def split_clspath(clspath):
    """Simple split of clspath into module and class names

    Note: This is a really simplistic implementation.

    """
    return clspath.rsplit('.', 1)


def import_class(clspath):
    """Given a clspath, returns the class

    Note: This is a really simplistic implementation.

    """
    modpath, clsname = split_clspath(clspath)
    __import__(modpath)
    module = sys.modules[modpath]
    return getattr(module, clsname)


class AutoConfigmanDirective(Directive):
    has_content = True
    required_arguments = 1
    optional_arguments = 0

    def add_line(self, line, source, *lineno):
        """Add a line to the result"""
        self.result.append(line, source, *lineno)

    def generate_docs(self, clspath, more_content):
        """Generate documentation for this configman class"""
        obj = import_class(clspath)
        sourcename = 'docstring of %s' % clspath

        # Add the header
        modname, clsname = split_clspath(clspath)
        self.add_line('.. %s:%s:: %s.%s' % ('py', 'class', modname, clsname), sourcename)
        self.add_line('', sourcename)

        # Add the docstring if there is one
        docstring = getattr(obj, '__doc__', None)
        if docstring:
            docstringlines = prepare_docstring(docstring, ignore=1)
            for i, line in enumerate(docstringlines):
                self.add_line('    ' + line, sourcename, i)
            self.add_line('', '')

        # Add additional content from the directive if there was any
        if more_content:
            for line, src in zip(more_content.data, more_content.items):
                self.add_line('    ' + line, src[0], src[1])
            self.add_line('', '')

        # Add configman related content
        namespace = Namespace()
        for cls in reversed(obj.__mro__):
            try:
                namespace.update(cls.required_config)
            except AttributeError:
                pass

        if namespace:
            self.add_line('    Configuration:', '')
            self.add_line('', '')

            sourcename = 'class definition'
            def generate_namespace_docs(namespace, basename=''):
                for name, value in namespace.iteritems():
                    if isinstance(value, Namespace):
                        generate_namespace_docs(value, name + '_')
                    elif isinstance(value, Option):
                        self.add_line('        ``%s``' % (basename + value.name), sourcename)
                        self.add_line('            :default: ``%r``' % value.default, sourcename)
                        self.add_line('            :converter: %r' % value.from_string_converter, sourcename)
                        if value.reference_value_from:
                            self.add_line('            :base: ``%s``' % (value.reference_value_from + '.' + value.name), sourcename)
                        self.add_line('', '')
                        self.add_line('            %s' % value.doc, sourcename)
                        self.add_line('', '')
                    elif isinstance(value, Aggregation):
                        # Ignore aggregations--they're for setting something up
                        # using a bunch of configuratino things (I think)
                        pass
                    else:
                        raise Exception('No idea what to do with %r' % value)

            generate_namespace_docs(namespace)

    def run(self):
        self.reporter = self.state.document.reporter
        self.result = ViewList()
        env = self.state.document.settings.env

        self.generate_docs(self.arguments[0], self.content)

        if not self.result:
            return []

        node = nodes.paragraph()
        node.document = self.state.document
        self.state.nested_parse(self.result, 0, node)
        return node.children


def setup(app):
    app.add_directive('autoconfigman', AutoConfigmanDirective)
