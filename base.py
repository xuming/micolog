# -*- coding: utf-8 -*-
import os,logging
import re
from functools import wraps
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.api import memcache
from google.appengine.api import urlfetch
##import app.webapp as webapp2
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.utils.translation import  activate
from django.template import TemplateDoesNotExist
from django.conf import settings
settings._target = None
#from model import g_blog,User
#activate(g_blog.language)
from google.appengine.api.labs import taskqueue
import wsgiref.handlers
from mimetypes import types_map
from datetime import datetime, timedelta
import urllib
import traceback
import micolog_template


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
		elif not (self.is_admin
			or self.author):
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
#only ajax methed allowed
def ajaxonly(method):
	@wraps(method)
	def wrapper(self, *args, **kwargs):
		if not self.request.headers["X-Requested-With"]=="XMLHttpRequest":
			 self.error(404)
		else:
			return method(self, *args, **kwargs)
	return wrapper

#only request from same host can passed
def hostonly(method):
	@wraps(method)
	def wrapper(self, *args, **kwargs):
		if  self.request.headers['Referer'].startswith(os.environ['HTTP_HOST'],7):
			return method(self, *args, **kwargs)
		else:
			self.error(404)
	return wrapper

def format_date(dt):
	return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')

def cache(key="",time=3600):
	def _decorate(method):
		def _wrapper(*args, **kwargs):
			from model import g_blog
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
				 ilen=len(html)
				 if ilen>=3:
					response.set_status(html[2])
				 if ilen>=4:
					for skey,value in html[3].items():
						response.headers[skey]=value
				 response.out.write(html[0])
			else:
				if 'last-modified' not in response.headers:
					response.last_modified = format_date(datetime.utcnow())

				method(*args, **kwargs)
				result=response.out.getvalue()
				status_code = response._Response__status[0]
				logging.debug("Cache:%s"%status_code)
				memcache.set(skey,(result,response.last_modified,status_code,response.headers),time)

		return _wrapper
	return _decorate

#-------------------------------------------------------------------------------
class PingbackError(Exception):
	"""Raised if the remote server caused an exception while pingbacking.
	This is not raised if the pingback function is unable to locate a
	remote server.
	"""

	_ = lambda x: x
	default_messages = {
		16: _(u'source URL does not exist'),
		17: _(u'The source URL does not contain a link to the target URL'),
		32: _(u'The specified target URL does not exist'),
		33: _(u'The specified target URL cannot be used as a target'),
		48: _(u'The pingback has already been registered'),
		49: _(u'Access Denied')
	}
	del _

	def __init__(self, fault_code, internal_message=None):
		Exception.__init__(self)
		self.fault_code = fault_code
		self._internal_message = internal_message

	def as_fault(self):
		"""Return the pingback errors XMLRPC fault."""
		return Fault(self.fault_code, self.internal_message or
					 'unknown server error')

	@property
	def ignore_silently(self):
		"""If the error can be ignored silently."""
		return self.fault_code in (17, 33, 48, 49)

	@property
	def means_missing(self):
		"""If the error means that the resource is missing or not
		accepting pingbacks.
		"""
		return self.fault_code in (32, 33)

	@property
	def internal_message(self):
		if self._internal_message is not None:
			return self._internal_message
		return self.default_messages.get(self.fault_code) or 'server error'

	@property
	def message(self):
		msg = self.default_messages.get(self.fault_code)
		if msg is not None:
			return _(msg)
		return _(u'An unknown server error (%s) occurred') % self.fault_code

class util:
	@classmethod
	def do_trackback(cls, tbUrl=None, title=None, excerpt=None, url=None, blog_name=None):
		taskqueue.add(url='/admin/do/trackback_ping',
			params={'tbUrl': tbUrl,'title':title,'excerpt':excerpt,'url':url,'blog_name':blog_name})

	#pingback ping
	@classmethod
	def do_pingback(cls,source_uri, target_uri):
		taskqueue.add(url='/admin/do/pingback_ping',
			params={'source': source_uri,'target':target_uri})



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
		if max_offset % self.items_per_page != 0:
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


class BaseRequestHandler(webapp.RequestHandler):
	def __init__(self):
		self.current='home'

	def initialize(self, request, response):
		webapp.RequestHandler.initialize(self, request, response)
		os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
		from model import g_blog,User
		self.blog = g_blog
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
		path = os.path.join(self.blog.rootdir, template_file)
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


