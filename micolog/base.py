# -*- coding: utf-8 -*-
import os,logging
import functools,webapp2
from google.appengine.api import users
from google.appengine.ext.webapp import template
from google.appengine.api import memcache
##import app.webapp as webapp2
from django.template import TemplateDoesNotExist
#from django.conf import settings
#settings._target = None
#from model import g_blog,User
#activate(g_blog.language)
from google.appengine.api import taskqueue
from mimetypes import types_map
from datetime import datetime
import urllib
import traceback
import template

def requires_admin(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.is_login:
            self.redirect(users.create_login_url(self.request.uri))
            return
        elif not (self.is_admin
            or self.author):
            return self.error(403)
        else:
            return method(self, *args, **kwargs)
    return wrapper

def printinfo(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        print self #.__name__
        print dir(self)
        for x in self.__dict__:
            print x
        return method(self, *args, **kwargs)
    return wrapper

#only ajax methed allowed
def ajaxonly(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.request.headers["X-Requested-With"]=="XMLHttpRequest":
             self.error(404)
        else:
            return method(self, *args, **kwargs)
    return wrapper

#only request from same host can passed
def hostonly(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if  self.request.headers['Referer'].startswith(os.environ['HTTP_HOST'],7):
            return method(self, *args, **kwargs)
        else:
            self.error(404)
    return wrapper


##cache variable

class Pager(object):

    def __init__(self, model=None,query=None, items_per_page=10):
        if model:
            self.query = model.all()
        else:
            self.query=query

        self.items_per_page = items_per_page

    def fetch(self, p):
        if hasattr(self.query,'__len__'):
            max_offset=len(self.query)
        else:
            max_offset = self.query.count()
        n = max_offset / self.items_per_page
        if max_offset % self.items_per_page:
            n += 1

        if p < 0 or p > n:
            p = 1
        offset = (p - 1) * self.items_per_page
        if hasattr(self.query,'fetch'):
            results = self.query.fetch(self.items_per_page, offset)
        else:
            results = self.query[offset:offset+self.items_per_page]



        links = {'count':max_offset,'page_index':p,'prev': p - 1, 'next': p + 1, 'last': n}
        if links['next'] > n:
            links['next'] = 0

        return (results, links)



class LangIterator:
    def __init__(self, path='locale'):
        self.iterating = False
        self.path = path
        self.list = []
        for value in  os.listdir(self.path):
            if os.path.isdir(os.path.join(self.path, value)):
                if os.path.exists(os.path.join(self.path, value, 'LC_MESSAGES')):
                    try:
                        lang = open(os.path.join(self.path, value, 'language')).readline()
                        self.list.append({'code':value, 'lang':lang})
                    except:
                        self.list.append( {'code':value, 'lang':value})

    def __iter__(self):
        return self

    def next(self):
        if not self.iterating:
            self.iterating = True
            self.cursor = 0

        if self.cursor >= len(self.list):
            self.iterating = False
            raise StopIteration
        else:
            value = self.list[self.cursor]
            self.cursor += 1
            return value

    def getlang(self, language):
        from django.utils.translation import  to_locale
        for item in self.list:
            if item['code'] == language or item['code'] == to_locale(language):
                return item
        return {'code':'en_US', 'lang':'English'}


def Sitemap_NotifySearch():
    """ Send notification of the new Sitemap(s) to the search engines. """


    url = g_blog.baseurl+"/sitemap"

    # Cycle through notifications
    # To understand this, see the comment near the NOTIFICATION_SITES comment
    for ping in settings.NOTIFICATION_SITES:
        query_map = ping[3]
        query_attr = ping[5]
        query_map[query_attr] = url
        query = urllib.urlencode(query_map)
        notify = urlparse.urlunsplit((ping[0], ping[1], ping[2], query, ping[4]))
        # Send the notification
        logging.info('Notifying search engines. %s'%ping[1])
        logging.info('url: %s'%notify)
        try:
            result = urlfetch.fetch(notify)
            if result.status_code == 200:
                logging.info('Notify Result: %s' % result.content)
            if result.status_code == 404:
                logging.info('HTTP error 404: Not Found')
                logging.warning('Cannot contact: %s' % ping[1])

        except :
            logging.error('Cannot contact: %s' % ping[1])


class BaseRequestHandler(webapp2.RequestHandler):



##	def head(self, *args):
##		return self.get(*args)

    def initialize(self, request, response):
        self.current='home'
        webapp2.RequestHandler.initialize(self, request, response)
        os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
        from model import User,Blog
        self.blog = Blog.getBlog()
        self.login_user = users.get_current_user()
        self.is_login = (self.login_user != None)
        self.loginurl=users.create_login_url(self.request.uri)
        self.logouturl=users.create_logout_url(self.request.uri)
        self.is_admin = users.is_current_user_admin()

        if self.is_admin:
            self.auth = 'admin'
            self.author=User.all().filter('email =',self.login_user.email()).get()
            if not self.author:
                self.author=User(dispname=self.login_user.nickname(),email=self.login_user.email())
                self.author.isadmin=True
                self.author.user=self.login_user
                self.author.put()
        elif self.is_login:
            self.author=User.all().filter('email =',self.login_user.email()).get()
            if self.author:
                self.auth='author'
            else:
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

        message+="<p><pre>"+traceback.format_exc()+"</pre><br></p>"
        self.template_vals.update( {'errorcode':errorcode,'message':message})

        if errorcode>0:
            self.response.set_status(errorcode)


        #errorfile=getattr(self.blog.theme,'error'+str(errorcode))
        #logging.debug(errorfile)
##		if not errorfile:
##			errorfile=self.blog.theme.error
        errorfile='error'+str(errorcode)+".html"
        try:
            content=micolog_template.render(self.blog.theme,errorfile, self.template_vals)
        except TemplateDoesNotExist:
            try:
                content=micolog_template.render(self.blog.theme,"error.html", self.template_vals)
            except TemplateDoesNotExist:
                content=micolog_template.render(self.blog.default_theme,"error.html", self.template_vals)
        except:
            content=message
        self.response.out.write(content)

    def get_render(self,template_file,values):
        template_file=template_file+".html"
        self.template_vals.update(values)

        try:
            #sfile=getattr(self.blog.theme, template_file)
            logging.debug("get_render:"+template_file)
            html = micolog_template.render(self.blog.theme, template_file, self.template_vals)
        except TemplateDoesNotExist:
            #sfile=getattr(self.blog.default_theme, template_file)
            html = micolog_template.render(self.blog.default_theme, template_file, self.template_vals)

        return html

    def render(self,template_file,values):
        """
        Helper method to render the appropriate template
        """
        html=self.get_render(template_file,values)
        self.response.out.write(html)

    def message(self,msg,returl=None,title='Infomation'):
        self.render('msg',{'message':msg,'title':title,'returl':returl})

    def render2(self,template_file,template_vals={}):
        """
        Helper method to render the appropriate template
        """
        self.template_vals.update(template_vals)
        path = os.path.join(os.path.dirname(__file__), template_file)
        self.response.out.write(template.render(path, self.template_vals))

    def param(self, name, **kw):
        return self.request.get(name, **kw)

    def paramint(self, name, default=0):
        try:
           return int(self.request.get(name))
        except:
           return default

    def parambool(self, name, default=False):
        try:
           return self.request.get(name)=='on'
        except:
           return default

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

