import os,logging,re
from model import OptionSet
from google.appengine.ext.webapp import template
from google.appengine.ext import zipserve
RE_FIND_GROUPS = re.compile('\(.*?\)')
class PluginIterator:
	def __init__(self, plugins_path='plugins'):
		self.iterating = False
		self.plugins_path = plugins_path
		self.list = []
		self.cursor = 0

	def __iter__(self):
		return self

	def next(self):
		if not self.iterating:
			self.iterating = True
			self.list = os.listdir(self.plugins_path)
			self.cursor = 0

		if self.cursor >= len(self.list):
			self.iterating = False
			raise StopIteration
		else:
			value = self.list[self.cursor]
			self.cursor += 1
			if os.path.isdir(os.path.join(self.plugins_path, value)):
				return (value,'%s.%s.%s'%(self.plugins_path,value,value))
			elif value.endswith('.py') and not value=='__init__.py':
				value=value[:-3]
				return (value,'%s.%s'%(self.plugins_path,value))
			else:
				return self.next()

class Plugins:
	def __init__(self,blog=None):
		self.blog=blog
		self.list={}
		self._filter_plugins={}
		self._action_plugins={}
		self._urlmap={}
		self._handlerlist={}
		self._setupmenu=[]
		pi=PluginIterator()
		self.active_list=OptionSet.getValue("PluginActive",[])
		for v,m in pi:
			try:
				#import plugins modules
				mod=__import__(m,globals(),locals(),[v])
				plugin=getattr(mod,v)()
				#internal name
				plugin.iname=v
				plugin.active=v in self.active_list
				plugin.blog=self.blog
				self.list[v]=plugin
			except:
				pass

	def add_urlhandler(self,plugin,application):
		for regexp,handler in plugin._handlerlist.items():
			try:
				application._handler_map[handler.__name__] = handler
				if not regexp.startswith('^'):
					regexp = '^' + regexp
				if not regexp.endswith('$'):
					regexp += '$'
				compiled = re.compile(regexp)
				application._url_mapping.insert(-2,(compiled, handler))

				num_groups = len(RE_FIND_GROUPS.findall(regexp))
				handler_patterns = application._pattern_map.setdefault(handler, [])
				handler_patterns.insert(-2,(compiled, num_groups))
			except:
				pass

	def remove_urlhandler(self,plugin,application):
		for regexp,handler in plugin._handlerlist.items():
			try:
				if application._handler_map.has_key(handler.__name__):
					del application._handler_map[handler.__name__]
					for um in application._url_mapping:
						if um[1].__name__==handler.__name__:
							del um
							break
					for pm in application._pattern_map:
						if pm.__name__==handler.__name__:
							del pm
							break

			except:
				pass

	def register_handlerlist(self,application):
		for name,item in self.list.items():
			if item.active and item._handlerlist:
				self.add_urlhandler(item,application)


	def reload(self):
		pass

	def __getitem__(self,index):
		return self.list.values()[index]

	def getPluginByName(self,iname):
		if self.list.has_key(iname):
			return self.list[iname]
		else:
			return None

	def activate(self,iname,active):
		if active:
			plugin=self.getPluginByName(iname)
			if plugin:
				if (iname not in self.active_list):
					self.active_list.append(iname)
					OptionSet.setValue("PluginActive",self.active_list)
				plugin.active=active
				#add filter
				for k,v in plugin._filter.items():
					if self._filter_plugins.has_key(k):
						if not v in self._filter_plugins[k]:
							self._filter_plugins[k].append(v)
				#add action
				for k,v in plugin._action.items():
					if self._action_plugins.has_key(k):
						if not v in self._action_plugins[k]:
							self._action_plugins[k].append(v)
				if self.blog.application:
					self.add_urlhandler(plugin,self.blog.application)

		else:
			plugin=self.getPluginByName(iname)
			if plugin:
				if (iname in self.active_list):
					self.active_list.remove(iname)
					OptionSet.setValue("PluginActive",self.active_list)
				plugin.active=active
				#remove filter
				for k,v in plugin._filter.items():
					if self._filter_plugins.has_key(k):
						if v in self._filter_plugins[k]:
							self._filter_plugins[k].remove(v)
				#remove action
				for k,v in plugin._action.items():
					if self._action_plugins.has_key(k):
						if v in self._action_plugins[k]:
							self._action_plugins[k].remove(v)
				if self.blog.application:
					self.remove_urlhandler(plugin,self.blog.application)
		self._urlmap={}
		self._setupmenu=[]


	def filter(self,attr,value):
		rlist=[]
		for item in self:
			if item.active and hasattr(item,attr) and getattr(item,attr)==value:
				rlist.append(item)
		return rlist

	def get_filter_plugins(self,name):
		if not self._filter_plugins.has_key(name) :
			for item in self:
				if item.active and hasattr(item,"_filter") :
					if item._filter.has_key(name):
						if	self._filter_plugins.has_key(name):
							self._filter_plugins[name].append(item._filter[name])
						else:
							self._filter_plugins[name]=[item._filter[name]]



		if self._filter_plugins.has_key(name):
			return tuple(self._filter_plugins[name])
		else:
			return ()

	def get_action_plugins(self,name):
		if not self._action_plugins.has_key(name) :
			for item in self:
				if item.active and hasattr(item,"_action") :
					if item._action.has_key(name):
						if	self._action_plugins.has_key(name):
							self._action_plugins[name].append(item._action[name])
						else:
							self._action_plugins[name]=[item._action[name]]

		if self._action_plugins.has_key(name):
			return tuple(self._action_plugins[name])
		else:
			return ()

	def get_urlmap_func(self,url):
		if not self._urlmap:
			for item in self:
				if item.active:
					self._urlmap.update(item._urlmap)
		if self._urlmap.has_key(url):
			return self._urlmap[url]
		else:
			return None
	
	def get_setupmenu(self):
		#Get menu list for admin setup page
		if not self._setupmenu:
			for item in self:
				if item.active:
					self._setupmenu+=item._setupmenu
		return self._setupmenu	

	def get_handlerlist(self,url):
		if not self._handlerlist:
			for item in self:
				if item.active:
					self._handlerlist.update(item._handlerlist)
		if self._handlerlist.has_key(url):
			return self._handlerlist[url]
		else:
			return {}



	def tigger_filter(self,name,content,*arg1,**arg2):
		for func in self.get_filter_plugins(name):
			content=func(content,*arg1,**arg2)
		return content

	def tigger_action(self,name,*arg1,**arg2):
		for func in self.get_action_plugins(name):
			func(*arg1,**arg2)

	def tigger_urlmap(self,url,*arg1,**arg2):
		func=self.get_urlmap_func(url)
		if func:
			func(*arg1,**arg2)
			return True
		else:
			return None

