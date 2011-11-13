# -*- coding: utf-8 -*-
from micolog_plugin import *
from BeautifulSoup import *
from datetime import datetime
from model import Entry,Comment,Media
import logging,math
import re
from base import BaseRequestHandler,urldecode


class Importhandler(BaseRequestHandler):
	def post(self):

		if not self.is_login:
			self.redirect(users.create_login_url(self.request.uri))
		filename=self.param('filename')
		do_comment=self.paramint('c',0)
		if filename[:4]=='img/':#处理图片
			new_filename=filename.split('/')[1]
			mtype =new_filename.split('.')[1]
			bits = self.request.body
			media=Media.all().filter('name =',new_filename)
			if media.count()>0:
				media=media[0]
			else:
				media=Media()
			media.name=new_filename
			media.mtype=mtype
			media.bits=bits
			media.put()
			bid='_'.join(new_filename.split('_')[:-1])
			entries=Entry.all().filter('slug =',bid)
			if entries.count()>0:
				entry=entries[0]
				entry.content=entry.content.replace(filename,'/media/'+str(media.key()))
				entry.put()
			return

		if filename=="index.html" or filename[-5:]!='.html':
			return
		#处理html页面
		bid=filename[:-5]
		try:

			soup=BeautifulSoup(self.request.body)
			bp=soup.find(id='bp')
			title=self.getChineseStr( soup.title.text)
			logging.info(bid)
			pubdate=self.getdate( bp.find(id='bp-'+bid+'-publish').text)
			body=bp.find('div','blogpost')

			entries=Entry.all().filter('title = ',title)
			if entries.count()<1:
				entry=Entry()
			else:
				entry=entries[0]
##			entry=Entry.get_by_key_name(bid)
##			if not entry:
##				entry=Entry(key_name=bid)
			entry.slug=bid
			entry.title=title
			entry.author_name=self.login_user.nickname()
			entry.date=pubdate
			entry.settags("")
			entry.content=unicode(body)
			entry.author=self.login_user

			entry.save(True)
			if do_comment>0:
				comments=soup.find('div','comments','div')
				if comments:
					for comment in comments.contents:
						name,date=comment.h5.text.split(' - ')
						# modify by lastmind4
						name_date_pair = comment.h5.text
						if name_date_pair.index('- ') == 0:
							name_date_pair = 'Anonymous ' + name_date_pair
						name,date=name_date_pair.split(' - ')

						key_id=comment.h5['id']
						date=self.getdate(date)
						content=comment.contents[1].text
						comment=Comment.get_or_insert(key_id,content=content)
						comment.entry=entry
						comment.date=date
						comment.author=name
						comment.save()

		except Exception,e :
			logging.info("import error: %s"%e.message)

	def getdate(self,d):
		try:
			ret=datetime.strptime(d,"%Y/%m/%d %H&#58;%M&#58;%S")
		except:
			try:
				ret=datetime.strptime(d,"%m/%d/%Y %H&#58;%M&#58;%S %p")
			except:
				ret=datetime.now()
		return ret

	def getChineseStr(self,s):
		return re.sub(r'&#(\d+);',lambda x:unichr(int(x.group(1))) ,s)

class live_import(Plugin_importbase):
	def __init__(self):
		Plugin_importbase.__init__(self,__file__,"spaces.live.com","Plugin for import entries from space.zip.")
		self.author="xuming"
		self.authoruri="http://xuming.net"
		self.uri="http://xuming.net"
		self.description='''Plugin for import entries from space.zip.<br>
		将Spaces.Live.com博客导入到Micolog.'''
		self.name="LiveSapce Import"
		self.version="0.12"
		self.register_urlzip('/admin/live_import/swfupload/(.*)','swfupload.zip')
		self.register_urlhandler('/admin/live_import/import',Importhandler)



	def get(self,page):
		return self.render_content("import.html",{'name':self.name})

