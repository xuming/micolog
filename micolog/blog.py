# -*- coding: utf-8 -*-
import cgi, os,logging

import wsgiref.handlers

# Google App Engine imports.
##import app.webapp as webapp2

from datetime import timedelta
import random
from django.utils import simplejson
from google.appengine.api import users
from app.safecode import Image
from app.gmemsess import Session
from base import *
from utils import *
from model import *
from django.utils.translation import ugettext as _

##os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
##from django.utils.translation import  activate
##from django.conf import settings
##settings._target = None
##activate(self.blog.language)
from google.appengine.ext import zipserve
from google.appengine.datastore import datastore_query
import utils,filter

def doRequestHandle(old_handler,new_handler,**args):
        new_handler.initialize(old_handler.request,old_handler.response)
        return  new_handler.get(**args)

def doRequestPostHandle(old_handler,new_handler,**args):
        new_handler.initialize(old_handler.request,old_handler.response)
        return  new_handler.post(**args)


class BasePublicPage(BaseRequestHandler):
    def initialize(self, request, response):
        BaseRequestHandler.initialize(self,request, response)

    def m_list_pages(self):
        menu_pages=None
        entry=None
        menu_pages=self.blog.menu_pages()

        if self.template_vals.has_key('entry'):
            entry=self.template_vals['entry']
        ret=''
        current=''
        for page in menu_pages:
            if entry and entry.entrytype=='page' and entry.key==page.key:
                current= 'current_page_item'
            else:
                current= 'page_item'
            #page is external page ,and page.slug is none.
            if page.is_external_page and not page.slug:
                ret+='<li class="%s"><a href="%s" target="%s" >%s</a></li>'%( current,page.link,page.target, page.title)
            else:
                ret+='<li class="%s"><a href="/%s" target="%s">%s</a></li>'%( current,page.link, page.target,page.title)
        return ret



class MainPage(BasePublicPage):
    def head(self,page=1):
        pass


    @request_memcache(key_prefix='HomePage', is_entry=True)
    def get(self):

        try:
            sPrev=self.param('prev')
            sNext=self.param('next')
        except:
            sPrev=''
            sNext=''


        orders= datastore_query.CompositeOrder([-Entry.sticky,-Entry.date])
        entries = Entry.query().filter(Entry.entrytype=='post',Entry.published==True)

        entries,links=Pager(query=entries,items_per_page=self.blog.posts_per_page).fetch_cursor(sNext,sPrev,orders)

        return self.render('index',
            dict(entries=entries, pager=links))

class OtherHandler(BasePublicPage):
    def  get(self,slug=None,postid=None):
        pass

##def getSinglePostHtml(req=None,entry=None):
##    if not (req and entry):
##        return ""
##
##    mp=req.paramint("mp",1)
##
##    if entry.is_external_page:
##        return self.redirect(entry.external_page_address,True)
##
##    self.entry=entry
##
##
##    comments=entry.get_comments_by_page(mp,self.blog.comments_per_page)
####
##    commentuser=['','','']
####
##    comments_nav=self.get_comments_nav(mp,entry.commentcount)
##
##    if entry.entrytype=='post':
##        self.render('single',
##                    dict(entry=entry,comments=comments,comments_nav=comments_nav))
##
##    else:
##        self.render('page',
##                    dict(entry=entry,comments=comments,comments_nav=comments_nav))

class SinglePost(BasePublicPage):
    #def head(self,slug=None,postid=None):
    #    pass

    #@request_memcache(key_prefix='single_post')
    def get(self,slug=None,postid=None):

        entries=[]
        if postid:
            entry=Entry.get_by_id(long(postid))
            if entry and entry.published:
                entries=[entry]

        else:
            #slug=utils.urldecode(self.request.path[1:])
            entries = Entry.query().filter(Entry.published == True).filter(Entry.link == slug).fetch(1)
        if not entries or len(entries) == 0:
            return self.error(404)



        entry=entries[0]
        if entry.is_external_page:
            return self.redirect(entry.external_page_address,True)

