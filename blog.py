# -*- coding: utf-8 -*-
import cgi, os,sys,math
import wsgiref.handlers
##os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
##from django.utils.translation import  activate


# Google App Engine imports.
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template, \
    WSGIApplication
from google.appengine.api import users
##import app.webapp as webapp2
from google.appengine.ext import db
# Force Django to reload its settings.

##from django.conf import settings
##settings._target = None
from base import *
##activate(g_blog.language)
from datetime import datetime ,timedelta
import base64,random
from django.utils import simplejson
import filter  as myfilter

##settings.configure(LANGUAGE_CODE = 'zh-cn')
# Must set this env var before importing any part of Django

def doRequestHandle(old_handler,new_handler,**args):
        new_handler.initialize(old_handler.request,old_handler.response)
        return  new_handler.get(**args)


class MainPage(BasePublicPage):

    def get(self,page=1):


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
        entrycount=g_blog.postscount()
       	max_page = entrycount / g_blog.posts_per_page + ( entrycount % g_blog.posts_per_page and 1 or 0 )


        if page < 1 or page > max_page:
				return	self.error(404)

        entries = Entry.all().filter('entrytype =','post').\
                filter("published =", True).order('-date').\
                fetch(self.blog.posts_per_page, offset = (page-1) * self.blog.posts_per_page)


        show_prev =entries and  (not (page == 1))
        show_next =entries and  (not (page == max_page))
        #print page,max_page,g_blog.entrycount,self.blog.posts_per_page


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
            entries=Entry.all().filter("published =", True).filter('categorie_keys =',cats[0].key()).order("-date")
            entries,links=Pager(query=entries).fetch(page_index)
            self.render('category',{'entries':entries,'category':cats[0],'pager':links})
        else:
            self.error(414,slug)

class archive_by_month(BasePublicPage):
    @cache()
    def get(self,year,month):
        try:
            page_index=int (self.param('page'))
        except:
            page_index=1

        firstday=datetime(int(year),int(month),1)
        if int(month)!=12:
            lastday=datetime(int(year),int(month)+1,1)
        else:
            lastday=datetime(int(year)+1,1,1)
        entries=db.GqlQuery("SELECT * FROM Entry WHERE date > :1 AND date <:2 AND entrytype =:3 AND published = True ORDER BY date DESC",firstday,lastday,'post')
        entries,links=Pager(query=entries).fetch(page_index)

        self.render('month',{'entries':entries,'year':year,'month':month,'pager':links})

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

        entries=Entry.all().filter("published =", True).filter('tags =',slug).order("-date")
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

        mp=self.paramint("mp",1)

        entry=entries[0]
        entry.readtimes += 1
        entry.put()
        self.entry=entry


        comments=entry.get_comments_by_page(mp,self.blog.comments_per_page)


##        commentuser=self.request.cookies.get('comment_user', '')
##        if commentuser:
##            commentuser=commentuser.split('#@#')
##        else:
        commentuser=['','','']

        comments_nav=self.get_comments_nav(mp,entry.comments().count())


        if entry.entrytype=='post':
            self.render('single',
                        {
                        'entry':entry,
                        'relateposts':entry.relateposts,
                        'comments':comments,
                        'user_name':commentuser[0],
                        'user_email':commentuser[1],
                        'user_url':commentuser[2],
                        'checknum1':random.randint(1,10),
                        'checknum2':random.randint(1,10),
                        'comments_nav':comments_nav,
                        })

        else:
            self.render('page',
                        {'entry':entry,
                        'relateposts':entry.relateposts,
                        'comments':comments,
                        'user_name':commentuser[0],
                        'user_email':commentuser[1],
                        'user_url':commentuser[2],
                        'checknum1':random.randint(1,10),
                        'checknum2':random.randint(1,10),
                        'comments_nav':comments_nav,
                        })

    def get_comments_nav(self,pindex,count):

        maxpage=count / g_blog.comments_per_page + ( count % g_blog.comments_per_page and 1 or 0 )
        if maxpage==1:
            return ""

        result=""

        if pindex>1:
            result="<a class='comment_prev' href='"+self.get_comments_pagenum_link(pindex-1)+"'>«</a>"

        minr=max(pindex-3,1)
        maxr=min(pindex+3,maxpage)
        if minr>2:
            result+="<a class='comment_num' href='"+self.get_comments_pagenum_link(1)+"'>1</a>"
            result+="<span class='comment_dot' >...</span>"

        for  n in range(minr,maxr+1):
            if n==pindex:
                result+="<span class='comment_current'>"+str(n)+"</span>"
            else:
                result+="<a class='comment_num' href='"+self.get_comments_pagenum_link(n)+"'>"+str(n)+"</a>"
        if maxr<maxpage-1:
            result+="<span class='comment_dot' >...</span>"
            result+="<a class='comment_num' href='"+self.get_comments_pagenum_link(maxpage)+"'>"+str(maxpage)+"</a>"

        if pindex<maxpage:
            result+="<a class='comment_next' href='"+self.get_comments_pagenum_link(pindex+1)+"'>»</a>"

        return {'nav':result,'current':pindex,'maxpage':maxpage}

    def get_comments_pagenum_link(self,pindex):
        url=str(self.entry.link)
        if url.find('?')>=0:
            return "/"+url+"&mp="+str(pindex)+"#comments"
        else:
            return "/"+url+"?mp="+str(pindex)+"#comments"

