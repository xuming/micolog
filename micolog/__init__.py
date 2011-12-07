import webapp2
import blog
import settings
micolog_app = webapp2.WSGIApplication([('/', blog.MainPage)],debug=True)