##        if self.blog.allow_pingback and entry.allow_trackback:
##            self.response.headers['X-Pingback']="%s/rpc"%str(self.blog.baseurl)
        #不再统计阅读数
        #entry.readtimes += 1
        #entry.put()
        self.entry=entry

        #@request_memcache(key_prefix='single_post',entry_id=entry.vkey)
        def render_single(self):
            loginurl=users.create_login_url(entry.fullurl+(self.isPhone() and "" or "#comment_area"))
            if entry.entrytype=='post':
                self.render('single',
                            dict(entry=entry,loginurl=loginurl))

            else:
                self.render('page',
                            dict(entry=entry,loginurl=loginurl))
        render_single(self)


##    def post(self,slug=None,postid=None):
##        '''handle trackback'''
##        error = '''<?xml version="1.0" encoding="utf-8"?>
##<response>
##<error>1</error>
##<message>%s</message>
##</response>
##'''
##        success = '''<?xml version="1.0" encoding="utf-8"?>
##<response>
##<error>0</error>
##</response>
##'''
##
##        if not self.blog.allow_trackback:
##            self.response.out.write(error % "Trackback denied.")
##            return
##        self.response.headers['Content-Type'] = "text/xml"
##        if postid:
##            entries = Entry.all().filter("published =", True).filter('post_id =', postid).fetch(1)
##        else:
##            slug=urldecode(slug)
##            entries = Entry.all().filter("published =", True).filter('link =', slug).fetch(1)
##
##        if not entries or len(entries) == 0 :#or  (postid and not entries[0].link.endswith(self.blog.default_link_format%{'post_id':postid})):
##            self.response.out.write(error % "empty slug/postid")
##            return
##        #check code ,rejest spam
##        entry=entries[0]
##        logging.info(self.request.remote_addr+self.request.path+" "+entry.trackbackurl)
##        #key=self.param("code")
##        #if (self.request.uri!=entry.trackbackurl) or entry.is_external_page or not entry.allow_trackback:
##        #import cgi
##        from urlparse import urlparse
##        param=urlparse(self.request.uri)
##        code=param[4]
##        param=cgi.parse_qs(code)
##        if param.has_key('code'):
##            code=param['code'][0]
##
##        if  (not str(entry.key())==code) or entry.is_external_page or not entry.allow_trackback:
##            self.response.out.write(error % "Invalid trackback url.")
##            return
##
##
##        coming_url = self.param('url')
##        blog_name = myfilter.do_filter(self.param('blog_name'))
##        excerpt = myfilter.do_filter(self.param('excerpt'))
##        title = myfilter.do_filter(self.param('title'))
##
##        if not coming_url or not blog_name or not excerpt or not title:
##            self.response.out.write(error % "not enough post info")
##            return
##
##        import time
##        #wait for half second in case otherside hasn't been published
##        time.sleep(0.5)
##
####		#also checking the coming url is valid and contains our link
####		#this is not standard trackback behavior
####		try:
####
####			result = urlfetch.fetch(coming_url)
####			if result.status_code != 200 :
####				#or ((self.blog.baseurl + '/' + slug) not in result.content.decode('ascii','ignore')):
####				self.response.out.write(error % "probably spam")
####				return
####		except Exception, e:
####			logging.info("urlfetch error")
####			self.response.out.write(error % "urlfetch error")
####			return
##
##        comment = Comment.all().filter("entry =", entry).filter("weburl =", coming_url).get()
##        if comment:
##            self.response.out.write(error % "has pinged before")
##            return
##
##        comment=Comment(author=blog_name,
##                content="...<strong>"+title[:250]+"</strong> " +
##                        excerpt[:250] + '...',
##                weburl=coming_url,
##                entry=entry)
##
##        comment.ip=self.request.remote_addr
##        comment.ctype=COMMENT_TRACKBACK
##        try:
##            comment.save()
##
##            memcache.delete("/"+entry.link)
##            self.write(success)
##            self.blog.tigger_action("pingback_post",comment)
##        except:
##            self.response.out.write(error % "unknow error")

    def get_comments_nav(self,pindex,count):
        maxpage=count / self.blog.comments_per_page + ( count % self.blog.comments_per_page and 1 or 0 )
        if maxpage==1:
            return {'nav':"",'current':pindex}

        result=""

        if pindex>1:
            result="<a class='comment_prev' href='"+self.get_comments_pagenum_link(pindex-1)+"'>«</a>"

        minr=max(pindex-3,1)
        maxr=min(pindex+3,maxpage)
        if minr>2:
            result+="<a class='comment_num' href='"+self.get_comments_pagenum_link(1)+"'>1</a>"
            result+="<span class='comment_dot' >...</span>"

        for n in range(minr,maxr+1):
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

