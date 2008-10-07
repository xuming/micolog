import cgi, os,sys
import wsgiref.handlers
from google.appengine.ext.webapp import template, \
    WSGIApplication
from google.appengine.api import users
import app.webapp as webapp2
from google.appengine.ext import db
from base import *
from datetime import datetime ,timedelta
import base64,random
from django.utils import simplejson


def doRequestHandle(old_handler,new_handler,**args):
        new_handler.initialize(old_handler.request,old_handler.response)
        return  new_handler.get(**args)


class MainPage(BasePublicPage):

    def get(self,page=0):


        postid=self.param('p')
        if postid:
            try:
                postid=int(postid)
                return doRequestHandle(self,SinglePost(),postid=postid)  #singlepost.get(postid=postid)
            except:
                return self.error(404)
        self.doget(page)

    @cache()
    def doget(self,page):



        page=int(page)
       	max_page = (self.blog.entrycount - 1) / self.blog.posts_per_page


        if page < 0 or page > max_page:
				return	self.error(404)

        entries = Entry.all().filter('entrytype =','post').\
                filter("published =", True).order('-date').\
                fetch(self.blog.posts_per_page, offset = page * self.blog.posts_per_page)


        show_prev =entries and  (not (page == 0))
        show_next =entries and  ( not (page == max_page))

        logging.debug('this is ok')


        return self.render('index',{'entries':entries,
       	                'show_prev' : show_prev,
				        'show_next' : show_next,
				        'pageindex':page,
				        'ishome':True
                            })


class entriesByCategory(BasePublicPage):
    @cache()
    def get(self,slug=None):
        if not slug:
             self.error(404)
             return
        try:
            page_index=int (self.param('page'))
        except:
            page_index=1
        slug=urllib.unquote(slug).decode('utf8')
        cats=Category.all().filter('slug =',slug).fetch(1)
        if cats:
            entries=Entry.all().filter('categorie_keys =',cats[0].key())
            entries,links=Pager(query=entries).fetch(page_index)
            self.render('category',{'entries':entries,'category':cats[0],'pager':links})
        else:
            self.error(414,slug)

class entriesByTag(BasePublicPage):
    @cache()
    def get(self,slug=None):
        if not slug:
             self.error(404)
             return
        try:
            page_index=int (self.param('page'))
        except:
            page_index=1
        import urllib
        slug=urldecode(slug)

        entries=Entry.all().filter('tags =',slug)
        entries,links=Pager(query=entries).fetch(page_index)
        self.render('tag',{'entries':entries,'tag':slug,'pager':links})



class SinglePost(BasePublicPage):
    @cache()
    def get(self,slug=None,postid=None):

        if postid:
            entries = Entry.all().filter("published =", True).filter('post_id =', postid).fetch(1)
        else:
            slug=urldecode(slug)
            entries = Entry.all().filter("published =", True).filter('link =', slug).fetch(1)
        if not entries or len(entries) == 0:
            return self.error(404)

        entry=entries[0]
        comments=Comment.all().filter("entry =",entry)

        commentuser=self.request.cookies.get('commentuser', '')
        if commentuser:
            commentuser=base64.b64decode(commentuser).split('#@#')
        else:
            commentuser=['','','']


        if entry.entrytype=='post':
            self.render('single',
                        {
                        'entry':entry,
                        'comments':comments,
                        'user_name':commentuser[0],
                        'user_email':commentuser[1],
                        'user_url':commentuser[2],
                        'checknum1':random.randint(1,10),
                        'checknum2':random.randint(1,10),
                        })

        else:
            self.render('page',
                        {'entry':entry,
                        'comments':comments,
                        'user_name':commentuser[0],
                        'user_email':commentuser[1],
                        'user_url':commentuser[2],
                        'checknum1':random.randint(1,10),
                        'checknum2':random.randint(1,10),
                        })


class FeedHandler(BaseRequestHandler):
    @cache(time=600)
    def get(self,tags=None):
        entries = Entry.all().filter('entrytype =','post').order('-date').fetch(10)
        if entries and entries[0]:
            last_updated = entries[0].date
            last_updated = last_updated.strftime("%Y-%m-%dT%H:%M:%SZ")
        for e in entries:
            e.formatted_date = e.date.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.response.headers['Content-Type'] = 'application/atom+xml'
        self.render2('views/atom.xml',{'entries':entries,'last_updated':last_updated})

