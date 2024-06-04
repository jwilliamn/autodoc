
from IPython import get_ipython
from IPython.utils import capture
from IPython.core import magic_arguments
from IPython.core.displayhook import DisplayHook
from IPython.core.magic import (Magics, magics_class, line_magic,
                                cell_magic, line_cell_magic)

from IPython.display import Markdown, Latex, Image
from base import template

import pandas as pd

import sys
from io import StringIO, BytesIO
from base64 import b64decode
import os.path


__all__ = ["MagicTools"]

#-----------------------------------------------------------------------------
# Classes and functions
#-----------------------------------------------------------------------------

class RichOutput(object):
    def __init__(self, data=None, metadata=None, transient=None, update=False):
        self.data = data or {}
        self.metadata = metadata or {}
        self.transient = transient or {}
        self.update = update

    def display(self):
        from IPython.display import publish_display_data
        publish_display_data(data=self.data, metadata=self.metadata,
                             transient=self.transient, update=self.update)

    def _repr_mime_(self, mime):
        if mime not in self.data:
            return
        data = self.data[mime]
        if mime in self.metadata:
            return data, self.metadata[mime]
        else:
            return data

    def _repr_mimebundle_(self, include=None, exclude=None):
        return self.data, self.metadata

    def _repr_html_(self):
        return self._repr_mime_("text/html")

    def _repr_latex_(self):
        return self._repr_mime_("text/latex")

    def _repr_json_(self):
        return self._repr_mime_("application/json")

    def _repr_javascript_(self):
        return self._repr_mime_("application/javascript")

    def _repr_png_(self):
        return self._repr_mime_("image/png")

    def _repr_jpeg_(self):
        return self._repr_mime_("image/jpeg")

    def _repr_svg_(self):
        return self._repr_mime_("image/svg+xml")


class CapturedIO(object):
    """Simple object for containing captured stdout/err and rich display StringIO objects

    Each instance `c` has three attributes:

    - ``c.stdout`` : standard output as a string
    - ``c.stderr`` : standard error as a string
    - ``c.outputs``: a list of rich display outputs

    Additionally, there's a ``c.show()`` method which will print all of the
    above in the same order, and can be invoked simply via ``c()``.
    """

    def __init__(self, stdout, stderr, outputs=None):
        self._stdout = stdout
        self._stderr = stderr
        if outputs is None:
            outputs = []
        self._outputs = outputs

    def __str__(self):
        return self.stdout

    @property
    def stdout(self):
        "Captured standard output"
        if not self._stdout:
            return ''
        return self._stdout.getvalue()

    @property
    def stderr(self):
        "Captured standard error"
        if not self._stderr:
            return ''
        return self._stderr.getvalue()

    @property
    def outputs(self):
        """A list of the captured rich display outputs, if any.

        If you have a CapturedIO object ``c``, these can be displayed in IPython
        using::

            from IPython.display import display
            for o in c.outputs:
                display(o)
        """
        return [ RichOutput(**kargs) for kargs in self._outputs ]

    def show(self):
        """write my output to sys.stdout/err as appropriate"""
        sys.stdout.write(self.stdout)
        sys.stderr.write(self.stderr)
        sys.stdout.flush()
        sys.stderr.flush()
        for kargs in self._outputs:
            RichOutput(**kargs).display()

    __call__ = show


class capture_output(object):
    """context manager for capturing stdout/err"""
    stdout = True
    stderr = True
    display = True

    def __init__(self, stdout=True, stderr=True, display=True):
        self.stdout = stdout
        self.stderr = stderr
        self.display = display
        self.shell = None

    def __enter__(self):
        from IPython.core.getipython import get_ipython
        from IPython.core.displaypub import CapturingDisplayPublisher
        from IPython.core.displayhook import CapturingDisplayHook

        self.sys_stdout = sys.stdout
        self.sys_stderr = sys.stderr

        if self.display:
            self.shell = get_ipython()
            if self.shell is None:
                self.save_display_pub = None
                self.display = False

        stdout = stderr = outputs = None
        if self.stdout:
            stdout = sys.stdout = StringIO()
        if self.stderr:
            stderr = sys.stderr = StringIO()
        if self.display:
            self.save_display_pub = self.shell.display_pub
            self.shell.display_pub = CapturingDisplayPublisher()
            outputs = self.shell.display_pub.outputs
            self.save_display_hook = sys.displayhook
            sys.displayhook = CapturingDisplayHook(shell=self.shell,
                                                   outputs=outputs)

        return CapturedIO(stdout, stderr, outputs)

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self.sys_stdout
        sys.stderr = self.sys_stderr
        if self.display and self.shell:
            self.shell.display_pub = self.save_display_pub
            sys.displayhook = self.save_display_hook



    
