# -*- coding: utf-8 -*-
import wsgiref.handlers
import xmlrpclib
from xmlrpclib import Fault
import sys
import cgi
import base64
#from datetime import datetime
import app.mktimefix as datetime
from SimpleXMLRPCServer import SimpleXMLRPCDispatcher
from functools import wraps
from django.utils.html import strip_tags
sys.path.append('modules')
from base import *
from model import *
from micolog_plugin import *
from urlparse import urlparse

def checkauth(pos=1):
	def _decorate(method):
		def _wrapper(*args, **kwargs):

			username = args[pos+0]
			password = args[pos+1]

			if not (username and password and g_blog.rpcuser and g_blog.rpcpassword
					and (g_blog.rpcuser==username)
					and (g_blog.rpcpassword==password)):
				 raise ValueError("Authentication Failure")
			args = args[0:pos]+args[pos+2:]
			return method(*args, **kwargs)

		return _wrapper
	return _decorate

def format_date(d):
	if not d: return None
	#return xmlrpclib.DateTime(d.isoformat())
	return xmlrpclib.DateTime(d)

def post_struct(entry):
	if not entry:
		 raise Fault(404, "Post does not exist")
	categories=[]
	if entry.categorie_keys:
		categories =[cate.name for cate in  entry.categories]


	struct = {
		'postid': entry.key().id(),
		'title': entry.title,
		'link': entry.fullurl,
		'permaLink': entry.fullurl,
		'description': unicode(entry.content),
		'categories': categories,
		'userid': '1',
		'mt_keywords':','.join(entry.tags),
		'mt_excerpt': '',
		'mt_text_more': '',
		'mt_allow_comments': entry.allow_comment and 1 or 0,
		'mt_allow_pings': entry.allow_trackback and 1 or 0,
		'custom_fields':[],
		'post_status':entry.post_status,
		'sticky':entry.sticky,
		'wp_author_display_name': entry.get_author_user().dispname,
 		'wp_author_id': str(entry.get_author_user().key().id()),
 		'wp_password': entry.password,
 		'wp_slug':entry.slug
		}
	if entry.date:
		t=timedelta(seconds=3600*g_blog.timedelta)
		struct['dateCreated'] = format_date(entry.date+t)
		struct['date_created_gmt'] = format_date(entry.date)

	return struct

def page_struct(entry):
	if not entry:
		 raise Fault(404, "Post does not exist")
	categories=[]
	if entry.categorie_keys:
		categories =[cate.name for cate in  entry.categories]


	struct = {
		'page_id': entry.key().id(),
		'title': entry.title,
		'link': entry.fullurl,
		'permaLink': entry.fullurl,
		'description': unicode(entry.content),
		'categories': categories,
		'userid': '1',
		'mt_allow_comments': entry.allow_comment and 1 or 0,
		'mt_allow_pings': entry.allow_trackback and 1 or 0,
		'custom_fields':[],
		'page_status':entry.post_status,
		'sticky':entry.sticky,
		'wp_author_display_name': entry.get_author_user().dispname,
 		'wp_author_id': str(entry.get_author_user().key().id()),
 		'wp_password': entry.password,
 		'wp_slug':entry.slug,
 		'text_more': '',
 		'wp_author': 'admin',
		'wp_page_order': entry.menu_order,
 		'wp_page_parent_id': 0,
 		'wp_page_parent_title': '',
 		'wp_page_template': 'default',
		}
	if entry.date:
		struct['dateCreated'] = format_date(entry.date)
		struct['date_created_gmt'] = format_date(entry.date)

	return struct