class entriesByCategory(BasePublicPage):
    @request_memcache(key_prefix='entriesByCategory',is_entry=True,time=3600*24)
    def get(self,slug=None):
        if not slug:
            self.error(404)
            return

        try:
            sPrev=self.param('prev')
            sNext=self.param('next')
        except:
            sPrev=''
            sNext=''


        slug=urldecode(slug)

        cats=Category.query().filter(Category.slug ==slug).fetch(1)
        if cats:

            entries=Entry.query().filter(Entry.published == True).filter(Entry.categorie_keys ==cats[0].key)


            #entries, cursor,more = q.fetch_page(20)
            entries,links=Pager(query=entries,items_per_page=20).fetch_cursor(sNext,sPrev,-Entry.date)
            self.render('category', dict(entries=entries, category=cats[0], pager=links))
        else:
            self.error(404,slug)

class archive_by_month(BasePublicPage):
    @request_memcache(key_prefix='archive',time=3600*24*3)
    def get(self,year,month):
        try:
            sPrev=self.param('prev')
            sNext=self.param('next')
        except:
            sPrev=''
            sNext=''

        firstday=datetime(int(year),int(month),1)
        if int(month)!=12:
            lastday=datetime(int(year),int(month)+1,1)
        else:
            lastday=datetime(int(year)+1,1,1)
        entries=Entry.query().filter(Entry.date>firstday,Entry.date<lastday,Entry.entrytype=='post')
        #entries=db.GqlQuery("SELECT * FROM Entry WHERE date > :1 AND date <:2 AND entrytype =:3 AND published = True ORDER BY date DESC",firstday,lastday,'post')
        entries,links=Pager(query=entries).fetch_cursor(sNext,sPrev,-Entry.date)

        self.render('month', dict(entries=entries, year=year, month=month, pager=links))

class entriesByTag(BasePublicPage):
    @request_memcache(key_prefix='tag',is_entry=True,time=3600*24)
    def get(self,slug=None):
        if not slug:
             self.error(404)
             return
        try:
            sPrev=self.param('prev')
            sNext=self.param('next')
        except:
            sPrev=''
            sNext=''
        slug=urldecode(slug)

        entries=Entry.query().filter(Entry.published == True).filter(Entry.tags ==slug)
        entries,links=Pager(query=entries,items_per_page=20).fetch_cursor(sNext,sPrev,-Entry.date)
        self.render('tag',{'entries':entries,'tag':slug,'pager':links})



class FeedHandler(BaseRequestHandler):
    @request_cache(key_prefix='feed',is_entry=True)
    def get(self,tags=None):
        entries = Entry.query().filter(Entry.entrytype =='post').filter(Entry.published ==True).order(-Entry.date).fetch(10)
        if entries and entries[0]:
            last_updated = entries[0].date
            last_updated = last_updated.strftime("%a, %d %b %Y %H:%M:%S +0000")
        for e in entries:
            e.formatted_date = e.date.strftime("%a, %d %b %Y %H:%M:%S +0000")
        self.response.headers['Content-Type'] = 'application/rss+xml; charset=utf-8'
        self.render2('views/rss.xml',{'entries':entries,'last_updated':last_updated})

