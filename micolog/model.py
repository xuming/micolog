# -*- coding: utf-8 -*-
"""
DB model for micolog.
This module define the struct of gae db store.
"""
import os, logging
##from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import ndb
##from google.appengine.ext.db import Model as DBModel
from google.appengine.api import memcache
from google.appengine.api import mail
from google.appengine.api import urlfetch
##from google.appengine.api import datastore
import urllib, hashlib, urlparse
import zipfile, re, pickle, uuid,settings
from utils import *
from base import LangIterator
from cache import *
from theme import Theme
from django.utils.translation import ugettext as _
USER_LEVEL_AUTHOR=1
USER_LEVEL_ADMIN=3

class BlogModel(ndb.Model):
    blogname=ndb.StringProperty(default='default')
    #blog=ndb.KeyProperty(kind=Blog)
    @property
    def blog(self):
        return Blog.getBlog(self.blogname)

##    def _pre_put_hook(self):
##
##    def __init__(self,*args, **kwds):
##        ndb.Model.__init__(self,*args,**kwds)
##        if not self.blog:
##            self.blog=Blog.get_by_id('default').key
            #Blog.getBlog('default').key

    @property
    def vkey(self):
        return str(self.key.id())

    @classmethod
    def get_by_key_name(cls,keyname):
        return cls.get_by_id(keyname)

    @classmethod
    def get(cls,key):
        return cls.get_by_id(int(key))


    def delete(self):
        return self.key.delete()

class User(BlogModel):
    #: ndb.UserProperty(required=False) - google user
    user = ndb.UserProperty(required=False)
    #: ndb.StringProperty() - display name
    dispname = ndb.StringProperty()
    #: ndb.StringProperty()
    email = ndb.StringProperty()
    #: ndb.LinkProperty()
    website = ndb.StringProperty()



    #: User level.
    #:  * ``USER_LEVEL_GUEST=0``
    #:  * ``USER_LEVEL_AUTHOR=1``
    #:  * ``USER_LEVEL_ADMIN=3``
    #:  * ``USER_LEVEL_Member=4``
    level=ndb.IntegerProperty(default=USER_LEVEL_AUTHOR)
    password = ndb.StringProperty()
    isAdmin = ndb.ComputedProperty(lambda self: bool(self.level&2))
    isAuthor = ndb.ComputedProperty(lambda self:bool( self.level&1))
    isGuest = ndb.ComputedProperty(lambda self: self.level==0)
    isMember=ndb.ComputedProperty(lambda self: bool(self.level&4))
    def __unicode__(self):
        return self.dispname

    def __str__(self):
        return self.__unicode__().encode('utf-8')


    @classmethod
    def Guest(cls):
        guest=User.get_by_id('guest')
        if not guest:
            guest=User(dispname='guest',email='')
            guest.put()
        return guest

