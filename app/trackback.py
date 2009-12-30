"""tblib.py: A Trackback (client) implementation in Python
"""
__author__ = "Matt Croydon <matt@ooiio.com>"
__copyright__ = "Copyright 2003, Matt Croydon"
__license__ = "GPL"
__version__ = "0.1.0"
__history__ = """
0.1.0: 1/29/03 - Code cleanup, release.  It can send pings, and autodiscover a URL to ping.
0.0.9: 1/29/03 - Basic error handling and autodiscovery works!
0.0.5: 1/29/03 - Internal development version.  Working on autodiscovery and error handling.
0.0.4: 1/22/03 - First public release, code cleanup.
0.0.3: 1/22/03 - Removed hard coding that was used for testing.
0.0.2: 1/21/03 - First working version.
0.0.1: 1/21/03 - Initial version.  Thanks to Mark Pilgrim for helping me figure some module basics out.
"""
import httplib, urllib, urlparse, re
from google.appengine.api import urlfetch
import logging
"""Everything I needed to know about trackback I learned from the trackback tech specs page
http://www.movabletype.org/docs/mttrackback.html.  All arguments are optional.  This allows us to create an empty TrackBack object,
then use autodiscovery to populate its attributes.
"""
class TrackBack:

    def __init__(self, tbUrl=None, title=None, excerpt=None, url=None, blog_name=None):
        self.tbUrl = tbUrl
        self.title = title
        self.excerpt = excerpt
        self.url = url
        self.blog_name = blog_name
        self.tbErrorCode = None
        self.tbErrorMessage = None

    def ping(self):

        # Only execute if a trackback url has been defined.
        if self.tbUrl:
            # Create paramaters and make them play nice with HTTP
            # Python's httplib example helps a lot:
            # http://python.org/doc/current/lib/httplib-examples.html
            params = urllib.urlencode({'title': self.title, 'url': self.url, 'excerpt': self.excerpt, 'blog_name': self.blog_name})
            headers = ({"Content-type": "application/x-www-form-urlencoded",
            "User-Agent": "micolog"})
            # urlparse is my hero
            # http://www.python.org/doc/current/lib/module-urlparse.html
            logging.info("ping...%s",params)
            response=urlfetch.fetch(self.tbUrl,method=urlfetch.POST,payload=params,headers=headers)

            self.httpResponse = response.status_code
            data = response.content
            self.tbResponse = data
            logging.info("ping...%s"%data)
            # Thanks to Steve Holden's book: _Python Web Programming_ (http://pydish.holdenweb.com/pwp/)
            # Why parse really simple XML when you can just use regular expressions?  Rawk.
            errorpattern = r'<error>(.*?)</error>'
            reg = re.search(errorpattern, self.tbResponse)
            if reg:
                self.tbErrorCode = reg.group(1)
                if int(self.tbErrorCode) == 1:
                    errorpattern2 = r'<message>(.*?)</message>'
                    reg2 = re.search(errorpattern2, self.tbResponse)
                    if reg2:
                        self.tbErrorMessage = reg2.group(1)

        else:
            return 1

    def autodiscover(self, urlToCheck):

        response=urlfetch.fetch(urlToCheck)
        data = response.read()
        tbpattern = r'trackback:ping="(.*?)"'
        reg = re.search(tbpattern, data)
        if reg:
            self.tbUrl = reg.group(1)