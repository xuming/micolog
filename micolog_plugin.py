import os,logging
from model import OptionSet
from google.appengine.ext.webapp import template

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
	def __init__(self):
		self.list={}
		self._filter_plugins={}
		self._action_plugins={}
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
				self.list[v]=plugin
			except:
				pass

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

	def tigger_filter(self,name,content,*arg1,**arg2):
		logging.info(name)
		for func in self.get_filter_plugins(name):
		    content=func(content,*arg1,**arg2)
		return content

	def tigger_action(self,name,*arg1,**arg2):
		for func in self.get_action_plugins(name):
			func(*arg1,**arg2)



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


class Plugin_importbase(Plugin):
	def __init__(self,pfile,name,description=""):
		Plugin.__init__(self,pfile)
		self.is_import_plugin=True
		self.import_name=name
		self.import_description=description

	def post(self):
		pass

