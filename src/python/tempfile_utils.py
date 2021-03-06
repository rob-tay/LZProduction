import os
from textwrap import dedent
from string import Template
from tempfile import NamedTemporaryFile
from contextlib import contextmanager
import jinja2
from git import Git

@contextmanager
def temporary_runscript(**kwargs):
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bash')
    template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=templates_dir))
    with NamedTemporaryFile(prefix='runscript_', suffix='.sh') as tmpfile:
        tmpfile.write(template_env.get_template('Simulation.bash').render(**kwargs))
        tmpfile.flush()
        yield tmpfile


@contextmanager
def temporary_macro(tag, macro, app, nevents):
    app_map = {'BACCARAT': 'Bacc'}
    macro_extras = Template(dedent("""
        /control/getEnv SEED
        /$app/randomSeed {SEED}
        /$app/beamOn $nevents
        exit
        """))
    lzprod_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    git_dir = os.path.join(lzprod_root, 'git', 'TDRAnalysis')
    macro = os.path.join(git_dir, macro)
    git = Git(git_dir)
    git.fetch('origin')
    git.checkout(tag)
    if not os.path.isfile(macro):
        raise Exception("Macro file '%s' doesn't exist in tag %s" % (macro, tag))

    with NamedTemporaryFile(prefix=os.path.splitext(os.path.basename(macro))[0] + '_',
                            suffix='.mac') as tmpfile:
        with open(macro, 'rb') as macro_file:
            tmpfile.write(macro_file.read())
        tmpfile.write(macro_extras.safe_substitute(app=app_map.get(app, app), nevents=nevents))
        tmpfile.flush()
        yield tmpfile

