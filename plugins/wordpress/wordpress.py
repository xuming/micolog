from micolog_plugin import *
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue
from wp_import import *

class wordpress(Plugin_importbase):
    def __init__(self):
        Plugin_importbase.__init__(self,__file__,"wordpress","Import posts, pages, comments, categories, and tags from a WordPress export file.")
        self.author="xuming"
        self.authoruri="http://xuming.net"
        self.uri="http://xuming.net"
        self.description="Plugin for import wxr file."
        self.name="Wordpress Import"
        self.version="0.5"

    def get(self,page):
        return self.render_content("wpimport.html",{'name':self.name})

    def post(self,page):
        try:

            queue=taskqueue.Queue("import")
            wpfile=page.param('wpfile')
            #global imt
            imt=import_wordpress(wpfile)
            imt.parse()
            memcache.set("imt",imt)
            queue.add(taskqueue.Task( url="/admin/import_next"))
            return self.render_content("wpimport.html",{'postback':True})

        except:
            return self.error("Import Error")