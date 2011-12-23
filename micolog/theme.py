# -*- coding: utf-8 -*-
import  os,sys,stat
#os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import wsgiref.handlers
from mimetypes import types_map
from datetime import  timedelta
from google.appengine.ext.webapp import template
from google.appengine.ext.zipserve import *
sys.path.append('modules')
from model import *
from settings import *

# Handlers

cwd = os.getcwd()
theme_path = os.path.join(cwd, 'themes')
file_modifieds={}

max_age = 600  #expires in 10 minutes

class Theme:
    def __init__(self, name='default'):
        self.name = name
        self.mapping_cache = {}
        self.dir = '/themes/%s' % name
        self.viewdir = os.path.join(ROOT_PATH, 'view')
        self.server_dir = os.path.join(ROOT_PATH, 'themes', self.name)
        if os.path.exists(self.server_dir):
            self.isZip = False
        else:
            self.isZip = True
            self.server_dir = self.server_dir+".zip"
        #self.server_dir=os.path.join(self.server_dir,"templates")
        logging.debug('server_dir:%s'%self.server_dir)

    def __getattr__(self, name):
        if self.mapping_cache.has_key(name):
            return self.mapping_cache[name]
        else:

            path = "/".join((self.name, 'templates', name + '.html'))
            logging.debug('path:%s'%path)
##                      if not os.path.exists(path):
##                              path = os.path.join(rootpath, 'themes', 'default', 'templates', name + '.html')
##                              if not os.path.exists(path):
##                                      path = None
            self.mapping_cache[name] = path
            return path

class ThemeIterator:
    def __init__(self, theme_path='themes'):
        self.iterating = False
        self.theme_path = theme_path
        self.list = []

    def __iter__(self):
        return self

    def next(self):
        if not self.iterating:
            self.iterating = True
            self.list = os.listdir(self.theme_path)
            self.cursor = 0

        if self.cursor >= len(self.list):
            self.iterating = False
            raise StopIteration
        else:
            value = self.list[self.cursor]
            self.cursor += 1
            if value.endswith('.zip'):
                value = value[:-4]
            return value

def Error404(handler):
    handler.response.set_status(404)
    html = template.render(os.path.join(cwd,'views/404.html'), {'error':404})
    handler.response.out.write(html)


class GetFile(webapp.RequestHandler):
    def get(self,prefix,name):
        request_path = self.request.path[8:]


        server_path = os.path.normpath(os.path.join(cwd, 'themes', request_path))
        try:
            fstat=os.stat(server_path)
        except:
            #use zipfile
            theme_file=os.path.normpath(os.path.join(cwd, 'themes', prefix))
            if os.path.exists(theme_file+".zip"):
                #is file exist?
                fstat=os.stat(theme_file+".zip")
                zipdo=ZipHandler()
                zipdo.initialize(self.request,self.response)
                return zipdo.get(theme_file,name)
            else:
                Error404(self)
                return


        fmtime=datetime.fromtimestamp(fstat[stat.ST_MTIME])
        if self.request.if_modified_since and self.request.if_modified_since.replace(tzinfo=None) >= fmtime:
            self.response.headers['Date'] = format_date(datetime.utcnow())
            self.response.headers['Last-Modified'] = format_date(fmtime)
            cache_expires(self.response, max_age)
            self.response.set_status(304)
            self.response.clear()

        elif server_path.startswith(theme_path):
            ext = os.path.splitext(server_path)[1]
            if types_map.has_key(ext):
                mime_type = types_map[ext]
            else:
                mime_type = 'application/octet-stream'
            try:
                self.response.headers['Content-Type'] = mime_type
                self.response.headers['Last-Modified'] = format_date(fmtime)
                cache_expires(self.response, max_age)
                self.response.out.write(open(server_path, 'rb').read())
            except Exception, e:
                Error404(self)
        else:
            Error404(self)

class NotFound(webapp.RequestHandler):
    def get(self):
         Error404(self)

#}}}

def format_date(dt):
    return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')

def cache_expires(response, seconds=0, **kw):
    """
    Set expiration on this request.  This sets the response to
    expire in the given seconds, and any other attributes are used
    for cache_control (e.g., private=True, etc).

    this function is modified from webob.Response
    it will be good if google.appengine.ext.webapp.Response inherits from this class...
    """
    if not seconds:
        # To really expire something, you have to force a
        # bunch of these cache control attributes, and IE may
        # not pay attention to those still so we also set
        # Expires.
        response.headers['Cache-Control'] = 'max-age=0, must-revalidate, no-cache, no-store'
        response.headers['Expires'] = format_date(datetime.utcnow())
        if 'last-modified' not in self.headers:
            self.last_modified = format_date(datetime.utcnow())
        response.headers['Pragma'] = 'no-cache'
    else:
        response.headers['Cache-Control'] = 'max-age=%d' % seconds
        response.headers['Expires'] = format_date(datetime.utcnow() + timedelta(seconds=seconds))

def main():
    application = webapp.WSGIApplication(
            [
                ('/themes/[\\w\\-]+/templates/.*', NotFound),
                ('/themes/(?P<prefix>[\\w\\-]+)/(?P<name>.+)', GetFile),
                ('.*', NotFound),
                ],
            debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
    main()

