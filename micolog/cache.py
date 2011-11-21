#-------------------------------------------------------------------------------
# Name:        cache.py
# Purpose:
#
# Author:      Administrator
#
# Created:     23-01-2011
# Copyright:   (c) Administrator 2011
# Licence:     GPL
#-------------------------------------------------------------------------------
#!/usr/bin/env python
"""A simple cache warp for micolog

The main purpose of this module is to design a common layer to deal with all
methods which need been cached!
"""
ENABLE_MEMCACHE=True
def vcache(key="", time=3600):
    """
    Cache for normal method which return some object

    example::

        @vcache("blog.hotposts")
        def hotposts(self):
            return Entry.all().filter('entrytype =', 'post').filter("published =", True).order('-readtimes').fetch(8)

    args:
        key: keyname fo memcache
        time: relative number of seconds from current time.

    """
    def _decorate(method):
        def _wrapper(*args, **kwargs):
            if  not ENABLE_MEMCACHE:
                return method(*args, **kwargs)

            result = method(*args, **kwargs)
            memcache.set(key, result, time)
            return result

        return _wrapper
    return _decorate


def cache(key="",time=3600):
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
            from model import g_blog
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
                 logging.info('cache:'+skey)
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
                result=response.out.getvalue()
                status_code = response._Response__status[0]
                logging.debug("Cache:%s"%status_code)
                memcache.set(skey,(result,response.last_modified,status_code,response.headers),time)

        return _wrapper
    return _decorate