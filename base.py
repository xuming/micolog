import os,logging
import re
from functools import wraps
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.api import memcache
import app.webapp as webapp2
from  model import *
import wsgiref.handlers
from mimetypes import types_map
from datetime import datetime, timedelta
import urllib
logging.info('module base reloaded')

def urldecode(value):
    return  urllib.unquote(urllib.unquote(value)).decode('utf8')

def urlencode(value):
    return urllib.quote(value.encode('utf8'))

def sid():
    now=datetime.datetime.now()
    return now.strftime('%y%m%d%H%M%S')+str(now.microsecond)


def requires_admin(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.is_login:
            self.redirect(users.create_login_url(self.request.uri))
            return
        elif not self.is_admin:
            return self.error(403)
        else:
            return method(self, *args, **kwargs)
    return wrapper

def printinfo(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        print self #.__name__
        print dir(self)
        for x in self.__dict__:
            print x
        return method(self, *args, **kwargs)
    return wrapper

def format_date(dt):
	return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')

def cache(key="",time=3600):
    def _decorate(method):
        def _wrapper(*args, **kwargs):
            if not g_blog.enable_memcache:
                method(*args, **kwargs)
                return

            request=args[0].request
            response=args[0].response
            skey=key+ request.path_qs
            #logging.info('skey:'+skey)
            html= memcache.get(skey)
            #arg[0] is BaseRequestHandler object


            if html:
                 logging.info('cache:'+skey)
                 response.last_modified =html[1]
                 response.out.write(html[0])
            else:
                if 'last-modified' not in response.headers:
                    response.last_modified = format_date(datetime.utcnow())

                method(*args, **kwargs)
                result=response.out.getvalue()
                memcache.set(skey,(result,response.last_modified),time)

        return _wrapper
    return _decorate



class Pager(object):

    def __init__(self, model=None,query=None, items_per_page=10):
        if model:
            self.query = model.all()
        elif query:
            self.query=query

        self.items_per_page = items_per_page

    def fetch(self, p):
        max_offset = self.query.count()
        n = max_offset / self.items_per_page
        if max_offset % self.items_per_page != 0:
            n += 1

        if p < 0 or p > n:
            p = 1
        offset = (p - 1) * self.items_per_page
        results = self.query.fetch(self.items_per_page, offset)



        links = {'count':max_offset,'page_index':p,'prev': p - 1, 'next': p + 1, 'last': n}
        if links['next'] > n:
            links['next'] = 0

        return (results, links)


class BaseRequestHandler(webapp2.RequestHandler):
    def __init__(self):
        self.current='home'
        pass

    def initialize(self, request, response):
		webapp2.RequestHandler.initialize(self, request, response)
		self.blog = g_blog
		self.login_user = users.get_current_user()
		self.is_login = (self.login_user != None)
		if self.is_login:
		    self.loginurl=users.create_logout_url(self.request.uri)
		    #self.user = User.all().filter('user = ', self.login_user).get() or User(user = self.login_user)
		else:
		    self.loginurl=users.create_login_url(self.request.uri)
		    #self.user = None

		self.is_admin = users.is_current_user_admin()
		if self.is_admin:
			self.auth = 'admin'
		elif self.is_login:
			self.auth = 'login'
		else:
			self.auth = 'guest'

		try:
			self.referer = self.request.headers['referer']
		except:
			self.referer = None



		self.template_vals = {'self':self,'blog':self.blog,'current':self.current}

    def __before__(self,*args):
        pass

    def __after__(self,*args):
        pass

    def error(self,errorcode,message='an error occured'):
        if errorcode == 404:
            message = 'Sorry, we were not able to find the requested page.  We have logged this error and will look into it.'
        elif errorcode == 403:
            message = 'Sorry, that page is reserved for administrators.  '
        elif errorcode == 500:
            message = "Sorry, the server encountered an error.  We have logged this error and will look into it."

        self.template_vals.update( {'errorcode':errorcode,'message':message})
        if errorcode>0:
            self.response.set_status(errorcode)


        errorfile=getattr(self.blog.theme,'error'+str(errorcode))
        if not errorfile:
            errorfile=self.blog.theme.error
        self.response.out.write( template.render(errorfile, self.template_vals))


    def render(self,template_file,values):
        """
        Helper method to render the appropriate template
        """

        sfile=getattr(self.blog.theme, template_file)
        logging.debug('template:'+sfile)
        self.template_vals.update(values)
        html = template.render(sfile, self.template_vals)

    	self.response.out.write(html)


    def render2(self,template_file,template_vals={}):
        """
        Helper method to render the appropriate template
        """

        self.template_vals.update(template_vals)
        path = os.path.join(self.blog.rootdir, template_file)
        self.response.out.write(template.render(path, self.template_vals))


    def param(self, name, **kw):
		return self.request.get(name, **kw)

    def write(self, s):
		self.response.out.write(s)



    def chk_login(self, redirect_url='/'):
		if self.is_login:
			return True
		else:
			self.redirect(redirect_url)
			return False

    def chk_admin(self, redirect_url='/'):
		if self.is_admin:
			return True
		else:
			self.redirect(redirect_url)
			return False

class BasePublicPage(BaseRequestHandler):
    def initialize(self, request, response):
        BaseRequestHandler.initialize(self,request, response)
        m_pages=Entry.all().filter('entrytype =','page')\
            .filter('published =',True)\
            .filter('entry_parent =',0)\
            .order('menu_order')
        blogroll=Link.all().filter('linktype =','blogroll')
        self.template_vals.update({
                        'menu_pages':m_pages,
                        'categories':Category.all(),
                        'blogroll':blogroll,
                        'recent_comments':Comment.all().order('-date').fetch(5)
        })
