import wsgiref.handlers
import xmlrpclib
import sys
import cgi
from datetime import datetime
from SimpleXMLRPCServer import SimpleXMLRPCDispatcher
from functools import wraps

sys.path.append('modules')
from app.base import *
from app.model import *

def checkauth(pos=1):
    def _decorate(method):
        def _wrapper(*args, **kwargs):
            username = args[pos+0]
            password = args[pos+1]
            args = args[0:pos]+args[pos+2:]
            if not (g_blog.rpcuser==username) and (g_blog.rpcpassword==password):
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

@checkauth()
def blogger_getUsersBlogs(discard):
	return [{'url' : g_blog.baseurl, 'blogid' : '001', 'blogName' : g_blog.title}]

@checkauth()
def metaWeblog_newPost(blogid, struct, publish):
    if publish:
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
        entry.publish(True)
        postid =entry.key().id()
        return str(postid)
    else:
        return 'notpublished'

@checkauth()
def metaWeblog_editPost(postid, struct, publish):
    if publish:

        if struct.has_key('categories'):
        	cates = struct['categories']
        else:
        	cates = []
        newcates=[]
        for cate in cates:
          c=Category.all().filter('name =',cate)
          if c:
              newcates.append(c[0].key())
        entry=Entry.get_by_id(int(postid))

        entry.title = struct['title']
        entry.content = struct['description']
        entry.categorie_keys=newcates
        entry.publish(True)

    	return True
    else:
    	return True
@checkauth()
def metaWeblog_getCategories(blogid):
	categories =Category.all()
	cates=[]
	for cate in categories:
		cates.append({  'categoryId' : cate.key().id(),
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
	entrys = Entry.all().filter('entrytype =','post').order('-date').fetch(min(num, 20))
	return [entry_struct(entry) for entry in entrys]

@checkauth(pos=2)
def blogger_deletePost(appkey, postid, publish):
    post=Entry.get_by_id(postid)
    post.delete()
    return True

class PlogXMLRPCDispatcher(SimpleXMLRPCDispatcher):
	def __init__(self, funcs):
		SimpleXMLRPCDispatcher.__init__(self, True, 'utf-8')
		self.funcs = funcs

dispatcher = PlogXMLRPCDispatcher({
	'blogger.getUsersBlogs' : blogger_getUsersBlogs,
	#'blogger.deletePost' : blogger_deletePost,
	'metaWeblog.newPost' : metaWeblog_newPost,
	'metaWeblog.editPost' : metaWeblog_editPost,
	'metaWeblog.getCategories' : metaWeblog_getCategories,
	'metaWeblog.getPost' : metaWeblog_getPost,
	'metaWeblog.getRecentPosts' : metaWeblog_getRecentPosts,
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
    	for log in Logger.all().order('-date'):
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


			self.redirect('/')
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

