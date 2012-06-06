#!/usr/bin/env python
#coding=utf-8

'''
Created on 2010-4-27
GPL License
@author: sypxue@gmail.com
'''

import urllib,pickle,StringIO
from micolog_plugin import *
from google.appengine.ext import db
from model import OptionSet,Comment,Blog,Entry,Blog
from google.appengine.api import urlfetch

class akismet(Plugin):
	def __init__(self):
		Plugin.__init__(self,__file__)
		self.author="sypxue"
		self.authoruri="http://sypxue.appspot.com"
		self.uri="http://sypxue.appspot.com"
		self.description="""Wordpress自带的Akismet插件的micolog版本,现在已实现过滤Spam,提交Spam,解除Spam等功能,开启即可使用,也可输入自己的Akismet API Key使用 。Author: sypxue@gmail.com"""
		self.name="Akismet"
		self.version="0.3.2"
		self.AKISMET_VERSION = "2.2.7"
		self.AKISMET_default_Key = "80e9452f5962"
		self.register_action("pre_comment",self.pre_comment)
		self.register_action("save_comment",self.save_comment)
	
	def comment_handler(self,comment,action,*arg1,**arg2):
		# rm 指示 是否自动过滤掉评论
		rm=OptionSet.getValue("Akismet_AutoRemove",False)
		if action=='pre' and rm!=True:
			return
		elif action=='save' and rm==True:
			return
		url = arg2['blog'].baseurl
		user_agent = os.environ.get('HTTP_USER_AGENT','')
		referrer = os.environ.get('HTTP_REFERER', 'unknown')
		AkismetItem = {
			'user_agent':user_agent,
			'referrer':referrer,
			'user_ip' : comment.ip,
			'comment_type' : 'comment', 
			'comment_author' : comment.author.encode('utf-8'),
			'comment_author_email' : comment.email,
			'comment_author_url' : comment.weburl,
			'comment_content' : comment.content.encode('utf-8')
		}
		apikey = OptionSet.getValue("Akismet_code",default=self.AKISMET_default_Key)
		if len(apikey)<5:
			apikey = self.AKISMET_default_Key
		m = AkismetManager(apikey,url)
		if m.IsSpam(AkismetItem):
			if rm==True:
				raise ''
			sComments=OptionSet.getValue("Akismet_Comments_v0.3",[])
			if type(sComments)!=type([]):
				sComments=[]
			db.Model.put(comment)
			sComments.append({'key':(str(comment.key()),str(comment.entry.key())),
				'other':{'user_agent':user_agent,'referrer':referrer,'url':url}})
			OptionSet.setValue("Akismet_Comments_v0.3",
				sComments)
			comment.entry.commentcount-=1
			comment.entry.put()
			e,comment.entry = comment.entry,None
			try:
				db.Model.put(comment)
				comment.entry = e
			except:
				pass		
	
	def pre_comment(self,comment,*arg1,**arg2):
		self.comment_handler(comment,'pre',*arg1,**arg2)
	
	def save_comment(self,comment,*arg1,**arg2):
		self.comment_handler(comment,'save',*arg1,**arg2)

	def filter(self,content,*arg1,**arg2):
		code=OptionSet.getValue("Akismet_code",default="")
		return content+str(code)

	def SubmitAkismet(self,item,url,f):
		apikey = OptionSet.getValue("Akismet_code",default=self.AKISMET_default_Key)
		if len(apikey)<5:
			apikey = self.AKISMET_default_Key
		m = AkismetManager(apikey,url)
		try:
			if f=="Ham":
				m.SubmitHam(item)
			elif f=="Spam":
				m.SubmitSpam(item)
		except:
			pass
		
	def get(self,page):
		code=OptionSet.getValue("Akismet_code",default="")
		up=OptionSet.getValue("Akismet_Comments_v0.3",default=[])
		rm=OptionSet.getValue("Akismet_AutoRemove",False)
		if type(up)!=type([]):
			up=[]
		delkey = page.param('delkey')
		rekey = page.param('rekey')
		if rekey or delkey:
			newup = []
			for i in up:
				cmtkey = i['key'][0];
				enykey = i['key'][1];
				if delkey and cmtkey==delkey:
					cm = Comment.get(cmtkey)
					db.Model.delete(cm)
				elif rekey and cmtkey==rekey:
					cm = Comment.get(cmtkey)
					eny = Entry.get(enykey)
					eny.commentcount+=1
					eny.put()
					cm.entry = eny
					db.Model.put(cm)
					self.SubmitAkismet({
						'user_agent':i['other']['user_agent'],
						'referrer':i['other']['referrer'],
						'user_ip' : cm.ip,
						'comment_type' : 'comment', 
						'comment_author' : cm.author.encode('utf-8'),
						'comment_author_email' : cm.email,
						'comment_author_url' : cm.weburl,
						'comment_content' : cm.content.encode('utf-8')
					},i['other'].get('url',''),"Ham")
				else:
					newup.append(i)
			if not len(up)==len(newup):
				OptionSet.setValue("Akismet_Comments_v0.3",newup)
			up = newup
		cmts = [(Comment.get(i['key'][0]),Entry.get(i['key'][1])) for i in up]
		comments = [u'<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td><a target="_blank" href="/%s">%s</a></td><td><a href="?delkey=%s" title="删除">删除</a> <a href="?rekey=%s" title="这不是一个垃圾评论">还原</a></td></tr>'%(i[0].date,
			i[0].author,i[0].content,i[0].email,i[0].ip,i[1].link,i[1].title,str(i[0].key()),str(i[0].key())) for i in cmts if i is not None and i[0] is not None]
		comments = ''.join(comments)
		apikey = OptionSet.getValue("Akismet_code",default=self.AKISMET_default_Key)
		if len(apikey)<5:
			apikey = self.AKISMET_default_Key
		api =  AkismetManager(apikey,Blog.all()[0].baseurl)
		if not code:
			status = ''
		elif api.IsValidKey():
			status = 'True'
		else:
			status = 'False'
		if rm==True:
			rmchecked='checked="checked"'
		else:
			rmchecked=''
		return u'''<h3>Akismet</h3>
					<form action="" method="post">
					<p>Akismet Api Key:</p>
					<input name="code" style="width:400px;" value="%s"> %s
					<br />
					<p>自动删除检测到的垃圾评论：
					<input type="checkbox" name="autorm" value="1" %s></p>
					<p>删除一条正常的评论并提交Spam(输入评论的ID):</p>
					<input name="spam" style="width:400px;" value="">
					<br />
					<input type="submit" value="submit">
					</form>
				  <div>
				  	<br />
				  	<h3>被过滤的评论</h3> <table class="widefat"><thead><tr><th>日期</th><th>作者</th><th>内容</th><th>电子邮件</th><th>IP地址</th><th>文章/页面</th><th style="width:15%%;">选择操作</th></tr></thead><tbody>%s </tbody></table>
				  </div>'''%(code,status,rmchecked,comments)
	
	def post(self,page):
		code=page.param("code")
		OptionSet.setValue("Akismet_code",code)
		rm=page.param('autorm')
		if rm and int(rm)==1:
			rm=True
		else:
			rm=False
		oldrm = OptionSet.getValue("Akismet_AutoRemove",False)
		if oldrm!=rm:
			OptionSet.setValue("Akismet_AutoRemove",rm)
		spam=page.param("spam")
		spam = len(spam)>0 and int(spam) or 0
		sOther = ""
		if spam>0:
			cm = Comment.get_by_id(spam)
			try:
				url = Blog.all().fetch(1)[0].baseurl
				self.SubmitAkismet({
					'user_ip' : cm.ip,
					'comment_type' : 'comment', 
					'comment_author' : cm.author.encode('utf-8'),
					'comment_author_email' : cm.email,
					'comment_author_url' : cm.weburl,
					'comment_content' : cm.content.encode('utf-8')
				},url,"Spam")
				sOther = u"<div style='padding:8px;margin:8px;border:1px solid #aaa;color:red;'>评论已删除</div>"
				cm.delit()
			except:
				sOther = u"<div style='padding:8px;margin:8px;border:1px solid #aaa;color:red;'>无法找到对应的评论项</div>"
		return sOther + self.get(page)


