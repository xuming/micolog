# gmemsess.py - memcache-backed session Class for Google Appengine
# Version 1.4
#	Copyright 2008 Greg Fawcett <greg@vig.co.nz>
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <http://www.gnu.org/licenses/>.

import random
from google.appengine.api import memcache

_sidChars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
_defaultTimeout=30*60 # 30 min
_defaultCookieName='gsid'

#----------------------------------------------------------------------
class Session(dict):
	"""A secure lightweight memcache-backed session Class for Google Appengine."""

	#----------------------------------------------------------
	def __init__(self,rh,name=_defaultCookieName,timeout=_defaultTimeout):
		"""Create a session object.

		Keyword arguments:
		rh -- the parent's request handler (usually self)
		name -- the cookie name (defaults to "gsid")
		timeout -- the number of seconds the session will last between
		           requests (defaults to 1800 secs - 30 minutes)
		"""
		self.rh=rh	# request handler
		self._timeout=timeout
		self._name=name
		self._new=True
		self._invalid=False
		dict.__init__(self)

		if name in rh.request.str_cookies:
			self._sid=rh.request.str_cookies[name]
			data=memcache.get(self._sid)
			if data!=None:
				self.update(data)
				# memcache timeout is absolute, so we need to reset it on each access
				memcache.set(self._sid,data,self._timeout)
				self._new=False
				return

		# Create a new session ID
		# There are about 10^14 combinations, so guessing won't work
		self._sid=random.choice(_sidChars)+random.choice(_sidChars)+\
							random.choice(_sidChars)+random.choice(_sidChars)+\
							random.choice(_sidChars)+random.choice(_sidChars)+\
							random.choice(_sidChars)+random.choice(_sidChars)
		# Added path so session works with any path
		rh.response.headers.add_header('Set-Cookie','%s=%s; path=/;'%(name,self._sid))

	#----------------------------------------------------------
	def save(self):
		"""Save session data."""
		if not self._invalid:
			memcache.set(self._sid,self.copy(),self._timeout)

	#----------------------------------------------------------
	def is_new(self):
		"""Returns True if session was created during this request."""
		return self._new

	#----------------------------------------------------------
	def get_id(self):
		"""Returns session id string."""
		return self._sid

	#----------------------------------------------------------
	def invalidate(self):
		"""Delete session data and cookie."""
		self.rh.response.headers.add_header('Set-Cookie',
				'%s=; expires=Sat, 1-Jan-2000 00:00:00 GMT;'%(self._name))
		memcache.delete(self._sid)
		self.clear()
		self._invalid=True
