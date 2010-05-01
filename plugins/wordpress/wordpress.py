from micolog_plugin import *
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue
from wp_import import *
from model import *
import logging,math
from django.utils import simplejson
from base import BaseRequestHandler,urldecode


class waphandler(BaseRequestHandler):
	def get(self):
		if not self.is_login:
			self.redirect(users.create_login_url(self.request.uri))

		action=self.param('action')

		if action=='stop':
			memcache.delete("imt")
			#OptionSet.remove('wpimport_data')
			self.write('"ok"')
			return

		imt=memcache.get('imt')
		#imt=OptionSet.getValue('wpimport_data')
		if imt and imt.cur_do:
			process=100-math.ceil(imt.count()*100/imt.total)
			if imt.cur_do[0]=='cat':
				msg="importing category '%s'"%imt.cur_do[1]['name']
			elif imt.cur_do[0]=='entry':
				msg="importing entry '%s'"%imt.cur_do[1]['title']
			else:
				msg="start importing..."
			self.write(simplejson.dumps((process,msg,not process==100)))
		else:
			self.write(simplejson.dumps((-1,"Have no data to import!",False)))

	def post(self):
		if not self.is_login:
			self.redirect(users.create_login_url(self.request.uri))


		try:
				#global imt
				imt=memcache.get("imt")
				#imt=OptionSet.getValue('wpimport_data')
				import_data=imt.pop()
				#if tdata=='men':
				memcache.set('imt',imt)
				#else:
				#	OptionSet.setValue('wpimport_data',imt)

				if import_data:
					try:
						if import_data[0]=='cat':

							_cat=import_data[1]
							nicename=_cat['slug']
							cat=Category.get_by_key_name(nicename)
							if not cat:
								cat=Category(key_name=nicename)
							cat.name=_cat['name']
							cat.slug=nicename
							cat.put()
						elif import_data[0]=='entry':
							_entry=import_data[1]
							logging.debug('importing:'+_entry['title'])
							hashkey=str(hash(_entry['title']))
							entry=Entry.get_by_key_name(hashkey)
							if not entry:
								entry=Entry(key_name=hashkey)

							entry.title=_entry['title']
							entry.author=self.login_user
							entry.is_wp=True
						   #entry.date=datetime.strptime( _entry['pubDate'],"%a, %d %b %Y %H:%M:%S +0000")
							try:
								entry.date=datetime.strptime( _entry['pubDate'][:-6],"%a, %d %b %Y %H:%M:%S")
							except:
								try:
									entry.date=datetime.strptime( _entry['pubDate'][0:19],"%Y-%m-%d %H:%M:%S")
								except:
									entry.date=datetime.now()
							entry.entrytype=_entry['post_type']
							entry.content=_entry['content']

							entry.excerpt=_entry['excerpt']
							entry.post_id=_entry['post_id']
							entry.slug=urldecode(_entry['post_name'])
							entry.entry_parent=_entry['post_parent']
							entry.menu_order=_entry['menu_order']

							for cat in _entry['categories']:
								c=Category.get_by_key_name(cat['slug'])
								if c:
									entry.categorie_keys.append(c.key())
							entry.settags(','.join(_entry['tags']))
				##				for tag in _entry['tags']:
				##					entry.tags.append(tag)
							if _entry['published']:
								entry.save(True)
							else:
								entry.save()
							for com in _entry['comments']:
									try:
										date=datetime.strptime(com['date'][0:19],"%Y-%m-%d %H:%M:%S")
									except:
										date=datetime.now()
									comment=Comment(author=com['author'],
													content=com['content'],
													entry=entry,
													date=date
													)
									try:
										comment.email=com['email']
										comment.weburl=com['weburl']
									except:
										pass
									comment.save()
					finally:
						queue=taskqueue.Queue("import")
						queue.add(taskqueue.Task( url="/admin/wp_import"))
		except Exception,e :
			logging.info("import error: %s"%e.message)


class wordpress(Plugin_importbase):
	def __init__(self):
		Plugin_importbase.__init__(self,__file__,"wordpress","Import posts, pages, comments, categories, and tags from a WordPress export file.")
		self.author="xuming"
		self.authoruri="http://xuming.net"
		self.uri="http://xuming.net"
		self.description="Plugin for import wxr file."
		self.name="Wordpress Import"
		self.version="0.7"
		self.register_urlhandler('/admin/wp_import',waphandler)

	def get(self,page):
		return self.render_content("wpimport.html",{'name':self.name})

	def post(self,page):
		try:

			queue=taskqueue.Queue("import")
			wpfile=page.param('wpfile')
			#global imt
			imt=import_wordpress(wpfile)
			imt.parse()
			#OptionSet.setValue('wpimport_data',imt)

			memcache.set("imt",imt)
			queue.add(taskqueue.Task( url="/admin/wp_import"))
			return self.render_content("wpimport.html",{'postback':True})

		except Exception , e:

			return self.error("Import Error:<p  style='color:red;font-size:11px;font-weight:normal'>%s</p>"%e.message)