class Blog(ndb.Model):
    owner = ndb.KeyProperty(kind='User')
    author = ndb.StringProperty(default='admin')
    rpcuser = ndb.StringProperty(default='admin')
    rpcpassword = ndb.StringProperty(default='')
    description = ndb.TextProperty()
    #baseurl = ndb.StringProperty( default=None)
    #urlpath = ndb.StringProperty()
    title = ndb.StringProperty( default='Micolog')
    subtitle = ndb.StringProperty( default='This is a micro blog.')
    entrycount = ndb.IntegerProperty(default=0)
    posts_per_page = ndb.IntegerProperty(default=10)
    feedurl = ndb.StringProperty( default='/feed')
    #blogversion = ndb.StringProperty( default='0.30')
    theme_name = ndb.StringProperty( default='default')
    enable_memcache = ndb.BooleanProperty(default=False)
    link_format = ndb.StringProperty( default='%(year)s/%(month)s/%(day)s/%(post_id)s.html')
    comment_notify_mail = ndb.BooleanProperty(default=True)
    #评论顺序
    comments_order = ndb.IntegerProperty(default=0)
    #每页评论数
    comments_per_page = ndb.IntegerProperty(default=20)
    #comment check type 0-No 1-算术 2-验证码 3-客户端计算
    comment_check_type = ndb.IntegerProperty(default=1)
    #0 default 1 identicon
    avatar_style = ndb.IntegerProperty(default=0)

    blognotice = ndb.TextProperty(default='')

    domain = ndb.StringProperty()
    show_excerpt = ndb.BooleanProperty(default=True)
    version = 0.8
    timedelta = ndb.FloatProperty(default=8.0)# hours
    language = ndb.StringProperty(default="en-us")

    sitemap_entries = ndb.IntegerProperty(default=30)
    sitemap_include_category = ndb.BooleanProperty(default=False)
    sitemap_include_tag = ndb.BooleanProperty(default=False)
    sitemap_ping = ndb.BooleanProperty(default=False)
    #allow_guest_comment=ndb.BooleanProperty(default=False)
    default_link_format ='post/%(post_id)s'# ndb.StringProperty( default='post/%(post_id)s')

    default_theme = Theme("default")


    #remove it
    #allow_pingback = ndb.BooleanProperty(default=False)
    #allow_trackback = ndb.BooleanProperty(default=False)



    @property
    def theme (self):
       return  self.get_theme()

    langs = None
    application = None

    @classmethod
    def getBlog(cls,keyname='default'):
        blog=memcache.get('blog_'+keyname)
        if not blog:
            blog=Blog.get_by_id(keyname)
            memcache.set('blog_'+keyname,blog)
        return blog


    @property
    def baseurl(self):
        return "http://"+self.domain

    @ndb.toplevel
    def InitBlogData(self):
        OptionSet.setValue('PluginActive',[u'googleAnalytics', u'wordpress', u'sys_plugin'])
        self.domain=os.environ['HTTP_HOST']
        self.feedurl=self.baseurl+"/feed"


        if os.environ.has_key('HTTP_ACCEPT_LANGUAGE'):
            lang=os.environ['HTTP_ACCEPT_LANGUAGE'].split(',')[0]
        else:
            lang='zh-CN'
        from django.utils.translation import  to_locale
        self.language=to_locale(lang)


        self.put_async()

        entry=Entry(title="Hello world!".decode('utf8'))
        entry.content='<p>Welcome to micolog %s. This is your first post. Edit or delete it, then start blogging!</p>'%self.version
        entry.published=True
        entry.put_async()
        link=Link()
        link.populate(href='http://xuming.net',linktext="Xuming's blog".decode('utf8'))
        link.put_async()
        link=Link()
        link.populate(href='http://eric.cloud-mes.com/',linktext="Eric Guo's blog".decode('utf8'))
        link.put_async()


    @property
    def plugins(self):
        if not hasattr(self,'_plugins'):
            from plugin import Plugins
            self._plugins=Plugins(self)
        return self._plugins

    def tigger_filter(self, name, content, *arg1, **arg2):
        return self.plugins.tigger_filter(name, content, blog=self, *arg1, **arg2)

    def tigger_action(self, name, *arg1, **arg2):
        return self.plugins.tigger_action(name, blog=self, *arg1, **arg2)

    def tigger_urlmap(self, url, *arg1, **arg2):
        return self.plugins.tigger_urlmap(url, blog=self, *arg1, **arg2)

    def get_ziplist(self):
        return self.plugins.get_ziplist();


    def initialsetup(self):
        self.title = 'Your Blog Title'
        self.subtitle = 'Your Blog Subtitle'

    def get_theme(self):
        return Theme(self.theme_name);

    def get_langs(self):
        self.langs = LangIterator()
        return self.langs

    def cur_language(self):
        return self.get_langs().getlang(self.language)

    def rootpath(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    @object_memcache("blog.hotposts",time=3600*24,is_hotposts=True)
    def hotposts(self,count=8):
        return Entry.query().filter(Entry.entrytype =='post',Entry.published ==True).order(-Entry.readtimes).fetch(count)

    @object_memcache("blog.recentposts",time=3600*24)
    def recentposts(self,count=8):
        return Entry.query().filter(Entry.entrytype=='post',Entry.published==True).order(-Entry.date).fetch(count)

    @object_cache("blog.postscount",is_entry=True)
    def postscount(self):
        return Entry.query().filter(Entry.entrytype =='post',Entry.published==True).order(-Entry.date).count()

    @object_memcache("blog.sticky_entries",time=0,is_entry=True)
    def sticky_entries(self):
        return Entry.query().filter(Entry.entrytype =='post')\
            .filter(Entry.published ==True)\
            .filter(Entry.sticky ==True)\
            .order(-Entry.date)

    @object_memcache("blog.get_entries_paged",time=0,is_entry=True)
    def get_entries_paged(self,entrytype='post',published=True,pindex=1,size=20):
        return Entry.query().filter(Entry.entrytype ==entrytype,Entry.published == published).\
                order(-Entry.sticky,-Entry.date).\
                fetch(size, offset = (pindex-1) * size)

    @object_cache("blog.get_blogrolls",is_blogroll=True)
    def blogrolls(self):
        return Link.query().filter(Link.linktype =='blogroll').fetch()

    @object_cache("blog.get_archives",time=3600*24*31,is_archives=True)
    def archives(self):
        return Archive.query().order(-Archive.year,-Archive.month).fetch()

    @object_cache("blog.get_alltags",is_tag=True)
    def tags(self):
        return Tag.query().fetch(1000)

    @object_cache("blog.recent_comments",is_comment=True)
    def recent_comments(self,count=5):
        return Comment.query().order(-Comment.date).fetch(count)

    @object_cache("blog.get_categories",is_category=True)
    def categories(self):
        return Category.query().fetch(1000)

    @object_memcache("blog.menu_pages",is_page=True)
    def menu_pages(self):
        return Entry.query().filter(Entry.entrytype=='page')\
            .filter(Entry.published ==True)\
            .filter(Entry.entry_parent ==0)\
            .order(Entry.menu_order).fetch(100)

    @object_memcache("BLOG.TEST",time=30)
    def test(self):
        import datetime
        return str(datetime.datetime.now())


    def Sitemap_NotifySearch(self):
        """ Send notification of the new Sitemap(s) to the search engines. """


        url = self.baseurl+"/sitemap"

        # Cycle through notifications
        # To understand this, see the comment near the NOTIFICATION_SITES comment
        for ping in settings.NOTIFICATION_SITES:
            query_map = ping[3]
            query_attr = ping[5]
            query_map[query_attr] = url
            query = urllib.urlencode(query_map)
            notify = urlparse.urlunsplit((ping[0], ping[1], ping[2], query, ping[4]))
            # Send the notification
            logging.info('Notifying search engines. %s'%ping[1])
            logging.info('url: %s'%notify)
            try:
                result = urlfetch.fetch(notify)
                if result.status_code == 200:
                    logging.info('Notify Result: %s' % result.content)
                if result.status_code == 404:
                    logging.info('HTTP error 404: Not Found')
                    logging.warning('Cannot contact: %s' % ping[1])

            except :
                logging.error('Cannot contact: %s' % ping[1])



class Category(BlogModel):
    name = ndb.StringProperty()
    slug = ndb.StringProperty()
    parent_cat = ndb.KeyProperty(default=None)

##    @property
##    def posts(self):
##        @object_memcache("category.posts",cache_key=(self.vkey,),cat_id=self.vkey)
##        def _posts():
##            return Entry.query().filter(Entry.entrytype == 'post').filter(Entry.published == True).filter(Entry.categorie_keys == self.key).fetch()
##        return _posts()

    @property
    def count(self):
        @object_memcache("category.postscount",cache_key=(self.vkey,),cat_id=self.vkey)
        def _count():
            return Entry.query().filter(Entry.entrytype == 'post').filter(Entry.published == True).filter(Entry.categorie_keys == self.key).count()
        return _count()

    def put(self):
        ndb.Model.put(self)
        ObjCache.flush_multi(is_category=True)
        ObjCache.flush_multi(cat_id=self.key.id)

        self.blog.tigger_action("save_category", self)

    def delete(self):
        for entry in Entry.query().filter(Entry.categorie_keys == self):
            entry.categorie_keys.remove(self.key())
            entry.put()
        for cat in self.children:
            cat.delete()
        ndb.Model.delete(self)
        ObjCache.flush_multi(is_category=True)
        ObjCache.flush_multi(cat_id=self.key.id())
        self.blog.tigger_action("delete_category", self)

    def ID(self):
        return self.key.id()

    @classmethod
    def get_from_id(cls, id):
        cate = Category.get_by_id(id)
        return

    @property
    def children(self):
        return Category.query().filter(Category.parent_cat==self.key).fetch()

    @classmethod
    def allTops(self):
        return [c for c in Category.query() if not c.parent_cat]

class Archive(BlogModel):
    monthyear = ndb.StringProperty()
    year = ndb.StringProperty()
    month = ndb.StringProperty()
    entrycount = ndb.IntegerProperty(default=0)
    date = ndb.DateTimeProperty(auto_now_add=True)


class Tag(BlogModel):
    tag = ndb.StringProperty()
    slug = ndb.StringProperty()
    tagcount = ndb.IntegerProperty(default=0)

    @property
    def posts(self):
        return Entry.all('entrytype =', 'post').filter("published =", True).filter('tags =', self)

    @classmethod
    def add(cls, value):
        if value:
            v = value.strip()
            tag = Tag.get_by_key_name(v)
            if not tag:
                tag = Tag(key_name=v)
                tag.tag = v
                tag.slug = slugify(v)
            tag.tagcount += 1
            tag.put()
            return tag
        else:
            return None

    @classmethod
    def remove(cls, value):
        if value:
            tag = Tag.get_by_key_name(value)
            if tag:
                if tag.tagcount > 1:
                    tag.tagcount -= 1
                    tag.put()
                else:
                    tag.delete()

    def __str__(self):
        return self.tag

    def put(self):
        ndb.Model.put(self)
        ObjCache.flush_multi(is_tag=True)
        ObjCache.flush_multi(tag_id=self.vkey)

    def delete(self):
        ndb.Model.delete(self)
        ObjCache.flush_multi(is_tag=True)
        ObjCache.flush_multi(tag_id=self.vkey)

class Link(BlogModel):
    href = ndb.StringProperty(default='')
    linktype = ndb.StringProperty( default='blogroll')
    linktext = ndb.StringProperty( default='')
    linkcomment = ndb.StringProperty(default='')
    createdate = ndb.DateTimeProperty(auto_now=True)

    @property
    def get_icon_url(self):
        "get ico url of the wetsite"
        ico_path = '/favicon.ico'
        ix = self.href.find('/', len('http://') )
        return (ix>0 and self.href[:ix] or self.href ) + ico_path

    def put(self):
        ndb.Model.put(self)
        #ObjCache.flush_multi(is_link=True)
        #self.blog.tigger_action("save_link", self)


    #def delete(self):
        #ndb.Model.delete(self)
        #ObjCache.flush_multi(is_link=True)
        #self.blog.tigger_action("delete_link", self)

class Entry(BlogModel):
    author = ndb.KeyProperty(kind=User)
    author_name = ndb.StringProperty()
    published = ndb.BooleanProperty(default=False)
    contentFormat=ndb.TextProperty(default='html')
    content = ndb.TextProperty(default='')
    readtimes = ndb.IntegerProperty(default=0)
    title = ndb.StringProperty( default='')
    date = ndb.DateTimeProperty(auto_now_add=True)
    mod_date = ndb.DateTimeProperty(auto_now_add=True)
    tags = ndb.StringProperty(repeated=True)
    categorie_keys = ndb.KeyProperty(repeated=True)
    slug = ndb.StringProperty( default='')
    link = ndb.StringProperty( default='')
    monthyear = ndb.StringProperty()
    entrytype = ndb.StringProperty( default='post', choices=[
            'post', 'page'])
    entry_parent = ndb.IntegerProperty(default=0)#When level=0 show on main menu.
    menu_order = ndb.IntegerProperty(default=0)

##    trackbackcount = ndb.IntegerProperty(default=0)

    allow_comment = ndb.BooleanProperty(default=True) #allow comment
    #allow_pingback=ndb.BooleanProperty(default=False)
    #allow_trackback = ndb.BooleanProperty(default=True)
    password = ndb.StringProperty()

    #compatible with wordpress
    #is_wp = ndb.BooleanProperty(default=False)
    #post_id = ndb.IntegerProperty()
    excerpt = ndb.StringProperty()

    #external page
    is_external_page = ndb.BooleanProperty(default=False)
    target = ndb.StringProperty(default="_self")
    external_page_address = ndb.StringProperty()

    #keep in top
    sticky = ndb.BooleanProperty(default=False)

    commentcount=ndb.IntegerProperty(default=0)

    postname = ''
    _relatepost = None

##    @property
##    def commentcount(self):
##        @object_cache("entry.commentcount",time=0,cache_key=(self.vkey,),comments=True,entry_id=self.vkey)
##        def _commentcount():
##            return Comment.query().filter(
##                                Comment.entry==self.key,\
##                                Comment.ctype==COMMENT_NORMAL,\
##                                Comment.status==COMMENT_APPROVE)\
##                                .count()
##        return _commentcount()

    @property
    def post_id(self):
       return self.key.id()

    @property
    def content_excerpt(self):
        return self.get_content_excerpt(_('..more'))

    def meta_description(self):
        return trim_excerpt(self.content)

    def get_content(self):
        return self.content#parse(self.content)

    def get_author_user(self):
        if not self.author:
            self.author = self.blog.owner
        return self.author

    def get_content_excerpt(self, more='..more'):
        if self.blog.show_excerpt:
            if self.excerpt:
                return self.excerpt+' <a href="/%s" class="e_more">%s</a>'%(self.link, more)
            else:
                sc = self.content.split('<!--more-->')
                if len(sc) > 1:
                    return sc[0]+u' <a href="/%s" class="e_more">%s</a>'%(self.link, more)
                else:
                    return sc[0]
        else:
            return self.content

    def slug_onchange(self, curval, newval):
        if not (curval==newval):
            self.setpostname(newval)
#todo fix double slug
##    def setpostname(self, newval):
##        #check and fix double slug
##        if newval:
##            slugcount = Entry.query()\
##                              .filter('entrytype', self.entrytype)\
##                              .filter('date <', self.date)\
##                              .filter('slug =', newval)\
##                              .filter('published', True)\
##                              .count()
##            if slugcount > 0:
##                self.postname = newval+str(slugcount)
##            else:
##                self.postname = newval
##        else:
##            self.postname = ""




    @property
    def fullurl(self):
        if self.link and self.link[0]!='?':
            return self.blog.baseurl+'/'+self.link;
        else:
            return self.blog.baseurl+'/post/'+str(self.post_id)

    @property
    def categories(self):
        @object_memcache("entry.categories",cache_key=(self.vkey),entry_id=self.vkey)
        def _categories():
            try:
                return ndb.get(self.categorie_keys)
            except:
                return []
        return _categories()

    @property
    def post_status(self):
        return  self.published and 'publish' or 'draft'

    def settags(self, values):
        if not values:tags = []
        if type(values) == type([]):
            tags = values
        else:
            tags = values.split(',')



        if not self.tags:
            removelist = []
            addlist = tags
        else:
            #search different  tags
            removelist = [n.strip() for n in self.tags if n not in tags]
            addlist = [n.strip() for n in tags if n not in self.tags]
        for v in removelist:
            Tag.remove(v)
        for v in addlist:
            Tag.add(v)
        self.tags = [t.strip() for t in tags]


    def get_comments_by_page(self,index, psize):
        @object_memcache("entry.get_comments_by_page",time=0,cache_key=(self.vkey,self.blog.comments_order,index,psize),entry_id=self.vkey)
        def _get_comments_by_page():
            if self.blog.comments_order:
                commentslist= Comment.query().filter(Comment.entry ==self.key)\
                        .filter(Comment.ctype == COMMENT_NORMAL)\
                        .filter(Comment.status == COMMENT_APPROVE)\
                        .order(-Comment.date).fetch(psize, offset=(index-1) * psize)
            else:
                commentslist= Comment.query().filter(Comment.entry ==self.key)\
                        .filter(Comment.ctype == COMMENT_NORMAL)\
                        .filter(Comment.status == COMMENT_APPROVE)\
                        .order(Comment.date).fetch(psize, offset=(index-1) * psize)
            i=0;
            for comment in commentslist:
                comment.no=(index-1) * psize+i
                i=i+1
            return commentslist
        return _get_comments_by_page()

    @property
    def strtags(self):
        return ','.join(self.tags)

    @property
    def edit_url(self):
        return '/admin/%s?key=%s&action=edit'%(self.entrytype, self.key())


    def comments(self,order):
        @object_memcache("entry.comments",time=0,cache_key=(self.vkey,order),comments=True,entry_id=self.vkey)
        def _comments():
            if order:
                commentslist= Comment.query().filter(Comment.entry == self.key)\
                        .filter(Comment.ctype == COMMENT_NORMAL)\
                        .filter(Comment.status == COMMENT_APPROVE)\
                        .order(-Comment.date).fetch(100)
            else:
                commentslist= Comment.query().filter(Comment.entry == self.key)\
                        .filter(Comment.ctype == COMMENT_NORMAL)\
                        .filter(Comment.status == COMMENT_APPROVE)\
                        .order(Comment.date).fetch(100)
            i=0
            for comment in commentslist:
                comment.no=i
                i=i+1
            return commentslist

        return _comments()

##    @object_cache("entry.purecomments")
##    def purecomments(self):
##        if self.blog.comments_order:
##            return Comment.query().filter('entry =', self).filter('ctype =', 0).order('-date')
##        else:
##            return Comment.query().filter('entry =', self).filter('ctype =', 0).order('date')

##    def trackcomments(self):
##        if self.blog.comments_order:
##            return Comment.query().filter('entry =', self).filter('ctype IN', [1, 2]).order('-date')
##        else:
##            return Comment.query().filter('entry =', self).filter('ctype IN', [1, 2]).order('date')
    #@object_cache("entry.commentsTops")
    def commentsTops(self):
        return [c for c  in self.comments() if c.parent_key() == None]


    def delete_comments(self):
        cmts = Comment.query().filter(Comment.entry ==self.key)
        for comment in cmts:
            comment.delete()
        self.commentcount = 0
        self.put()
##        self.trackbackcount = 0

##    def update_commentno(self):
##        cmts = Comment.query().filter('entry =', self).order('date')
##        i = 1
##        for comment in cmts:
##            comment.no = i
##            i += 1
##            comment.store()

    def update_archive(self, cnt=1):
        """Checks to see if there is a month-year entry for the
        month of current blog, if not creates it and increments count"""
        my = self.date.strftime('%B %Y') # September-2008
        sy = self.date.strftime('%Y') #2008
        sm = self.date.strftime('%m') #09


        archive = Archive.query().filter(Archive.monthyear==my).get()
        if self.entrytype == 'post':
            if not archive:
                archive = Archive(monthyear=my, year=sy, month=sm, entrycount=1)
                self.monthyear = my
                archive.put()
            else:
                # ratchet up the count
                archive.entrycount += cnt
                archive.put()
        self.blog.entrycount += cnt
        self.blog.put()

    def get_min_category(self):
        min = self.categories[0].ID()
        category = self.categories[0]
        for cat in self.categories:
            if min > cat.ID():
                min = cat.ID()
                category = cat

        return category

    def save(self, is_publish=False):
        """
        Use this instead of self.put(), as we do some other work here
        @is_publish:Check if need publish id
        """
        self.blog.tigger_action("pre_save_post", self, is_publish)
        if not self.date:
            self.date=datetime.now()
            my = self.date.strftime('%B %Y') # September 2008
            self.monthyear = my
        old_publish = self.published
        self.mod_date = datetime.now()

        if is_publish:
            self.put()
            #if not self.is_wp:
            #    self.put()
                #self.post_id = self.key().id()

            #fix for old version
            if not self.postname:
                self.postname=self.slug


            vals = {'year':self.date.year, 'month':str(self.date.month).zfill(2), 'day':self.date.day,
                    'postname':self.postname, 'post_id':self.post_id}


            if self.entrytype == 'page':
                if self.slug:
                    self.link = self.slug
                else:
                    #use external page address as link
                    if self.is_external_page:
                        self.link = self.external_page_address
                    else:
                        self.link = self.blog.default_link_format%vals
            else:
                if self.blog.link_format and self.postname:
                    self.link = self.blog.link_format.strip()%vals
                else:
                    self.link = self.blog.default_link_format%vals

        self.published = is_publish
        self.put()

        if is_publish:
            if self.blog.sitemap_ping:
                self.blog.Sitemap_NotifySearch()

        if old_publish and not is_publish:
            self.update_archive(-1)
        if not old_publish and is_publish:
            self.update_archive(1)

        self.removecache()

        self.put()
        self.blog.tigger_action("save_post", self, is_publish)




    def removecache(self):
        if(self.entrytype=="page"):
            ObjCache.flush_multi(is_page=True)
        else:
            ObjCache.flush_multi(is_entry=True)
        ObjCache.flush_multi(entry_id=self.vkey)
##        memcache.delete('/')
##        memcache.delete('/'+self.link)
##        memcache.delete('/sitemap')
##        memcache.delete('blog.postcount')
        self.blog.tigger_action("clean_post_cache", self)

    @property
    def next(self):
        return Entry.query().filter(Entry.entrytype == 'post').filter(Entry.published == True).order(Entry.date).filter(Entry.date > self.date).fetch(1)


    @property
    def prev(self):
        return Entry.query().filter(Entry.entrytype == 'post').filter(Entry.published == True).order(-Entry.date).filter(Entry.date < self.date).fetch(1)

    @property
    def relateposts(self):
        if  self._relatepost:
            return self._relatepost
        else:
            if self.tags:
                #self._relatepost = Entry.gql("WHERE published=True and tags IN :1 and post_id!=:2 order by post_id desc ", self.tags, self.post_id).fetch(5)
                self._relatepost =Entry.query().filter(Entry.published==True,Entry.tags.IN(self.tags), Entry.key!=self.key).order(-Entry.key,-Entry.date).fetch(5)
            else:
                self._relatepost = []
            return self._relatepost

    @property
    def trackbackurl(self):
        if self.link.find("?") > -1:
            return self.blog.baseurl+"/"+self.link+"&code="+str(self.key())
        else:
            return self.blog.baseurl+"/"+self.link+"?code="+str(self.key())

    def getbylink(self):
        pass

    def delete(self):
        self.blog.tigger_action("pre_delete_post", self)
        if self.published:
            self.update_archive(-1)
        self.delete_comments()
        self.removecache()
        self.key.delete()
        self.blog.tigger_action("delete_post", self)




#用于兼容旧版本，新版本中不再使用Comment对象
COMMENT_NORMAL=0
COMMENT_TRACKBACK=1
COMMENT_PINGBACK=2

COMMENT_HOLD=0
COMMENT_APPROVE=1
COMMENT_SPAM=2
COMMENT_TRASH=3

BBODY='''Hi~ New reference on your comment for post "%(title)s"
Author : %(author)s
URL	: %(weburl)s
Comment:
%(content)s
You can see all comments on this post here:
%(commenturl)s
'''

class Comment(BlogModel):
    entry = ndb.KeyProperty(Entry)
    user=ndb.KeyProperty(User)
    date = ndb.DateTimeProperty(auto_now_add=True)
    content = ndb.TextProperty(required=True)
    author=ndb.StringProperty()
    email=ndb.StringProperty()
    weburl=ndb.StringProperty()
    status=ndb.IntegerProperty(default=0)
    reply_notify_mail=ndb.BooleanProperty(default=False)
    ip=ndb.StringProperty()
    ctype=ndb.IntegerProperty(default=COMMENT_NORMAL)

    @property
    def shortcontent(self, len=20):
        """
        Short string for this message.
        """
        scontent = self.content
        scontent = re.sub(r'<br\s*/>', ' ', scontent)
        scontent = re.sub(r'<[^>]+>', '', scontent)
        scontent = re.sub(r'(@[\S]+)-\d{2,7}', r'\1:', scontent)
        return scontent[:len].replace('<', '&lt;').replace('>', '&gt;')

    def gravatar_url(self):

        # Set your variables here
        if self.blog.avatar_style == 0:
            default = self.blog.baseurl+'/static/images/homsar.jpeg'
        else:
            default = 'identicon'

        if not self.email:
            return default

        size = 50

        try:
            # construct the url
            imgurl = "http://www.gravatar.com/avatar/"
            imgurl += hashlib.md5(self.email.lower()).hexdigest()+"?"+ urllib.urlencode({
                    'd':default, 's':str(size), 'r':'G'})

            return imgurl
        except:
            return default

    def save(self):
        self.status=COMMENT_APPROVE
        self.blog.tigger_action("pre_comment", self)
        self.put()
        entry=self.entry.get()
        if entry:
            entry.commentcount=entry.commentcount+1
            entry.put()
        self.reply_notify()

        ObjCache.flush_multi(comment_entry_key=self.entry.id())
        self.blog.tigger_action("save_comment", self)

    def put(self):
        ndb.Model.put(self)
        ObjCache.flush_multi(is_comment=True)
        ObjCache.flush_multi(comments=True,entry_id=self.entry.id)

    def delete(self):
        entry=self.entry.get()
        if entry:
            entry.commentcount=entry.commentcount-1
            entry.put()
        ObjCache.flush_multi(comment_entry_key=self.entry.id())
        self.key.delete()

    def reply_notify(self):
  		#reply comment mail notify
        if not self.blog.owner: return
        comment=self


        refers = re.findall(r'#comment-(\d+)', comment.content)
        if len(refers)!=0:
            replyIDs=[ndb.Key(Comment,int(a)) for a in refers]
            commentlist=ndb.get_multi(replyIDs)

            emaillist=[c.email for c in commentlist if c.reply_notify_mail]
            emaillist = {}.fromkeys(emaillist).keys()
            entry=comment.entry.get()
            for refer in emaillist:
                if mail.is_email_valid(refer):
                        emailbody = BBODY%{'title':entry.title,
                           'author':comment.author,
                           'weburl':comment.weburl,
                           'email':comment.email,
                           'content':comment.content,
                           'commenturl':entry.fullurl+"#comment-"+str(comment.key.id())
                         }
                        message = mail.EmailMessage(sender = self.blog.owner.email(),subject = 'Comments:'+entry.title)
                        message.to = refer
                        message.body = emailbody
                        message.send()


#从1.0版本开始，使用Message取代Comment,暂时不使用
##MESSAGE_HOLD=0
##MESSAGE_APPROVE=1
##MESSAGE_SPAM=2
##MESSAGE_TRASH=3


##class Message(BlogModel):
##    """
##    message object.
##
##    ..  warning::
##        In micolog 0.8. message don't belongs to any entry.
##        Every thing can be messaged if it has a unique message entry key.
##    """
##    #: ndb.StringProperty() - The unique key of a message.
##    message_entry_key=ndb.StringProperty()
##    #: ndb.SelfReference() - Parent message.
##    message_parent=ndb.SelfReference()
##    #: ndb.DateTimeProperty(auto_now_add=True) - The date of the message created.
##    date = ndb.DateTimeProperty(auto_now_add=True)
##    #: ndb.TextProperty(required=True)- message content.
##    content = ndb.TextProperty(required=True)
##    #: ndb.StringProperty() - Author of this message.
##    author = ndb.StringProperty()
##    #: ndb.EmailProperty() - Email address
##    email = ndb.EmailProperty()
##    #: ndb.URLProperty() - Web url
##    weburl = ndb.URLProperty()
##
##    status = ndb.IntegerProperty(default=MESSAGE_APPROVE)
##    """
##    ndb.IntegerProperty(default=MESSAGE_APPROVE)
##
##    Comment status:
##        * MESSAGE_HOLD=0
##        * MESSAGE_APPROVE=1
##        * MESSAGE_SPAM=2
##        * MESSAGE_TRASH=3
##    """
##    #: ndb.BooleanProperty(default=False)
##    #: Whether need send mail to messageer when a reply occurred
##    reply_notify_mail = ndb.BooleanProperty(default=False)
##    #: ndb.StringProperty() - Ip address.
##    ip = ndb.StringProperty()
##
##
####    #ctype = ndb.IntegerProperty(default=0)
####    """
####    ndb.IntegerProperty(default=MESSAGE_TYPE_NORMAL)
####
####    Comment Type.
####        * MESSAGE_TYPE_NORMAL = 0
####        * MESSAGE_TYPE_TRACKBACK = 1
####        * MESSAGE_TYPE_PINGBACK = 2
####    """
##
####    #: Comment No.
####    no = ndb.IntegerProperty(default=0)
####    Comment order.
####    message_order = ndb.IntegerProperty(default=1)
####
####    @property
####    def mpindex(self):
####        count = self.entry.messagecount
####        no = self.no
####        if self.blog.messages_order:
####            no = count-no+1
####        index = no / self.blog.messages_per_page
####        if no % self.blog.messages_per_page or no == 0:
####            index += 1
####        return index
##
##    @property
##    def shortcontent(self, len=20):
##        """
##        Short string for this message.
##        """
##        scontent = self.content
##        scontent = re.sub(r'<br\s*/>', ' ', scontent)
##        scontent = re.sub(r'<[^>]+>', '', scontent)
##        scontent = re.sub(r'(@[\S]+)-\d{2,7}', r'\1:', scontent)
##        return scontent[:len].replace('<', '&lt;').replace('>', '&gt;')
##
##
####    def gravatar_url(self):
####
####        # Set your variables here
####        if self.blog.avatar_style == 0:
####            default = self.blog.baseurl+'/static/images/homsar.jpeg'
####        else:
####            default = 'identicon'
####
####        if not self.email:
####            return default
####
####        size = 50
####
####        try:
####            # construct the url
####            imgurl = "http://www.gravatar.com/avatar/"
####            imgurl += hashlib.md5(self.email.lower()).hexdigest()+"?"+ urllib.urlencode({
####                    'd':default, 's':str(size), 'r':'G'})
####
####            return imgurl
####        except:
####            return default
##
##    def put(self):
##        """
##        Save message to ndb.
##        """
##        self.blog.tigger_action("pre_message", self)
##        ndb.Model.put(self)
##        self.blog.tigger_action("save_message", self)
##
##    def delete(self):
##        """
##        Delete message.
##        """
##        ndb.Model.delete(self)
##        self.blog.tigger_action("delete_message", self)
##
##    @property
##    def children(self):
##        """Children messages."""
##        messages = Message.query().filter("message_parent =",self)
##
##    def store(self, **kwargs):
##        """
##        This method used by function pickle(). It make data simple.
##        """
##        rpc = datastore.GetRpcFromKwargs(kwargs)
##        self._populate_internal_entity()
##        return datastore.Put(self._entity, rpc=rpc)

class Media(BlogModel):
    """
    Media object. Used to store files. Such as: gif,jpeg,txt ... and so on.
    """

    #: ndb.StringProperty() - name for media
    name = ndb.StringProperty()
    #: ndb.StringProperty() - media type. Such as ``image\jpeg`` ``image\gif``
    mtype = ndb.StringProperty()
    #: ndb.BlobProperty() - bits for media object.
    bits = ndb.BlobProperty()
    #: ndb.DateTimeProperty(auto_now_add=True) - media upload date.
    date = ndb.DateTimeProperty(auto_now_add=True)
    #: ndb.IntegerProperty(default=0) - download times of this media.
    download = ndb.IntegerProperty(default=0)


    @property
    def size(self):
        """
        Get media object size.
        """
        return len(self.bits)



class OptionSet(BlogModel):
    """
    This class provide some methods to get and set value from GAE db store.
    Usually, it used by micolog plugins.
    exmpale::

        >>> from micolog.model import OptionSet
        >>> v=[1,2,4]
        >>> OptionSet.setValue('v',v)
        >>> OptionSet.getValue('v')
        [1, 2, 4]
        >>> OptionSet.remove('v')

    """

    name = ndb.StringProperty() #: ndb.StringProperty() - key name
    value = ndb.PickleProperty() #: ndb.TextProperty() - key value


    @classmethod
    def getValue(cls, name, default=None):
        """
        Get value from ndb.
        """
        try:
            opt = OptionSet.get_by_id(name)
            return opt.value
            #return pickle.loads(str(opt.value))
        except:
            return default

    @classmethod
    def setValue(cls, name, value):
        """
        Save value to ndb.
        Args:
            name (str):  The name to use.
        """
        opt = OptionSet.get_or_insert(name)
        opt.name = name
        opt.value=value
        #opt.value = pickle.dumps(value)
        opt.put()

    @classmethod
    def remove(cls, name):
        """
        Remove value form ndb.
        """
        opt = OptionSet.get_by_id(name)
        if opt:
            opt.delete()