class FeedHandler(BaseRequestHandler):
    @cache(time=600)
    def get(self,tags=None):
        entries = Entry.all().filter('entrytype =','post').filter('published =',True).order('-date').fetch(10)
        if entries and entries[0]:
            last_updated = entries[0].date
            last_updated = last_updated.strftime("%Y-%m-%dT%H:%M:%SZ")
        for e in entries:
            e.formatted_date = e.date.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.response.headers['Content-Type'] = 'application/atom+xml'
        self.render2('views/atom.xml',{'entries':entries,'last_updated':last_updated})

class CommentsFeedHandler(BaseRequestHandler):
    @cache(time=600)
    def get(self,tags=None):
        comments = Comment.all().order('-date').fetch(10)
        if comments and comments[0]:
            last_updated = comments[0].date
            last_updated = last_updated.strftime("%Y-%m-%dT%H:%M:%SZ")
        for e in comments:
            e.formatted_date = e.date.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.response.headers['Content-Type'] = 'application/atom+xml'
        self.render2('views/comments.xml',{'comments':comments,'last_updated':last_updated})

class SitemapHandler(BaseRequestHandler):
    @cache(time=36000)
    def get(self,tags=None):
        urls = []
        def addurl(loc,lastmod=None,changefreq=None,priority=None):
            url_info = {
                'location':   loc,
                'lastmod':    lastmod,
                'changefreq': changefreq,
                'priority':   priority
            }
            urls.append(url_info)

        addurl(g_blog.baseurl,changefreq='daily',priority=0.9 )

        entries = Entry.all().filter('published =',True).order('-date').fetch(g_blog.sitemap_entries)

        for item in entries:
            loc = "%s/%s" % (g_blog.baseurl, item.link)
            addurl(loc,item.date,'never',0.6)

        if g_blog.sitemap_include_category:
            cats=Category.all()
            for cat in cats:
                loc="%s/category/%s"%(g_blog.baseurl,cat.slug)
                addurl(loc,None,'weekly',0.5)

        if g_blog.sitemap_include_tag:
            tags=Tag.all()
            for tag in tags:
                loc="%s/tag/%s"%(g_blog.baseurl, urlencode(tag.tag))
                addurl(loc,None,'weekly',0.5)


##        self.response.headers['Content-Type'] = 'application/atom+xml'
        self.render2('views/sitemap.xml',{'urlset':urls})



class Error404(BaseRequestHandler):
    @cache(time=36000)
    def get(self,slug=None):
         self.error(404)

class Post_comment(BaseRequestHandler):
    #@printinfo
    def post(self,slug=None):
        useajax=self.param('useajax')=='1'
##        if self.is_admin:
##            name=self.blog.author
##            email=self.login_user.email()
##            url=self.blog.baseurl
##        else:
        name=self.param('author')
        email=self.param('email')
        url=self.param('url')

        key=self.param('key')
        content=self.param('comment')
        checknum=self.param('checknum')
        checkret=self.param('checkret')
