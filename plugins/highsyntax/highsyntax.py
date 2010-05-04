from micolog_plugin import *
import logging
from model import *
from google.appengine.api import users
class highsyntax(Plugin):
	def __init__(self):
		Plugin.__init__(self,__file__)
		self.author="xuming"
		self.authoruri="http://xuming.net"
		self.uri="http://xuming.net"
		self.description="HighSyntax Plugin."
		self.name="HighSyntax plugin"
		self.version="0.1"
		self.register_filter('footer',self.footer)
		self.register_urlzip('/syntaxhighlighter/(.*)','syntaxhighlighter.zip')
		self.theme=OptionSet.getValue("highsyntax_theme",default="Default")


	def footer(self,content,blog=None,*arg1,**arg2):
		return content+'''
<script type="text/javascript">
if ($('pre[class^=brush:]').length > 0)
{
	$.getScript("/syntaxhighlighter/scripts/shCore.js", function() {
		SyntaxHighlighter.boot("/syntaxhighlighter/", {theme : "'''+str(self.theme)+'''", stripBrs : true}, {});
	});
}
</script>
'''

	def get(self,page):
		return '''<h3>HighSyntax Plugin</h3>
			   <p>HighSyntax plugin for micolog.</p>
			   <p>This plugin based on <a href="http://alexgorbatchev.com/wiki/SyntaxHighlighter" target="_blank">SyntaxHighlighter</a>
			    and <a href="http://www.outofwhatbox.com/blog/syntaxhighlighter-downloads/" target="_blank">SyntaxHighlighter.boot()</a></p>
				<form action="" method="post">
			   <p><B>Require:</B>
					<ol>
					<li><b>{%mf footer%} </b>in template "base.html".</li>
					<li><a href="http://jquery.org"  target="_blank">Jquery</a> version 1.3.2 or new.</li>
					</ol>
			   </p>
			   <p><b>Theme:</b>
			   </p>
				<p>
				<select name="theme" id="theme">
	<option value="Default">Default</option>
	<option value="Django">Django</option>
	<option value="Eclipse">Eclipse</option>
	<option value="Emacs">Emacs</option>
	<option value="FadeToGrey">FadeToGrey</option>
	<option value="Midnight">Midnight</option>
	<option value="RDark">RDark</option>
</select>
</p>
			   <p>
			   <input type="submit" value="submit">
			   </p>
				</form>
<script>
$("#theme").val("'''+str(self.theme)+'''");</script>
				'''

	def post(self,page):
		self.theme=page.param("theme")
		OptionSet.setValue("highsyntax_theme",self.theme)
		return self.get(page)