#-------------------------------------------------------------------------------
# Name:        gaedbimporter
# Purpose:
#
# Author:      Xuming
#
# Created:     16-11-2010
#-------------------------------------------------------------------------------
#!/usr/bin/env python

import sys,  imp, new
class gaedbimporter(object):
	def __init__(self, item, *args, **kw):
		if item != "gaedb":
			raise ImportError

	def is_package(self,fullname):
		return True

	def get_code(self,fullname):
		return  compile(self.get_source(fullname), "db:%s" % fullname, "exec")

	def	get_source(self,fullname):
		return '''def test():
		    		print 'testff' '''

	def find_module(self, fullname, path=None):
		if fullname=='dbtest':
			return self
		else:
			return None

	def load_module(self, fullname):
		print "load_module:", fullname
		ispkg=True
		code=self.get_code(fullname)

		#ispkg, code = self._get_code(fullname)
		#mod = sys.modules.setdefault(fullname, imp.new_module(fullname))
		mod=sys.modules.values()[0]
		mod.__file__ = "<%s>" % self.__class__.__name__
		mod.__loader__ = self
		if ispkg:
			mod.__path__ = []
		mod=sys.modules.setdefault(fullname,mod)
		print sys.modules
		#print mod.__dict__
		exec code in mod.__dict__
		return mod

	@classmethod
	def install(cls):
		sys.path_hooks.append(gaedbimporter)
		sys.path_importer_cache.clear() # probably not necessary
		sys.path.insert(0, "gaedb")

if __name__ == "__main__":
	gaedbimporter.install()
	from dbtest import *
	test()

