"""Git tag service."""
import os
import threading
from collections import namedtuple
import cherrypy
import pylru
from git import Git, Repo
from natsort import natsorted

Macro = namedtuple('Macro', ('name', 'path'))

macro_dir_map = {'LUXSim': 'BackgroundMacros',
                 'BACCARAT': 'BaccValidationMacros'}

@cherrypy.popargs('tagid', 'app')
class GitTagMacros(object):
    """
    Git tag checking service.

    Service for reporting the macros associated to a given git tag
    or returning list of available tags.
    """

    def __init__(self, repo, git_dir, template_env):
        """Initialisation."""
        if not os.path.isdir(git_dir):
            Git().clone(repo, git_dir)
        Git(git_dir).fetch()  # this introduces a slight delay if done in index. May be acceptible
        self.git_dir = git_dir
        self.fs_lock = threading.Lock()
        self.tag_cache = pylru.lrucache(50)
        self.template = template_env.get_template("html/gittags.html")

    @cherrypy.expose
    def index(self, tagid=None, app='LUXSim'):
        """Return the index page."""
        print "IN GitTagMacro: tagid=(%s), app=(%s)" % (tagid, app)
        cache_key = app + '::' + str(tagid)
        if cache_key in self.tag_cache:
            return self.tag_cache[cache_key]

        if tagid is None:
            tags = natsorted((tag.name for tag in Repo(self.git_dir).tags), reverse=True)
            return self.template.render({'tags': tags})

        if app not in macro_dir_map:
            return ''

        with self.fs_lock:
            Git(self.git_dir).checkout(tagid)
            macros = (Macro(name=os.path.splitext(file_)[0],
                            path=os.path.relpath(os.path.join(root, file_), self.git_dir))
                      for root, _, files in os.walk(os.path.join(self.git_dir, macro_dir_map[app]))
                      for file_ in files if file_.endswith('.mac'))

            html = self.template.render({'macros': macros})
            # print "returning:", str(html)
            self.tag_cache[cache_key] = html
            return html