def entry_title_struct(entry):
	if not entry:
		 raise Fault(404, "Post does not exist")
	struct = {
		'postid': str(entry.key().id()),
		'title': entry.title,
		'userid': '1',
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
	return [{'url' : g_blog.baseurl, 'blogid' : '1','isAdmin':True, 'blogName' : g_blog.title,'xmlrpc':g_blog.baseurl+"/rpc"}]

@checkauth(pos=2)
def blogger_deletePost(appkey, postid, publish=False):
	post=Entry.get_by_id(int(postid))
	post.delete()
	return True

@checkauth()
def blogger_getUserInfo(appkey):
	for user in User.all():
		if user.isadmin:
			return {'email':user.email,'firstname':'','nickname':user.dispname,'userid':str(user.key().id()),
		   'url':'','lastname':''}
	return None

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

	try:
		if struct.has_key('date_created_gmt'): #如果有日期属性
			entry.date=datetime.strptime(str(struct['date_created_gmt']), "%Y%m%dT%H:%M:%S")
		elif struct.has_key('dateCreated'): #如果有日期属性
			entry.date=datetime.strptime(str(struct['dateCreated']), "%Y%m%dT%H:%M:%S")-timedelta(seconds=3600*g_blog.timedelta)
	except:
		pass

	if struct.has_key('wp_password'):
		entry.password=struct['wp_password']

	if struct.has_key('sticky'):
		entry.sticky=struct['sticky']


	if struct.has_key('wp_author_id'):
		author=User.get_by_id(int(struct['wp_author_id']))
		entry.author=author.user
		entry.author_name=author.dispname
	else:
		entry.author=g_blog.owner
		entry.author_name=g_blog.author

	if publish:
		entry.save(True)

		if struct.has_key('mt_tb_ping_urls'):
			for url in struct['mt_tb_ping_urls']:
				util.do_trackback(url,entry.title,entry.get_content_excerpt(more='')[:60],entry.fullurl,g_blog.title)
		g_blog.tigger_action("xmlrpc_publish_post",entry)
	else:
		entry.save()
	postid =entry.key().id()
	return str(postid)

@checkauth()
def metaWeblog_newMediaObject(blogid,struct):
	name=struct['name']

	if struct.has_key('type'):
		mtype=struct['type']
	else:
		st=name.split('.')
		if len(st)>1:
			mtype=st[-1]
		else:
			mtype=None
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

	try:
		if struct.has_key('date_created_gmt'): #如果有日期属性
			entry.date=datetime.strptime(str(struct['date_created_gmt']), "%Y%m%dT%H:%M:%S")
		elif struct.has_key('dateCreated'): #如果有日期属性
			entry.date=datetime.strptime(str(struct['dateCreated']), "%Y%m%dT%H:%M:%S")-timedelta(seconds=3600*g_blog.timedelta)
	except:
		pass

	if struct.has_key('wp_password'):
		entry.password=struct['wp_password']

	if struct.has_key('sticky'):
		entry.sticky=struct['sticky']

	if struct.has_key('wp_author_id'):
		author=User.get_by_id(int(struct['wp_author_id']))
		entry.author=author.user
		entry.author_name=author.dispname
	else:
		entry.author=g_blog.owner
		entry.author_name=g_blog.author

	entry.title = struct['title']
	entry.content = struct['description']
	if struct.has_key('mt_text_more'):
		content=struct['mt_text_more']
		if content:
			entry.content=entry.content+"<!--more-->"+struct['mt_text_more']
	entry.categorie_keys=newcates
	if publish:
		entry.save(True)
	else:
		entry.save()

	return True


@checkauth()
def metaWeblog_getCategories(blogid):
	categories =Category.all()
	cates=[]
	for cate in categories:
		cates.append({  'categoryDescription':'',
						'categoryId' : str(cate.ID()),
						'parentId':'0',
						'description':cate.name,
						'categoryName':cate.name,
						'htmlUrl':'',
						'rssUrl':''
						})
	return cates

@checkauth()
def metaWeblog_getPost(postid):
	entry = Entry.get_by_id(int(postid))
	return post_struct(entry)

@checkauth()
def metaWeblog_getRecentPosts(blogid, num):
	entries = Entry.all().filter('entrytype =','post').order('-date').fetch(min(num, 20))
	return [post_struct(entry) for entry in entries]



#-------------------------------------------------------------------------------
#  WordPress API
#-------------------------------------------------------------------------------
@checkauth(pos=0)
def wp_getUsersBlogs():
	#return [{'url' : g_blog.baseurl, 'blog_id' : 1,'is_admin':True, 'blog_name' : g_blog.title,'xmlrpc_url':g_blog.baseurl+"/xmlrpc.php"}]
    return [{'url' : g_blog.baseurl, 'blogid' : '1','isAdmin':True, 'blogName' : g_blog.title,'xmlrpc':g_blog.baseurl+"/rpc"}]

@checkauth()
def wp_getTags(blog_id):
	def func(blog_id):
		for tag in Tag.all():
			yield {'tag_ID':'0','name':tag.tag,'count':str(tag.tagcount),'slug':tag.tag,'html_url':'','rss_url':''}
	return list(func(blog_id))

@checkauth()
def wp_getCommentCount(blog_id,postid):
	entry = Entry.get_by_id(postid)
	if entry:
		return {'approved':entry.commentcount,'awaiting_moderation':0,'spam':0,'total_comments':entry.commentcount}

@checkauth()
def wp_getPostStatusList(blogid):
	return {'draft': 'Draft',
 			'pending': 'Pending Review',
 			'private': 'Private',
 			'publish': 'Published'}

@checkauth()
def wp_getPageStatusList(blogid):
	return {'draft': 'Draft', 'private': 'Private', 'publish': 'Published'}

@checkauth()
def wp_getPageTemplates(blogid):
	return {}

@checkauth()
def wp_setOptions(blogid,options):
	for name,value in options,options.values():
		if hasattr(g_blog,name):
			setattr(g_blog,name,value)
	return options

@checkauth()
def wp_getOptions(blogid,options):
	#todo:Options is None ,return all attrbutes
	mdict={}
	if options:
		for option in options:
			if hasattr(g_blog,option):
				mdict[option]={'desc':option,
								'readonly:':False,
								'value':getattr(g_blog,option)}
	return mdict

@checkauth()
def wp_newCategory(blogid,struct):
	name=struct['name']

	category=Category.all().filter('name =',name).fetch(1)
	if category and len(category):
		return category[0].ID()
	else:
		#category=Category(key_name=urlencode(name), name=name,slug=urlencode(name))
		category=Category(name=name,slug=name)
		category.put()
		return category.ID()


@checkauth()
def wp_newPage(blogid,struct,publish):

		entry=Entry(title = struct['title'],
				content = struct['description'],
				)
		if struct.has_key('mt_text_more'):
			entry.content=entry.content+"<!--more-->"+struct['mt_text_more']

		try:
			if struct.has_key('date_created_gmt'): #如果有日期属性
				entry.date=datetime.strptime(str(struct['date_created_gmt']), "%Y%m%dT%H:%M:%S")
			elif struct.has_key('dateCreated'): #如果有日期属性
				entry.date=datetime.strptime(str(struct['dateCreated']), "%Y%m%dT%H:%M:%S")-timedelta(seconds=3600*g_blog.timedelta)
		except:
			pass

		if struct.has_key('wp_slug'):
			entry.slug=struct['wp_slug']
		if struct.has_key('wp_page_order'):
			entry.menu_order=int(struct['wp_page_order'])
		if struct.has_key('wp_password'):
			entry.password=struct['wp_password']

		if struct.has_key('wp_author_id'):
			author=User.get_by_id(int(struct['wp_author_id']))
			entry.author=author.user
			entry.author_name=author.dispname
		else:
			entry.author=g_blog.owner
			entry.author_name=g_blog.author

		entry.entrytype='page'
		if publish:
			entry.save(True)
		else:
			entry.save()

		postid =entry.key().id()
		return str(postid)


@checkauth(2)
def wp_getPage(blogid,pageid):
	entry = Entry.get_by_id(int(pageid))
	return page_struct(entry)

@checkauth()
def wp_getPages(blogid,num=20):
	entries = Entry.all().filter('entrytype =','page').order('-date').fetch(min(num, 20))
	return [page_struct(entry) for entry in entries]

@checkauth(2)
def wp_editPage(blogid,pageid,struct,publish):

	entry=Entry.get_by_id(int(pageid))

	##		if struct.has_key('mt_keywords'):
	##			entry.tags=struct['mt_keywords'].split(',')

	if struct.has_key('wp_slug'):
		entry.slug=struct['wp_slug']

	if struct.has_key('wp_page_order'):
		entry.menu_order=int(struct['wp_page_order'])
	try:
		if struct.has_key('date_created_gmt'): #如果有日期属性
			entry.date=datetime.strptime(str(struct['date_created_gmt']), "%Y%m%dT%H:%M:%S")
		elif struct.has_key('dateCreated'): #如果有日期属性
			entry.date=datetime.strptime(str(struct['dateCreated']), "%Y%m%dT%H:%M:%S")-timedelta(seconds=3600*g_blog.timedelta)
	except:
		pass

	if struct.has_key('wp_password'):
		entry.password=struct['wp_password']
	if struct.has_key('wp_author_id'):
		author=User.get_by_id(int(struct['wp_author_id']))
		entry.author=author.user
		entry.author_name=author.dispname
	else:
		entry.author=g_blog.owner
		entry.author_name=g_blog.author
	entry.title = struct['title']
	entry.content = struct['description']
	if struct.has_key('mt_text_more'):
		entry.content=entry.content+"<!--more-->"+struct['mt_text_more']
	entry.save(True)

	return True


@checkauth()
def wp_deletePage(blogid,pageid):
	post=Entry.get_by_id(int(pageid))
	post.delete()
	return True

@checkauth()
def wp_getAuthors(blogid):
	ulist=[]
	i=1
	for user in User.all():
		ulist.append({'user_id':str(user.key().id()),'user_login':'admin','display_name':user.dispname})
		i=i+1
	return ulist

@checkauth()
def wp_deleteComment(blogid,commentid):
	try:
		comment=Comment.get_by_id(int(commentid))
		if comment:
			comment.delit()
		return True

	except:
		return False
@checkauth()
def wp_editComment(blogid,commentid,struct):
	try:
		comment=Comment.get_by_id(int(commentid))
		if comment:
			url=struct['author_url']
			if url:
		   		try:
					comment.weburl=url
		   		except:
			   		comment.weburl=None
			#comment.date= format_date(datetime.now())
			comment.author=struct['author']
			#comment.weburl=struct['author_url']
			comment.email=struct['author_email']
			comment.content=struct['content']
			#comment.status=struct['status']
			comment.save()
			return True
	except:
		raise
		return False

@checkauth()
def wp_newComment(blogid,postid,struct):
	post=Entry.get_by_id(postid)
	if not post:
		raise Fault(404, "Post does not exist")
	comment=Comment(entry=post,content=struct['content'],
	                author=struct['author'],
	                email=struct['author_email'])
	url=struct['author_url']
	if url:
	   try:
			comment.weburl=url
	   except:
		   comment.weburl=None

	comment.save()
	return comment.key().id()

@checkauth()
def wp_getCommentStatusList(blogid):
	return {'hold':0,'approve':Comment.all().count(),'spam':0}

@checkauth()
def wp_getPageList(blogid,num=20):
	def func(blogid):
		entries = Entry.all().filter('entrytype =','page').order('-date').fetch(min(num, 20))
		for entry in entries:
			yield {'page_id':str(entry.key().id()),'page_title':entry.title,'page_parent_id':0,'dateCreated': format_date(entry.date),'date_created_gmt': format_date(entry.date)}
	return list(func(blogid))

@checkauth()
def wp_deleteCategory(blogid,cateid):
	try:
		cate=Category.get_from_id(int(cateid))
		cate.delete()
		return True
	except:
		return False
@checkauth()
def	wp_suggestCategories(blogid,category,max_result):
	categories=Category.all()
  	cates=[]
  	for cate in categories:
		cates.append({  'categoryId' : str(cate.ID()),
					'categoryName':cate.name
					})
  	return cates[:max_result]

@checkauth()
def wp_getComment(blogid,commentid):
	comment=Comment.get_by_id(int(commentid))
	return {
 					'dateCreated':format_date(comment.date),
			 				'date_created_gmt':format_date(comment.date),
			 				'user_id':'0',
							'comment_id':str(comment.key().id()),
							'parent':'',
							'status':'approve',
							'content':unicode(comment.content),
							'link':comment.entry.link+"#comment-"+str(comment.key().id()),
							'post_id':str(comment.entry.key().id()),
							'post_title':comment.entry.title,
							'author':comment.author,
							'author_url':str(comment.weburl),
							'author_email':str(comment.email),
							'author_ip':comment.ip,
							'type':''
			}

@checkauth()
def wp_getComments(blogid,data):
	def func(blogid,data):
		number=int(data['number'])
		try:
			offset=int(data['offset'])
		except:
			offset=0

		comments=[]

		if data['post_id']:
			postid=int(data['post_id'])
			post=Entry.get_by_id(postid)
			if post:
				comments=post.comments()
		else:
			comments=Comment.all()

		for comment in comments.fetch(number,offset):
			yield {
		 				'dateCreated':format_date(comment.date),
		 				'date_created_gmt':format_date(comment.date),
		 				'user_id':'0',
						'comment_id':str(comment.key().id()),
						'parent':'',
						'status':'approve',
						'content':unicode(comment.content),
						'link':comment.entry.link+"#comment-"+str(comment.key().id()),
						'post_id':str(comment.entry.key().id()),
						'post_title':comment.entry.title,
						'author':comment.author,
						'author_url':str(comment.weburl),
						'author_email':str(comment.email),
						'author_ip':comment.ip,
						'type':''
					}
	return list(func(blogid,data))


@checkauth()
def mt_getPostCategories(postid):
	  post=Entry.get_by_id(int(postid))
	  categories=post.categories
	  cates=[]
	  for cate in categories:
			#cate=Category(key)
			cates.append({'categoryId' : str(cate.ID()),
						'categoryName':cate.name,
						'isPrimary':True
						})
	  return cates

@checkauth()
def mt_getCategoryList(blogid):
	  categories=Category.all()
	  cates=[]
	  for cate in categories:
			cates.append({  'categoryId' : str(cate.ID()),
						'categoryName':cate.name
						})
	  return cates

@checkauth()
def mt_setPostCategories(postid,cates):
	try:
		entry=Entry.get_by_id(int(postid))
		newcates=[]

		for cate in cates:
			if cate.has_key('categoryId'):
				id=int(cate['categoryId'])
				c=Category.get_from_id(int(cate['categoryId']))
				if c:
					newcates.append(c.key())
		entry.categorie_keys=newcates
		entry.put()
		return True
	except:
		return False

@checkauth()
def mt_publishPost(postid):
	try:
		entry=Entry.get_by_id(int(postid))
		entry.save(True)
		return entry.key().id()
	except:
		return 0

@checkauth()
def mt_getRecentPostTitles(blogid,num):
	entries = Entry.all().filter('entrytype =','post').order('-date').fetch(min(num, 20))
 	return [entry_title_struct(entry) for entry in entries]

#------------------------------------------------------------------------------
#pingback
#------------------------------------------------------------------------------
_title_re = re.compile(r'<title>(.*?)</title>(?i)')
_pingback_re = re.compile(r'<link rel="pingback" href="([^"]+)" ?/?>(?i)')
_chunk_re = re.compile(r'\n\n|<(?:p|div|h\d)[^>]*>')
def pingback_ping(source_uri, target_uri):
	# next we check if the source URL does indeed exist
	if not g_blog.allow_pingback:
		raise Fault(49,"Access denied.")
	try:

		g_blog.tigger_action("pre_ping",source_uri,target_uri)
		response = urlfetch.fetch(source_uri)
	except Exception ,e :
		#logging.info(e.message)
		raise Fault(16, 'The source URL does not exist.%s'%source_uri)
	# we only accept pingbacks for links below our blog URL
	blog_url = g_blog.baseurl
	if not blog_url.endswith('/'):
		blog_url += '/'
	if not target_uri.startswith(blog_url):
		raise Fault(32, 'The specified target URL does not exist.')
	path_info = target_uri[len(blog_url):]

	pingback_post(response,source_uri,target_uri,path_info)
	try:

		return "Micolog pingback succeed!"
	except:
		raise Fault(49,"Access denied.")


def get_excerpt(response, url_hint, body_limit=1024 * 512):
	"""Get an excerpt from the given `response`.  `url_hint` is the URL
	which will be used as anchor for the excerpt.  The return value is a
	tuple in the form ``(title, body)``.  If one of the two items could
	not be calculated it will be `None`.
	"""
	contents = response.content[:body_limit]

	title_match = _title_re.search(contents)
	title = title_match and strip_tags(title_match.group(1)) or None

	link_re = re.compile(r'<a[^>]+?"\s*%s\s*"[^>]*>(.*?)</a>(?is)' %
						 re.escape(url_hint))
	for chunk in _chunk_re.split(contents):
		match = link_re.search(chunk)
		if not match:
			continue
		before = chunk[:match.start()]
		after = chunk[match.end():]
		raw_body = '%s\0%s' % (strip_tags(before).replace('\0', ''),
							   strip_tags(after).replace('\0', ''))
		body_match = re.compile(r'(?:^|\b)(.{0,120})\0(.{0,120})(?:\b|$)') \
					   .search(raw_body)
		if body_match:
			break
	else:
		return title, None


	before, after = body_match.groups()
	link_text = strip_tags(match.group(1))
	if len(link_text) > 60:
		link_text = link_text[:60] + u' …'

	bits = before.split()
	bits.append(link_text)
	bits.extend(after.split())
	return title, u'[…] %s […]' % u' '.join(bits)

def pingback_post(response,source_uri, target_uri, slug):
	"""This is the pingback handler for posts."""
	entry = Entry.all().filter("published =", True).filter('link =', slug).get()
	#use allow_trackback as allow_pingback
	if entry is None or not entry.allow_trackback:
		raise Fault(33, 'no such post')
	title, excerpt = get_excerpt(response, target_uri)
	if not title:
		raise Fault(17, 'no title provided')
	elif not excerpt:
		raise Fault(17, 'no useable link to target')

	comment = Comment.all().filter("entry =", entry).filter("weburl =", source_uri).get()
	if comment:
		raise Fault(48, 'pingback has already been registered')
		return

	comment=Comment(author=urlparse(source_uri).hostname,
			content="<strong>"+title[:250]+"...</strong><br/>" +
					excerpt[:250] + '...',
			weburl=source_uri,
			entry=entry)
	comment.ctype=COMMENT_PINGBACK
	try:
		comment.save()
		g_blog.tigger_action("pingback_post",comment)
		memcache.delete("/"+entry.link)
		return True
	except:
		raise Fault(49,"Access denied.")
		return

##------------------------------------------------------------------------------
class PlogXMLRPCDispatcher(SimpleXMLRPCDispatcher):
	def __init__(self, funcs):
		SimpleXMLRPCDispatcher.__init__(self, True, 'utf-8')
		self.funcs = funcs
		self.register_introspection_functions()

dispatcher = PlogXMLRPCDispatcher({
	'blogger.getUsersBlogs' : blogger_getUsersBlogs,
	'blogger.deletePost' : blogger_deletePost,
	'blogger.getUserInfo': blogger_getUserInfo,

	'metaWeblog.newPost' : metaWeblog_newPost,
	'metaWeblog.editPost' : metaWeblog_editPost,
	'metaWeblog.getCategories' : metaWeblog_getCategories,
	'metaWeblog.getPost' : metaWeblog_getPost,
	'metaWeblog.getRecentPosts' : metaWeblog_getRecentPosts,
	'metaWeblog.newMediaObject':metaWeblog_newMediaObject,

	'wp.getUsersBlogs':wp_getUsersBlogs,
	'wp.getTags':wp_getTags,
	'wp.getCommentCount':wp_getCommentCount,
	'wp.getPostStatusList':wp_getPostStatusList,
	'wp.getPageStatusList':wp_getPageStatusList,
	'wp.getPageTemplates':wp_getPageTemplates,
	'wp.getOptions':wp_getOptions,
	'wp.setOptions':wp_setOptions,
	'wp.getCategories':metaWeblog_getCategories,
	'wp.newCategory':wp_newCategory,
	'wp.newPage':wp_newPage,
	'wp.getPage':wp_getPage,
	'wp.getPages':wp_getPages,
	'wp.editPage':wp_editPage,
	'wp.getPageList':wp_getPageList,
	'wp.deletePage':wp_deletePage,
	'wp.getAuthors':wp_getAuthors,
	'wp.deleteComment':wp_deleteComment,
	'wp.editComment':wp_editComment,
	'wp.newComment':wp_newComment,
	'wp.getCommentStatusList':wp_getCommentStatusList,
	'wp.deleteCategory':wp_deleteCategory,
	'wp.suggestCategories':wp_suggestCategories,
	'wp.getComment':wp_getComment,
	'wp.getComments':wp_getComments,
	'wp.uploadFile':metaWeblog_newMediaObject,

	'mt.setPostCategories':mt_setPostCategories,
	'mt.getPostCategories':mt_getPostCategories,
	'mt.getCategoryList':mt_getCategoryList,
	'mt.publishPost':mt_publishPost,
	'mt.getRecentPostTitles':mt_getRecentPostTitles,

	##pingback
	'pingback.ping':pingback_ping,



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
				('/xmlrpc\.php',CallApi),
				('/rpc/view', View),
				('/rpc/dellog', DeleteLog),

				],
			debug=True)
	wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
	main()