##        if useajax:
##            name=urldecode(name)
##            email=urldecode(email)
##            url=urldecode(url)
##            key=urldecode(key)
##            content=urldecode(content)
##            checknum=urldecode(checknum)
##            checkret=urldecode(checkret)

        if not self.is_login:
            if not (self.request.cookies.get('comment_user', '')):

                try:
                    import app.gbtools as gb
                    if eval(checknum)<>int(gb.stringQ2B( checkret)):
                        if useajax:
                            self.write(simplejson.dumps((False,-102,_('Your check code is invalid .'))))
                        else:
                            self.error(-102,_('Your check code is invalid .'))
                        return
                except:
                    if useajax:
                        self.write(simplejson.dumps((False,-102,_('Your check code is invalid .'))))
                    else:
                        self.error(-102,_('Your check code is invalid .'))
                    return



        content=content.replace('\n','<br>')
        content=myfilter.do_filter(content)
        name=cgi.escape(name)[:20]
        url=cgi.escape(url)[:100]

        if not (name and email and content):
            if useajax:
                        self.write(simplejson.dumps((False,-101,_('Please input name, email and comment .'))))
            else:
                self.error(-101,_('Please input name, email and comment .'))
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

            #name=name.decode('utf8').encode('gb2312')


            info_str='#@#'.join([urlencode(name),urlencode(email),urlencode(url)])

            logging.info("info:"+info_str)
             #info_str='#@#'.join([name,email,url.encode('utf8')])
            cookiestr='comment_user=%s;expires=%s;domain=%s;path=/'%( info_str,
                       (datetime.now()+timedelta(days=100)).strftime("%a, %d-%b-%Y %H:%M:%S GMT"),
                       ''
                       )
            comment.save()
            memcache.delete("/"+comment.entry.link)

            self.response.headers.add_header( 'Set-Cookie', cookiestr)
            if useajax:
                comment_c=self.get_render('comment',{'comment':comment})
                self.write(simplejson.dumps((True,comment_c.decode('utf8'))))
            else:
                self.redirect(self.referer+"#comment-"+str(comment.key().id()))

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
        except BaseException,e:
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

        commentuser=self.request.cookies.get('comment_user', '')
        if commentuser:
            commentuser=commentuser.split('#@#')
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

    def action_test(self):
        self.write(settings.LANGUAGE_CODE)
        self.write(_("this is a test"))


class getMedia(webapp.RequestHandler):
    def get(self,slug):
        media=Media.get(slug)
        if media:
            self.response.headers['Expires'] = 'Thu, 15 Apr 2010 20:00:00 GMT'
            self.response.headers['Cache-Control'] = 'max-age=3600,public'
            self.response.headers['Content-Type'] = str(media.mtype)
            self.response.out.write(media.bits)

#Thanks for cxu
#Author web:http://cxu.yimudi.org
class TrackBackHandler(webapp.RequestHandler):
    error = '''
<?xml version="1.0" encoding="utf-8"?>
<response>
<error>1</error>
<message>%s</message>
</response>
'''
    success = '''
<?xml version="1.0" encoding="utf-8"?>
<response>
<error>0</error>
</response>
'''

    def post(self, slug=None):
        self.response.headers['Content-Type'] = "text/xml"
        if not slug:
            postid = self.request.get('p')
            try:
                postid = int(postid)
            except:
                postid = None
            if not postid:
                self.response.out.write(self.error % "empty slug/postid")
                return

        coming_url = self.request.get('url')
        blog_name = myfilter.do_filter(self.request.get('blog_name'))
        excerpt = myfilter.do_filter(self.request.get('excerpt'))
        title = myfilter.do_filter(self.request.get('title'))

        if not coming_url or not blog_name or not excerpt or not title:
            self.response.out.write(self.error % "not enough post info")
            return

        import time
        #wait for half second in case otherside hasn't been published
        time.sleep(0.5)

        #also checking the coming url is valid and contains our link
        #this is not standard trackback behavior
        try:
            result = urlfetch.fetch(coming_url)
            if result.status_code != 200 or ((g_blog.baseurl + '/' + slug)
                    not in result.content.decode('ascii','ignore')):
                self.response.out.write(self.error % "probably spam")
                return
        except Exception, e:
            logging.info(e)
            self.response.out.write(self.error % "urlfetch error")
            return

        if slug:
            slug = urldecode(slug)
            entry = Entry.all().filter("published =", True).filter('link =', slug).get()
        else:
            entry = Entry.all().filter("published =", True).filter('post_id =', postid).get()
        if not entry:
            self.response.out.write(self.error % "no target post")
            return

        comment = Comment.all().filter("entry =", entry).filter("weburl =", coming_url).get()
        if comment:
            self.response.out.write(self.error % "has pinged before")
            return

        comment=Comment(author=blog_name,
                content="<strong>"+title[:250]+"...</strong><br/>" +
                        excerpt[:250] + '...',
                weburl=coming_url,
                entry=entry)
        comment.save()
        memcache.delete("/"+entry.link)
        self.response.out.write(self.success)


def main():
    webapp.template.register_template_library('filter')
    application = webapp.WSGIApplication(
                    [('/media/(.*)',getMedia),
                    ('/skin',ChangeTheme),
                    ('/feed', FeedHandler),
                    ('/feed/comments',CommentsFeedHandler),
                    ('/sitemap', SitemapHandler),
                    ('/post_comment',Post_comment),
                    ('/page/(?P<page>\d+)', MainPage),
                    ('/category/(.*)',entriesByCategory),
                    ('/(\d{4})/(\d{2})',archive_by_month),
                    ('/tag/(.*)',entriesByTag),
##                    ('/\?p=(?P<postid>\d+)',SinglePost),
                    ('/', MainPage),
                    ('/do/(\w+)', do_action),

                    ('/([\\w\\-\\./]+)', SinglePost),
                    ('.*',Error404),
                    ],debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
    main()