from micolog_plugin import *
import logging,os
from model import *
from google.appengine.api import users
class xheditor(Plugin):
	def __init__(self):
		Plugin.__init__(self,__file__)
		self.author="xuming"
		self.authoruri="http://xuming.net"
		self.uri="http://xuming.net"
		self.description="xheditor."
		self.name="xheditor plugin"
		self.version="0.1"
		self.register_urlzip('/xheditor/(.*)','xheditor.zip')
		self.register_filter('editor_header',self.head)



	def head(self,content,blog=None,*arg1,**arg2):
		if blog.language=='zh_CN':
			js='xheditor-zh-cn.js'
		else:
			js='xheditor-en.js'
		sret='''<script type="text/javascript" src="/xheditor/%s"></script>
<script type="text/javascript">
$(function(){
  $("#content").xheditor(true,{
  upImgUrl:'!/admin/uploadex?ext=jpg|png|jpeg|gif',
  upFlashUrl:'!/admin/uploadex?ext=swf',
  upMediaUrl:'!/admin/uploadex?ext=wmv|avi|wma|mp3|mid'});
});

</script>'''%js
		return sret


	def get(self,page):
		return '''<h3>xheditor Plugin </h3>
			   <p>This is a demo for write editor plugin.</p>
			   <h4>feature</h4>
			   <p><ol>
			   <li>Change editor as xheditor.</li>
			   </ol></p>
				'''
