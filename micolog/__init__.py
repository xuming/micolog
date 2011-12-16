import settings
from google.appengine.ext.webapp import template
import webapp2
import blog,theme


template.register_template_library('micolog.filter')
micolog_app = webapp2.WSGIApplication(
            [
                ('/', blog.MainPage),
                ('/themes/[\\w\\-]+/templates/.*',theme.NotFound),
                ('/themes/(?P<prefix>[\\w\\-]+)/(?P<name>.+)', theme.GetFile),
            ],debug=True)