class AkismetManager():
	def __init__(self,key,url):
		self.ApiKey = key
		self.Url = url
		
	def ExecuteRequest(self,url,content,method="GET"):
		request = urlfetch.fetch(url,
			method='POST',
			payload=content
			)
		return request
		
	def IsValidKey(self):
		content = "key=%(key)s&blog=%(url)s&"%{'key':self.ApiKey,'url':self.Url}
		response = self.ExecuteRequest("http://rest.akismet.com/1.1/verify-key", 
			content).content
		if response and response == 'valid':
			return True
		else:
			return False
		
	def IsSpam(self,item=None):
		if not item:
			raise Exception
		content = self.AddDefaultFields(urllib.urlencode(item))
		response = self.ExecuteRequest(
			"http://%(key)s.rest.akismet.com/1.1/comment-check"%{'key':self.ApiKey},
			content).content
		if response:
			result = {'true':True,'false': False}
			return result[response]
		return  False
		
	def SubmitSpam(self,item):
		if not item:
			raise Exception
		content = self.AddDefaultFields(urllib.urlencode(item))
		response = self.ExecuteRequest(
			"http://%(key)s.rest.akismet.com/1.1/submit-spam"%{'key':self.ApiKey},
			content).content
		if response == 'invalid':
			raise Exception
		elif len(response)>0:
			raise Exception
		
	def SubmitHam(self,item):
		if not item:
			raise Exception
		content = self.AddDefaultFields(urllib.urlencode(item))
		response = self.ExecuteRequest(
			"http://%(key)s.rest.akismet.com/1.1/submit-ham"%{'key':self.ApiKey},
			content).content
		if response == 'invalid':
			raise Exception
		elif len(response)>0:
			raise Exception
	
	def AddDefaultFields(self,content):
		return ''.join(["key=%(key)s&blog=%(url)s&"%{'key':self.ApiKey,'url':self.Url},content])
