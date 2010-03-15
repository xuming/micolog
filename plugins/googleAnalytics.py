from micolog_plugin import *
from model import OptionSet
class googleAnalytics(Plugin):
	def __init__(self):
		Plugin.__init__(self,__file__)
		self.author="xuming"
		self.authoruri="http://xuming.net"
		self.uri="http://xuming.net"
		self.description="Plugin for put google Analytics into micolog."
		self.name="google Analytics"
		self.version="0.1"
		self.register_filter('footer',self.filter)

	def filter(self,content,*arg1,**arg2):
		code=OptionSet.getValue("googleAnalytics_code",default="")
		return content+str(code)

	def get(self,page):
		code=OptionSet.getValue("googleAnalytics_code",default="")
		return '''<h3>Google Anslytics</h3>
					<form action="" method="post">
					<p>Analytics Code:</p>
					<textarea name="code" style="width:500px;height:100px">%s</textarea>
					<br>
					<input type="submit" value="submit">
					</form>'''%code

	def post(self,page):
		code=page.param("code")
		OptionSet.setValue("googleAnalytics_code",code)
		return self.get(page)
