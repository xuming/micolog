# -*- coding: utf-8 -*-
import wsgiref.handlers
import xmlrpclib
import sys
import cgi
import base64
from datetime import datetime
from SimpleXMLRPCServer import SimpleXMLRPCDispatcher
from functools import wraps

sys.path.append('modules')
from base import *
from model import *

def checkauth(pos=1):
    def _decorate(method):
        def _wrapper(*args, **kwargs):

            username = args[pos+0]
            password = args[pos+1]
            args = args[0:pos]+args[pos+2:]
            if not (username and password and g_blog.rpcuser and g_blog.rpcpassword
                    and (g_blog.rpcuser==username)
                    and (g_blog.rpcpassword==password)):
                 raise ValueError("Authentication Failure")
            return method(*args, **kwargs)

        return _wrapper
    return _decorate

def format_date(d):
    if not d: return None
    return xmlrpclib.DateTime(d.isoformat())

def entry_struct(entry):
    categories=[]
    if entry.categorie_keys:
        categories =[cate.name for cate in  entry.categories]


    struct = {
        'postid': entry.key().id(),
        'title': entry.title,
        'link': entry.fullurl(),
        'permaLink': entry.fullurl(),
        'description': unicode(entry.content),
        'categories': categories,
        'userid': 1,
        'mt_keywords':','.join(entry.tags),
        'wp_slug':entry.slug,
        'wp_page_order':entry.menu_order,
        # 'mt_excerpt': '',
        # 'mt_text_more': '',
        # 'mt_allow_comments': 1,
        # 'mt_allow_pings': 1}
        }
    if entry.date:
        struct['dateCreated'] = format_date(entry.date)
    return struct

class Logger(db.Model):
	request = db.TextProperty()
	response = db.TextProperty()
	date = db.DateTimeProperty(auto_now_add=True)


#-------------------------------------------------------------------------------
# blogger
#-------------------------------------------------------------------------------

@checkauth()
def blogger_getUsersBlogs(discard):
	return [{'url' : g_blog.baseurl, 'blogid' : '001', 'blogName' : g_blog.title}]

#-------------------------------------------------------------------------------
# metaWeblog
#-------------------------------------------------------------------------------

@checkauth()
def metaWeblog_newPost(blogid, struct, publish):
    if struct.has_key('categories'):
    	cates = struct['categories']
    else:
    	cates = []

    newcates=[]
    for cate in cates:
      c=Category.all().filter('name =',cate)
      if c:
          newcates.append(c[0].key())
    entry=Entry(title = struct['title'],
            content = struct['description'],
            categorie_keys=newcates
     )

    if struct.has_key('mt_text_more'):
        content=struct['mt_text_more']
        if content:
            entry.content=entry.content+"<!--more-->"+struct['mt_text_more']
    if struct.has_key('mt_keywords'):
        entry.settags(struct['mt_keywords'])

    if struct.has_key('wp_slug'):
        entry.slug=struct['wp_slug']

    if struct.has_key('mt_excerpt'):
        entry.excerpt=struct['mt_excerpt']

    if publish:
        entry.publish(True)
    else:
        entry.save()
    postid =entry.key().id()
    return str(postid)
@checkauth()
def metaWeblog_newMediaObject(postid,struct):
    name=struct['name']
    mtype=struct['type']
    #logging.info( struct['bits'])
    bits=db.Blob(str(struct['bits']))
    media=Media(name=name,mtype=mtype,bits=bits)
    media.put()

    return {'url':g_blog.baseurl+'/media/'+str(media.key())}

@checkauth()
def metaWeblog_editPost(postid, struct, publish):
    if struct.has_key('categories'):
    	cates = struct['categories']
    else:
    	cates = []
    newcates=[]
    for cate in cates:
      c=Category.all().filter('name =',cate).fetch(1)
      if c:
          newcates.append(c[0].key())
    entry=Entry.get_by_id(int(postid))


    if struct.has_key('mt_keywords'):
       entry.settags(struct['mt_keywords'])

    if struct.has_key('wp_slug'):
        entry.slug=struct['wp_slug']
    if struct.has_key('mt_excerpt'):
        entry.excerpt=struct['mt_excerpt']


    entry.title = struct['title']
    entry.content = struct['description']
    if struct.has_key('mt_text_more'):
        content=struct['mt_text_more']
        if content:
            entry.content=entry.content+"<!--more-->"+struct['mt_text_more']
    entry.categorie_keys=newcates
    if publish:
        entry.publish(True)
    else:
        entry.save()

	return True


@checkauth()
def metaWeblog_getCategories(blogid):
	categories =Category.all()
	cates=[]
	for cate in categories:
		cates.append({  'categoryId' : cate.key().id_or_name(),
                        'parentId':0,
                        'description':cate.name,
                        'categoryName':cate.name,
                        'htmlUrl':'',
                        'rssUrl':''
                        })
	return cates

@checkauth()
def metaWeblog_getPost(postid):
	entry = Entry.get_by_id(int(postid))
	return entry_struct(entry)

@checkauth()
def metaWeblog_getRecentPosts(blogid, num):
	entries = Entry.all().filter('entrytype =','post').order('-date').fetch(min(num, 20))
	return [entry_struct(entry) for entry in entries]

@checkauth(pos=2)
def blogger_deletePost(appkey, postid, publish):
    post=Entry.get_by_id(int(postid))
    post.delete()
    return True