class CommentsFeedHandler(BaseRequestHandler):
    @request_cache(key_prefix='commentsfeedhandler',time=3600*24,is_comment=True)
    def get(self,tags=None):
        comments = Comment.query().order(-Comment.date).filter(Comment.ctype ==0).fetch(10)
        if comments and comments[0]:
            last_updated = comments[0].date
            last_updated = last_updated.strftime("%a, %d %b %Y %H:%M:%S +0000")
        for e in comments:
            e.formatted_date = e.date.strftime("%a, %d %b %Y %H:%M:%S +0000")
        self.response.headers['Content-Type'] = 'application/rss+xml; charset=UTF-8'
        self.render2('views/comments.xml',{'comments':comments,'last_updated':last_updated})

class SitemapHandler(BaseRequestHandler):
    @request_cache(key_prefix='sitemap',is_entry=True,is_page=True)
    def get(self,tags=None):
        urls = []
        def addurl(loc,lastmod=None,changefreq=None,priority=None):
            url_info = {
                'location':   loc,
                'lastmod':	lastmod,
                'changefreq': changefreq,
                'priority':   priority
            }
            urls.append(url_info)

        addurl(self.blog.baseurl,changefreq='daily',priority=0.9 )

        entries = Entry.query().filter(Entry.published ==True).order(-Entry.date).fetch(self.blog.sitemap_entries)

        for item in entries:
            loc = "%s/%s" % (self.blog.baseurl, item.link)
            addurl(loc,item.mod_date or item.date,'never',0.6)

        if self.blog.sitemap_include_category:
            cats=Category.query()
            for cat in cats:
                loc="%s/category/%s"%(self.blog.baseurl,cat.slug)
                addurl(loc,None,'weekly',0.5)

        if self.blog.sitemap_include_tag:
            tags=Tag.query()
            for tag in tags:
                loc="%s/tag/%s"%(self.blog.baseurl, urlencode(tag.tag))
                addurl(loc,None,'weekly',0.5)


##		self.response.headers['Content-Type'] = 'application/atom+xml'
        self.render2('views/sitemap.xml',{'urlset':urls})


class Error404(BaseRequestHandler):
    @request_cache(key_prefix='error404')
    def get(self,slug=None):
        self.error(404)

class Post_comment(BaseRequestHandler):
    #@printinfo
    def post(self,slug=None):
        useajax=self.param('useajax')=='1'
        ismobile=self.paramint('ismobile')==1
        if not self.is_login:
            if useajax:
                    self.write(simplejson.dumps((False,-102,_('You must login before comment.')),ensure_ascii = False))
            else:
                    self.error(-102,_('You must login before comment .'))
            return


        name=self.login_user.nickname()
        email=self.login_user.email()
        url=self.param('url')

        key=self.param('key')
        content=self.param('comment')
        parent_id=self.paramint('parentid',0)
        reply_notify_mail=self.parambool('reply_notify_mail')

        content=content.replace('\n','<br />')
        content=filter.do_filter(content)
        name=cgi.escape(name)[:20]
        url=cgi.escape(url)[:100]

        if not (name and email and content):
            if useajax:
                        self.write(simplejson.dumps((False,-101,_('Please input comment .'))))
            else:
                self.error(-101,_('Please input comment .'))
        else:
            comment=Comment(author=name,
                            content=content,
                            email=email,
                            reply_notify_mail=reply_notify_mail,
                            entry=ndb.Key(Entry,int(key)))
            if url:
                try:
                    if not url.lower().startswith(('http://','https://')):
                        url = 'http://' + url
                    comment.weburl=url
                except:
                    comment.weburl=None


            comment.ip=self.request.remote_addr

            if parent_id:
                comment.parent=Comment.get_by_id(parent_id)

            #comment.no=comment.entry.commentcount+1
            try:
                comment.save()
                #memcache.delete("/"+comment.entry.link)

                #self.response.headers.add_header( 'Set-Cookie', cookiestr)
                if useajax:
                    if ismobile:
                        self.write(simplejson.dumps((True,'')))
                    else:
                        comment_c=self.get_render('comment',{'comment':comment})
                        self.write(simplejson.dumps((True,comment_c.decode('utf8')),ensure_ascii = False))
                else:
                    self.redirect(self.referer+"#comment-"+str(comment.key().id()))

                #comment.entry.removecache()
                #memcache.delete("/feed/comments")
            except Exception,e:
                if useajax:
                    self.write(simplejson.dumps((False,-103,_('Comment not allowed.')+unicode(e))))
                else:
                    self.error(-102,_('Comment not allowed .'+str(e)))

