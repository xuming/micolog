#-------------------------------------------------------------------------------
# Name:        cache.py
# Purpose:
#
# Author:      xuming
#
# Created:     23-01-2011
# Copyright:   (c) xuming 2011
# Licence:     GPL
#-------------------------------------------------------------------------------
#!/usr/bin/env python
"""A simple cache warp for micolog

The main purpose of this module is to design a common layer to deal with all
methods which need been cached!
"""
from google.appengine.api import memcache
from utils import format_date
from datetime import datetime
from  settings import ENABLE_MEMCACHE
def vcache(key="", time=0,args=()):
    """
    Cache for normal method which return some object

    example::

        @vcache("blog.hotposts",args=('count'))
        def hotposts(self,count=8):
            return Entry.all().filter('entrytype =', 'post').filter("published =", True).order('-readtimes').fetch(count)

    args:
        key: keyname fo memcache
        args: the list of cached args
        time: relative number of seconds from current time.


    """
    def _decorate(method):
        def _wrapper(*cargs, **kwargs):
            if  not ENABLE_MEMCACHE:
                return method(*cargs, **kwargs)
            skey=key
            if hasattr(cargs[0],"vkey"):
                skey=key+cargs[0].vkey

            for arg in args:
                if kwargs.has_key(arg):
                    skey+="_"+str(arg)+"_"+str(kwargs[arg])
            result=memcache.get(skey)
            if result==None:
                result = method(*cargs, **kwargs)
                memcache.set(skey, result, time)
            return result

        return _wrapper
    return _decorate


def cache(key="",time=0):
    """
    Cache for request handler method, such as: get or post.
    It will cache the web page.

    example::

        @cache(time=600)
        def get(self,tags=None):

    args:
        key: optional key name. Request. path_qs as default.
        time: relative number of seconds from current time.
    """

    def _decorate(method):
        def _wrapper(*args, **kwargs):

            if not ENABLE_MEMCACHE:
                method(*args, **kwargs)
                return

            request=args[0].request
            response=args[0].response
            skey=key+ request.path_qs
            #logging.info('skey:'+skey)
            html= memcache.get(skey)
            #arg[0] is BaseRequestHandler object

            if html:
                 #logging.info('cache:'+skey)
                 response.last_modified =html[1]
                 ilen=len(html)
                 if ilen>=3:
                    response.set_status(html[2])
                 if ilen>=4:
                    for skey,value in html[3].items():
                        response.headers[skey]=value
                 response.out.write(html[0])
            else:
                if 'last-modified' not in response.headers:
                    response.last_modified = format_date(datetime.utcnow())
                method(*args, **kwargs)
                result=response.body
                status_code = response.status_int
                memcache.set(skey,(result,response.last_modified,status_code,response.headers),time)

        return _wrapper
    return _decorate