#-------------------------------------------------------------------------------
#  WordPress API
#-------------------------------------------------------------------------------
@checkauth()
def wp_newCategory(blogid,struct):
    name=struct['name']

    category=Category.all().filter('name =',name).fetch(1)
    if category and len(category):
        return category[0].slug
    else:
        category=Category(key_name=urlencode(name), name=name,slug=urlencode(name))
        category.put()
        return category.slug


@checkauth()
def wp_newPage(blogid,struct,publish):

        entry=Entry(title = struct['title'],
                content = struct['description'],
                )
        if struct.has_key('mt_text_more'):
            entry.content=entry.content+"<!--more-->"+struct['mt_text_more']

        if struct.has_key('wp_slug'):
            entry.slug=struct['wp_slug']
        if struct.has_key('wp_page_order'):
            entry.menu_order=int(struct['wp_page_order'])
        entry.entrytype='page'
        if publish:
            entry.publish(True)
        else:
            entry.save()

        postid =entry.key().id()
        return str(postid)


@checkauth(2)
def wp_getPage(blogid,pageid):
    entry = Entry.get_by_id(int(pageid))
    return entry_struct(entry)

@checkauth()
def wp_getPages(blogid,num):
	entries = Entry.all().filter('entrytype =','page').order('-date').fetch(min(num, 20))
	return [entry_struct(entry) for entry in entries]

@checkauth(2)
def wp_editPage(blogid,pageid,struct,publish):

    entry=Entry.get_by_id(int(pageid))

    ##        if struct.has_key('mt_keywords'):
    ##            entry.tags=struct['mt_keywords'].split(',')

    if struct.has_key('wp_slug'):
        entry.slug=struct['wp_slug']

    if struct.has_key('wp_page_order'):
        entry.menu_order=int(struct['wp_page_order'])


    entry.title = struct['title']
    entry.content = struct['description']
    if struct.has_key('mt_text_more'):
        entry.content=entry.content+"<!--more-->"+struct['mt_text_more']
    if publish:
        entry.publish(True)
    else:
        entry.save()

    return True


@checkauth()
def wp_deletePage(blogid,pageid):
    post=Entry.get_by_id(int(pageid))
    post.delete()
    return True

@checkauth()
def wp_getAuthors(blogid):
    return [{'user_id':1,'user_login':'','display_name':'admin'}]

@checkauth()
def wp_getPageList(blogid):
    return []

@checkauth()
def mt_getPostCategories(blogid):
      post=Entry.get_by_id(int(blogid))
      categories=post.categorie_keys
      cates=[]
      for cate in categories:
            cates.append({  'categoryId' : cate.id_or_name(),
                        'parentId':0,
                        'description':cate.name(),
                        'categoryName':cate.name(),
                        'htmlUrl':'',
                        'rssUrl':''
                        })
      return cates

def mt_setPostCategories(*arg):
    return True
#-------------------------------------------------------------------------------

class PlogXMLRPCDispatcher(SimpleXMLRPCDispatcher):
	def __init__(self, funcs):
		SimpleXMLRPCDispatcher.__init__(self, True, 'utf-8')
		self.funcs = funcs

dispatcher = PlogXMLRPCDispatcher({
	'blogger.getUsersBlogs' : blogger_getUsersBlogs,
	'blogger.deletePost' : blogger_deletePost,

	'metaWeblog.newPost' : metaWeblog_newPost,
	'metaWeblog.editPost' : metaWeblog_editPost,
	'metaWeblog.getCategories' : metaWeblog_getCategories,
	'metaWeblog.getPost' : metaWeblog_getPost,
	'metaWeblog.getRecentPosts' : metaWeblog_getRecentPosts,
	'metaWeblog.newMediaObject':metaWeblog_newMediaObject,

	'wp.getCategories':metaWeblog_getCategories,
	'wp.newCategory':wp_newCategory,
	'wp.newPage':wp_newPage,
	'wp.getPage':wp_getPage,
	'wp.getPages':wp_getPages,
	'wp.editPage':wp_editPage,
	'wp.getPageList':wp_getPageList,
	'wp.deletePage':wp_deletePage,
    'wp.getAuthors':wp_getAuthors,

    'mt.setPostCategories':mt_setPostCategories,
    'mt.getPostCategories':mt_getPostCategories,



	})


# {{{ Handlers
class CallApi(BaseRequestHandler):
	def get(self):
		Logger(request = self.request.uri, response = '----------------------------------').put()
		self.write('<h1>please use POST</h1>')

	def post(self):
		#self.response.headers['Content-Type'] = 'application/xml; charset=utf-8'
		request = self.request.body
		response = dispatcher._marshaled_dispatch(request)
		Logger(request = unicode(request, 'utf-8'), response = unicode(response, 'utf-8')).put()
		self.write(response)

class View(BaseRequestHandler):
    @requires_admin
    def get(self):
    	self.write('<html><body><h1>Logger</h1>')
    	for log in Logger.all().order('-date').fetch(5,0):
    		self.write("<p>date: %s</p>" % log.date)
    		self.write("<h1>Request</h1>")
    		self.write('<pre>%s</pre>' % cgi.escape(log.request))
    		self.write("<h1>Reponse</h1>")
    		self.write('<pre>%s</pre>' % cgi.escape(log.response))
    		self.write("<hr />")
    	self.write('</body></html>')

class DeleteLog(BaseRequestHandler):
	def get(self):
		if self.chk_admin():
			for log in Logger.all():
				log.delete()


			self.redirect('/rpc/view')
#}}}


def main():
	#webapp.template.register_template_library("filter")
	application = webapp.WSGIApplication(
			[
				('/rpc', CallApi),
				('/rpc/view', View),
				('/rpc/dellog', DeleteLog),

				],
			debug=True)
	wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
	main()

