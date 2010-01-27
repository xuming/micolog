from micolog_plugin import *
import logging
from model import *
from google.appengine.api import users
class sys_plugin(Plugin):
	def __init__(self):
		Plugin.__init__(self,__file__)
		self.author="xuming"
		self.authoruri="http://xuming.net"
		self.uri="http://xuming.net"
		self.description="SysPlugin."
		self.name="sys plugin"
		self.version="0.7"
		self.blocklist=OptionSet.getValue("sys_plugin_blocklist",default="")
		self.register_filter('head',self.head)
		self.register_filter('footer',self.footer)
		self.register_urlmap('sys_plugin/setup',self.setup)
		self.register_action('pre_comment',self.pre_comment)



	def head(self,content,blog=None,*arg1,**arg2):
	    return content+'<meta name="generator" content="Micolog %s" />'%blog.version

	def footer(self,content,blog=None,*arg1,**arg2):
	    return content+'<!--Powered by micolog %s-->'%blog.version

	def setup(self,page=None,*arg1,**arg2):
		if not page.is_login:
			page.redirect(users.create_login_url(page.request.uri))
		tempstr='''blocklist:
			<form action="" method="post">
			<p>
			<textarea name="ta_list" style="width:400px;height:300px">%s</textarea>
			</p>
			<input type="submit" value="submit">
			</form>'''
		if page.request.method=='GET':
			page.render2('views/admin/base.html',{'content':tempstr%self.blocklist})
		else:
			self.blocklist=page.param("ta_list")
			OptionSet.setValue("sys_plugin_blocklist",self.blocklist)
			page.render2('views/admin/base.html',{'content':tempstr%self.blocklist})

	def get(self,page):
		return '''<h3>Sys Plugin Demo</h3>
			   <p>This is a demo for write plugin.</p>
			   <h4>feature</h4>
			   <p><ol>
			   <li>Add Meta &lt;meta name="generator" content="Micolog x.x" /&gt;</li>
			   <li>Add footer "&lt;!--Powered by micolog x.x--&gt;"</li>
			   <li>Comments Filter with blocklist <a href="/e/sys_plugin/setup">Setup</a></li>
			   </ol></p>
				'''

	def pre_comment(self,comment,*arg1,**arg2):
		for s in self.blocklist.splitlines():
			if comment.content.find(s)>-1:
   				raise Exception