class Plugin:
	def __init__(self,pfile=__file__):
		self.name="Unnamed"
		self.author=""
		self.description=""
		self.uri=""
		self.version=""
		self.authoruri=""
		self.template_vals={}
		self.dir=os.path.dirname(pfile)
		self._filter={}
		self._action={}
		self._urlmap={}
		self._handlerlist={}
		self._urlhandler={}
		self._setupmenu=[]

	def get(self,page):
		return "<h3>%s</h3><p>%s</p>"%(self.name,self.description)

	def render_content(self,template_file,template_vals={}):
		"""
		Helper method to render the appropriate template
		"""
		self.template_vals.update(template_vals)
		path = os.path.join(self.dir, template_file)
		return template.render(path, self.template_vals)

	def error(self,msg=""):
		return  "<h3>Error:%s</h3>"%msg

	def register_filter(self,name,func):
		self._filter[name]=func


	def register_action(self,name,func):
		self._action[name]=func

	def register_urlmap(self,url,func):
		self._urlmap[url]=func

	def register_urlhandler(self,url,handler):
		self._handlerlist[url]=handler

	def register_urlzip(self,name,zipfile):
		zipfile=os.path.join(self.dir,zipfile)
		self._handlerlist[name]=zipserve.make_zip_handler(zipfile)
		
	def register_setupmenu(self,m_id,title,url):
		#Add menu to admin setup page.
		#m_id is a flag to check current page
		self._setupmenu.append({'m_id':m_id,'title':title,'url':url})


class Plugin_importbase(Plugin):
	def __init__(self,pfile,name,description=""):
		Plugin.__init__(self,pfile)
		self.is_import_plugin=True
		self.import_name=name
		self.import_description=description

	def post(self):
		pass