##class Post_comment(BaseRequestHandler):
##    #@printinfo
##    def post(self,slug=None):
##        useajax=self.param('useajax')=='1'
##        if not self.blog.allow_guest_comment:
##            if not self.is_login:
##                if useajax:
##                        self.write(simplejson.dumps((False,-102,_('You must login before comment.')),ensure_ascii = False))
##                else:
##                        self.error(-102,_('You must login before comment .'))
##                return
##
##
##
##
##        name=self.param('author')
##        email=self.param('email')
##        url=self.param('url')
##
##        key=self.param('key')
##        content=self.param('comment')
##        parent_id=self.paramint('parentid',0)
##        reply_notify_mail=self.parambool('reply_notify_mail')
##
##
##        if not self.is_login:
##            sess=Session(self,timeout=180)
##            #if not (self.request.cookies.get('comment_user', '')):
##            try:
##                check_ret=True
##                if self.blog.comment_check_type==1:
##                    checkret=self.param('checkret')
##                    check_ret=(int(checkret) == sess['code'])
##                elif self.blog.comment_check_type==2:
##                    checkret=self.param('checkret')
##
##                    check_ret=(int(checkret) == sess['icode'])
##
##                elif  self.blog.comment_check_type ==3:
##                    import app.gbtools as gb
##                    checknum=self.param('checknum')
##                    checkret=self.param('checkret')
##                    check_ret=eval(checknum)==int(gb.stringQ2B( checkret))
##
##                if not check_ret:
##                    if useajax:
##                        self.write(simplejson.dumps((False,-102,_('Your check code is invalid .')),ensure_ascii = False))
##                    else:
##                        self.error(-102,_('Your check code is invalid .'))
##                    return
##            except Exception,e:
##                if useajax:
##                    self.write(simplejson.dumps((False,-102,_('Your check code is invalid .')+unicode(e)),ensure_ascii = False))
##                else:
##                    self.error(-102,_('Your check code is invalid .'))
##                return
##
##            sess.invalidate()
##        content=content.replace('\n','<br />')
##        content=filter.do_filter(content)
##        name=cgi.escape(name)[:20]
##        url=cgi.escape(url)[:100]
##
##        if not (name and email and content):
##            if useajax:
##                        self.write(simplejson.dumps((False,-101,_('Please input name, email and comment .'))))
##            else:
##                self.error(-101,_('Please input name, email and comment .'))
##        else:
##            comment=Comment(author=name,
##                            content=content,
##                            email=email,
##                            reply_notify_mail=reply_notify_mail,
##                            entry=ndb.Key(Entry,int(key)))
##            if url:
##                try:
##                    if not url.lower().startswith(('http://','https://')):
##                        url = 'http://' + url
##                    comment.weburl=url
##                except:
##                    comment.weburl=None
##
##            #name=name.decode('utf8').encode('gb2312')
##
##            info_str='#@#'.join([utils.urlencode(name),utils.urlencode(email),utils.urlencode(url)])
##
##             #info_str='#@#'.join([name,email,url.encode('utf8')])
##            cookiestr='comment_user=%s;expires=%s;path=/;'%( info_str,
##                       (datetime.now()+timedelta(days=100)).strftime("%a, %d-%b-%Y %H:%M:%S GMT")
##                       )
##            comment.ip=self.request.remote_addr
##
##            if parent_id:
##                comment.parent=Comment.get_by_id(parent_id)
##
##            #comment.no=comment.entry.commentcount+1
##            try:
##                comment.save()
##                #memcache.delete("/"+comment.entry.link)
##
##                self.response.headers.add_header( 'Set-Cookie', cookiestr)
##                if useajax:
##                    comment_c=self.get_render('comment',{'comment':comment})
##                    self.write(simplejson.dumps((True,comment_c.decode('utf8')),ensure_ascii = False))
##                else:
##                    self.redirect(self.referer+"#comment-"+str(comment.key().id()))
##
##                #comment.entry.removecache()
##                #memcache.delete("/feed/comments")
##            except Exception,e:
##                if useajax:
##                    self.write(simplejson.dumps((False,-103,_('Comment not allowed.')+unicode(e))))
##                else:
##                    self.error(-102,_('Comment not allowed .'+str(e)))
class ChangeTheme(BaseRequestHandler):
    @requires_admin
    def get(self,slug=None):
       theme=self.param('t')
       self.blog.theme_name=theme
       self.blog.get_theme()
       self.redirect('/')