@magics_class
class MagicTools(Magics):
    
    @magic_arguments.magic_arguments()
    @magic_arguments.argument(
        'output', type=str, default='', nargs='?',
        help=("Add an output name"),
    )
    @magic_arguments.argument('--no-stderr', action="store_true",
            help="""Don't capture stderr."""
    )
    @magic_arguments.argument('--no-stdout', action="store_true",
        help="""Don't capture stdout."""
    )
    @magic_arguments.argument('--no-display', action="store_true",
        help="""Don't capture IPython's rich display."""
    )
    @magic_arguments.argument('--fname', type=str, default='autoDoc.md',
        help="""Add file name."""
    )
    @magic_arguments.argument('--iname', type=str, default='',
        help="""Add image name."""
    )
    @cell_magic
    def capture_auto(self, line, cell):
        """run the cell, capturing stdout, stderr, and IPython's rich display() calls.
            and at the same time shows the output cell
        """
        args = magic_arguments.parse_argstring(self.capture_auto, line)
        print('The output of this cell will be part of your documentation\n')
        out = not args.no_stdout
        err = not args.no_stderr
        disp = not args.no_display
        
        self.fname = args.fname
        self.shell.run_cell(cell)
        with capture.capture_output(out, err, disp) as io:
            self.shell.run_cell(cell)
            
        if DisplayHook.semicolon_at_end_of_expression(cell):
            if args.output in self.shell.user_ns:
                del self.shell.user_ns[args.output]
        elif args.output:
            self.shell.user_ns[args.output] = io


        auto_doc.raw_input(args, io)

        
def load_ipython_extension(magic):
    """
    Any module file that define a function named `load_ipython_extension`
    can be loaded via `%load_ext module.path` or be configured to be
    autoloaded by IPython at startup time.
    """
    # You can register the class itself without instantiating it.  IPython will
    # call the default constructor on it.
    # ipython.register_magics(MagicTools)
    get_ipython().register_magics(magic)

    
    
class AutoDoc():
    """Objet that will write the document for you 

    
    Parameters
    ----------
    outputs : output objects

    ``write_doc()`` is the main function which will write all it receives 
    from the notebook in the same order.
    """

    def __init__(self, outputs: list['str'] | None = None) -> None:
        if outputs is None:
            outputs = []
        self._outputs = outputs
        self.fname = None
        self.iname = None
        self._table = None
        self._image = False
        self._body = ''

    def __str__(self):
        return self.stdout
    
    def raw_input(self, args = None, io = None) -> None:
        self.fname = args.fname
        self.iname = args.iname
        
        if 'text' in args.output and not io.outputs:
            self._body = io.stdout
            self.write_doc(self._body)
        
        if 'text' in args.output and io.outputs:
            if io.stdout:
                self._body = io.stdout
            self._body += io.outputs[0].data['text/plain']
            self.write_doc(self._body)
            
        if 'table' in args.output and io.stdout:
            self._body = io.stdout
            self.write_doc(self._body)
            
        if 'image' in args.output and io.outputs:
            if io.stdout:
                self._body = io.stdout
                self.write_doc(self._body)
                
            self._image = io.outputs[0].data['image/png']
            if len(self._image) > 0:
                self.convert_image(self._image)
    
    def include(self, df: pd.DataFrame | None):
        table = df.to_markdown()
        self._table = table
        
    def convert_image(self, image: str | None):
        png_bytes = b64decode(image)
        if self.iname is None or len(self.iname) == 0:
            self.iname = 'image1.png'
            os.makedirs('img', exist_ok=True)
            if os.path.isfile(os.path.join('img', self.iname)):
                numfiles = [int(f[-5]) for f in os.listdir('img') if os.path.isfile(os.path.join('img', f))]
                #num = int(self.iname[-5]) + 1
                num = max(numfiles) + 1
                self.iname = 'image' + str(num) + '.png'
        with open(os.path.join('img', self.iname), "wb") as png:
            png.write(png_bytes)
            self._image = True
            self.write_doc(chunk='')
        

    #@property
    def write_doc(self, chunk: str | None):
        "Generate markdown"
        doc = Markdown(f'''
{chunk if len(self._body) > 0 else ''}

{self._table if self._table is not None else ''}

{'![Alt text](img/' + self.iname + ')' if self._image else ''}
        ''')
        
        #writting markdown file
        mode = 'a' if os.path.isfile(self.fname) else 'w'
        with open(self.fname, mode, encoding='utf-8') as file:
            if mode == 'w':
                file.write(template + doc.data)
            else: file.write(doc.data)
                
        self._table = None
        self._image = False
        self._body = ''
            
            
auto_doc = AutoDoc()