class Error404(BaseRequestHandler):
    @cache(36000)
    def get(self,slug=None):
         self.error(404)

class Post_comment(BaseRequestHandler):
    #@printinfo
    def post(self,slug=None):
        if self.is_admin:
            name=self.blog.author
            email=self.login_user.email()
            url=self.blog.baseurl
        else:
            name=self.param('author')
            email=self.param('email')
            url=self.param('url')

        if not self.is_login:
            checknum=self.param('checknum')
            checkret=self.param('checkret')
            try:
                import app.gbtools as gb
                if eval(checknum)<>int(gb.stringQ2B( checkret)):
                    self.error(-102,'Your check code is invalid .')
                    return
            except:
                self.error(-102,'Your check code is invalid .')
                return


        key=self.param('key')
        content=self.param('comment')
        if not (name and email and content):
            self.error(-101,'Please input name, email and comment .')
        else:
            comment=Comment(author=name,
                            content=content,
                            email=email,
                            entry=Entry.get(key))
            if url:
               try:
                    comment.weburl=url
               except:
                   comment.weburl='http://'+url

            info_str=base64.b64encode('#@#'.join([name.encode('utf8'),email.encode('utf8'),url.encode('utf8')]))

            self.response.headers.add_header( 'Set-Cookie',
            'commentuser=%s;expires=%s;domain=%s;path=/'
                %( info_str,
                   (datetime.now()+timedelta(days=100)).strftime("%a, %d-%b-%Y %H:%M:%S GMT"),
                   ''
                   )
            )

            comment.save()
            memcache.delete("/"+comment.entry.link)
            self.redirect(self.referer)

class ChangeTheme(BaseRequestHandler):
    @requires_admin
    def get(self,slug=None):
       theme=self.param('t')
       g_blog.theme_name=theme
       g_blog.get_theme()
       self.redirect('/')


class do_action(BaseRequestHandler):
    def get(self,slug=None):
        try:
            func=getattr(self,'action_'+slug)
            if func and callable(func):
                func()
            else:
                self.error(404)
        except:
             self.error(404)

    def post(self,slug=None):
        try:
            func=getattr(self,'action_'+slug)
            if func and callable(func):
                func()
            else:
                self.error(404)
        except:
             self.error(404)

    def action_info_login(self):
        if self.login_user:
            self.write(simplejson.dumps({'islogin':True,
                                         'isadmin':self.is_admin,
                                         'name': self.login_user.nickname()}))
        else:
            self.write(simplejson.dumps({'islogin':False}))

    def action_getcomments(self):
        key=self.param('key')
        entry=Entry.get(key)
        comments=Comment.all().filter("entry =",key)

        commentuser=self.request.cookies.get('commentuser', '')
        if commentuser:
            commentuser=base64.b64decode(commentuser).split('#@#')
        else:
            commentuser=['','','']


        vals={
            'entry':entry,
            'comments':comments,
            'user_name':commentuser[0],
            'user_email':commentuser[1],
            'user_url':commentuser[2],
            'checknum1':random.randint(1,10),
            'checknum2':random.randint(1,10),
            }
        html=self.get_render('comments',vals)

        self.write(simplejson.dumps(html.decode('utf8')))


class getMedia(webapp2.RequestHandler):
    def get(self,slug):
        media=Media.get(slug)
        if media:
            self.response.headers['Expires'] = 'Thu, 15 Apr 2010 20:00:00 GMT'
            self.response.headers['Cache-Control'] = 'max-age=3600,public'
            self.response.headers['Content-Type'] = str(media.mtype)
            self.response.out.write(media.bits)





def main():
    webapp.template.register_template_library('filter')
    application = webapp2.WSGIApplication2(
                    [('/media/(.*)',getMedia),
                     ('/skin',ChangeTheme),
                     ('/feed', FeedHandler),
                     ('/post_comment',Post_comment),
                     ('/page/(?P<page>\d+)', MainPage),
                     ('/category/(.*)',entriesByCategory),
                     ('/tag/(.*)',entriesByTag),
##                     ('/\?p=(?P<postid>\d+)',SinglePost),
                     ('/', MainPage),
                     ('/do/(\w+)', do_action),

                     ('/([\\w\\-\\./]+)', SinglePost),
                     ('.*',Error404),
                     ],debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
    main()