class do_action(BasePublicPage):
    def get(self,slug=None):

        try:

            func=getattr(self,'action_'+slug)
            if func and callable(func):
                func()
            else:
                self.error(404)
        except BaseException,e:
            raise
            #self.error(404)

    def post(self,slug=None):
        try:
            func=getattr(self,'action_'+slug)
            if func and callable(func):
                func()
            else:
                self.error(404)
        except:
             self.error(404)

    @ajaxonly
    def action_info_login(self):
        if self.login_user:
            self.write(simplejson.dumps({'islogin':True,
                                         'isadmin':self.is_admin,
                                         'name': self.login_user.nickname()}))
        else:
            self.write(simplejson.dumps({'islogin':False}))

##    #@hostonly
##
    def action_proxy(self):
        result=urlfetch.fetch(self.param("url"), headers=self.request.headers)
        if result.status_code == 200:
            self.response.headers['Expires'] = 'Thu, 15 Apr 3010 20:00:00 GMT'
            self.response.headers['Cache-Control'] = 'max-age=3600,public'
            self.response.headers['Content-Type'] = result.headers['Content-Type']
            self.response.out.write(result.content)
        return


    def action_getcomments(self):
        key=self.param('key')
        @request_memcache(key_prefix='',comment_entry_key=key,time=3600*24)
        def get_comments(self,key):
            entry=Entry.get(key)
            comments,cursor,more=Comment.query().filter(Comment.entry ==entry.key).order(-Comment.date).fetch_page(10)



            vals= dict(entry=entry, comments=comments,cursor=more and cursor.to_websafe_string() or '',more=more)
            html=self.get_render('comments',vals)
            self.write(html)
        get_comments(self,key)
        #self.write(simplejson.dumps(html.decode('utf8')))
    def action_getcomments_more(self):
        key=self.param('key')
        @request_memcache(key_prefix='',comment_entry_key=key,time=3600*24)
        def get_comments_more(self,key):
            cursor=self.param('next')
            entry=Entry.get(key)
            from google.appengine.datastore.datastore_query import Cursor
            cur=Cursor.from_websafe_string(cursor)

            comments,cursor,more=Comment.query().filter(Comment.entry ==entry.key).order(-Comment.date).fetch_page(10,start_cursor=cur)

            vals= dict(entry=entry, comments=comments,cursor=more and  cursor.to_websafe_string() or '',more=more)
            html=self.get_render('comments_more',vals)
            self.write(html)
        get_comments_more(self,key)

    def action_getcomment_edit(self):
        key=self.param('key')
        useajax=self.paramint('useajax',1)

        entry=Entry.get(key)
        #loginurl=users.create_login_url(entry.fullurl+(self.isPhone() and "" or "#comment_area"))

        loginurl=users.create_login_url(entry.fullurl)

        vals=dict(loginurl=loginurl,useajax=useajax,entry=entry,is_login=self.is_login,key=key)
        self.render('comment_edit',vals)



        #以下代码不会被执行

##        commentuser=self.request.cookies.get('comment_user', '')
##        if commentuser:
##            commentuser=commentuser.split('#@#')
##        else:
##            commentuser=['','','']
##
##
##        vals= dict(useajax=useajax,entry=entry, user_name=commentuser[0], user_email=commentuser[1],
##                   user_url=commentuser[2], checknum1=random.randint(1, 10), checknum2=random.randint(1, 10))
##        html=self.get_render('comment_edit',vals)
##        self.write(html)
    def action_mobile_more(self):

        self.render('more',{})

    #@request_memcache("action_test")
    def action_test(self):
        self.write(_("this is a test"))
        self.write("<br>")
        blog1=Link.get_by_id_async(2)

        #blog2=ndb.Key(Blog,'default').get_async()

        #blog3=Blog.get_by_id_async('default')
        link=blog1.get_result()
        self.write(link.href)
        #blog=blog2.get_result()

        #self.write(blog.title)
        #blog=blog3.get_result()
        #self.write(blog.subtitle)
        count=Link.query().count()
        self.write(count)

##        self.write(self.blog.test())
##        from google.appengine.api import memcache
##        for c in self.blog.recent_comments():
##            self.write(str(c.content)+"<br>")

##        memcache.set('mm_test2',122)
##        s=memcache.get_multi(None,key_prefix='mm_')
##        self.write(str(s))
####
##        entry=Entry.get_by_id(2004)
##
##        cats=entry.categories
##        for c in cats:
##            self.write(c.name+"<br>")

    def action_test2(self):
        ObjCache.flush_multi(is_category=True,cid=123)
    def action_test3(self):
        ObjCache.flush_all()



class getMedia(webapp.RequestHandler):
    def get(self,slug):
        media=Media.get(slug)
        if media:
            self.response.headers['Expires'] = 'Thu, 15 Apr 3010 20:00:00 GMT'
            self.response.headers['Cache-Control'] = 'max-age=3600,public'
            self.response.headers['Content-Type'] = str(media.mtype)
            self.response.out.write(media.bits)
            a=self.request.get('a')
            if a and a.lower()=='download':
                media.download+=1
                media.put()



class CheckImg(BaseRequestHandler):
    def get(self):
        img = Image()
        imgdata = img.create()
        sess=Session(self,timeout=900)
        if not sess.is_new():
            sess.invalidate()
            sess=Session(self,timeout=900)
        sess['icode']=img.text
        sess.save()
        self.response.headers['Content-Type'] = "image/png"
        self.response.out.write(imgdata)


class CheckCode(BaseRequestHandler):
    def get(self):
        sess=Session(self,timeout=900)
        num1=random.randint(30,50)
        num2=random.randint(1,10)
        code="<span style='font-size:12px;color:red'>%d - %d =</span>"%(num1,num2)
        sess['code']=num1-num2
        sess.save()
        #self.response.headers['Content-Type'] = "text/html"
        self.response.out.write(code)

class Other(BaseRequestHandler):
    def get(self,slug=None):
        if not self.blog.tigger_urlmap(slug,page=self):
            self.error(404)

    def post(self,slug=None):
        content=self.blog.tigger_urlmap(slug,page=self)
        if content:
            self.write(content)
        else:
            self.error(404)

if __name__ == "__main__":
    main()