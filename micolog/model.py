# -*- coding: utf-8 -*-
"""
DB model for micolog.
This module define the struct of gae db store.
"""
import os, logging
##from google.appengine.api import users
from google.appengine.ext import db
##from google.appengine.ext.db import Model as DBModel
from google.appengine.api import memcache
##from google.appengine.api import mail
##from google.appengine.api import urlfetch
##from google.appengine.api import datastore
##from datetime import datetime
##from micolog.utils import trim_excerpt
##import urllib, hashlib, urlparse
import zipfile, re, pickle, uuid
##from micolog.utils import slugify
##from theme import Theme
from cache import *

class Blog(db.Model):
    owner = db.UserProperty()
    author = db.StringProperty(default='admin')
    rpcuser = db.StringProperty(default='admin')
    rpcpassword = db.StringProperty(default='')
    description = db.TextProperty()
    #baseurl = db.StringProperty(multiline=False, default=None)
    #urlpath = db.StringProperty(multiline=False)
    title = db.StringProperty(multiline=False, default='Micolog')
    subtitle = db.StringProperty(multiline=False, default='This is a micro blog.')
    entrycount = db.IntegerProperty(default=0)
    posts_per_page = db.IntegerProperty(default=10)
    feedurl = db.StringProperty(multiline=False, default='/feed')
    #blogversion = db.StringProperty(multiline=False, default='0.30')
    theme_name = db.StringProperty(multiline=False, default='default')
    enable_memcache = db.BooleanProperty(default=False)
    link_format = db.StringProperty(multiline=False, default='%(year)s/%(month)s/%(day)s/%(postname)s.html')
    comment_notify_mail = db.BooleanProperty(default=True)
    #评论顺序
    comments_order = db.IntegerProperty(default=0)
    #每页评论数
    comments_per_page = db.IntegerProperty(default=20)
    #comment check type 0-No 1-算术 2-验证码 3-客户端计算
    comment_check_type = db.IntegerProperty(default=1)
    #0 default 1 identicon
    avatar_style = db.IntegerProperty(default=0)

    blognotice = db.TextProperty(default='')

    domain = db.StringProperty()
    show_excerpt = db.BooleanProperty(default=True)
    version = 0.8
    timedelta = db.FloatProperty(default=8.0)# hours
    language = db.StringProperty(default="en-us")

    sitemap_entries = db.IntegerProperty(default=30)
    sitemap_include_category = db.BooleanProperty(default=False)
    sitemap_include_tag = db.BooleanProperty(default=False)
    sitemap_ping = db.BooleanProperty(default=False)
    default_link_format = db.StringProperty(multiline=False, default='?p=%(post_id)s')
    #todo
    #default_theme = Theme("default")


    #remove it
    #allow_pingback = db.BooleanProperty(default=False)
    #allow_trackback = db.BooleanProperty(default=False)

    theme = None
    langs = None
    application = None

    @classmethod
    def getBlog(cls):
        blog=memcache.get("gblog")
        if not blog:
            blog=Blog.get_by_key_name('default')
            if not blog:
                blog=Blog(key_name = 'default')
                blog.InitBlogData()
            memcache.set("gblog",blog)
        return blog

    def InitBlogData(self):

        OptionSet.setValue('PluginActive',[u'googleAnalytics', u'wordpress', u'sys_plugin'])
        self.domain=os.environ['HTTP_HOST']
        self.baseurl="http://"+self.domain
        self.feedurl=self.baseurl+"/feed"
        os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
        self.admin_essential = False
        if os.environ.has_key('HTTP_ACCEPT_LANGUAGE'):
            lang=os.environ['HTTP_ACCEPT_LANGUAGE'].split(',')[0]
        from django.utils.translation import  activate,to_locale
        self.language=to_locale(lang)
        self.admin_essential=False
        from django.conf import settings
        settings._target = None
        activate(self.language)
        self.save()

        entry=Entry(title="Hello world!".decode('utf8'))
        entry.content='<p>Welcome to micolog %s. This is your first post. Edit or delete it, then start blogging!</p>'%g_blog.version
        entry.save(True)
        link=Link(href='http://xuming.net',linktext="Xuming's blog".decode('utf8'))
        link.put()
        link=Link(href='http://eric.cloud-mes.com/',linktext="Eric Guo's blog".decode('utf8'))
        link.put()



    def __init__(self,
                       parent=None,
                       key_name=None,
                       _app=None,
                       _from_entity=False,
                       **kwds):
        from plugin import Plugins
        self.plugins = Plugins(self)
        db.Model.__init__(self, parent, key_name, _app, _from_entity, **kwds)

    def tigger_filter(self, name, content, *arg1, **arg2):
        return self.plugins.tigger_filter(name, content, blog=self, *arg1, **arg2)

    def tigger_action(self, name, *arg1, **arg2):
        return self.plugins.tigger_action(name, blog=self, *arg1, **arg2)

    def tigger_urlmap(self, url, *arg1, **arg2):
        return self.plugins.tigger_urlmap(url, blog=self, *arg1, **arg2)

    def get_ziplist(self):
        return self.plugins.get_ziplist();

    def save(self):
        self.put()

    def initialsetup(self):
        self.title = 'Your Blog Title'
        self.subtitle = 'Your Blog Subtitle'

    def get_theme(self):
        self.theme = Theme(self.theme_name);
        return self.theme

    def get_langs(self):
        self.langs = LangIterator()
        return self.langs

    def cur_language(self):
        return self.get_langs().getlang(self.language)

    def rootpath(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    @vcache("blog.hotposts",args=("count"))
    def hotposts(self,count=8):
        return Entry.all().filter('entrytype =', 'post').filter("published =", True).order('-readtimes').fetch(count)

    @vcache("blog.recentposts",args=("count"))
    def recentposts(self,count=8):
        return Entry.all().filter('entrytype =', 'post').filter("published =", True).order('-date').fetch(count)

    @vcache("blog.postscount")
    def postscount(self):
        return Entry.all().filter('entrytype =', 'post').filter("published =", True).order('-date').count()

    @vcache("blog.sticky_entries")
    def sticky_entries(self):
        return Entry.all().filter('entrytype =','post')\
            .filter('published =',True)\
            .filter('sticky =',True)\
            .order('-date')

class Category(db.Model):
    uid = db.IntegerProperty()
    name = db.StringProperty(multiline=False)
    slug = db.StringProperty(multiline=False)
    parent_cat = db.SelfReferenceProperty()
    date = db.DateTimeProperty(auto_now_add=True)
    @property
    def posts(self):
        return Entry.all().filter('entrytype =', 'post').filter("published =", True).filter('categorie_keys =', self)

    @property
    def count(self):
        return self.posts.count()

    def put(self):
        db.Model.put(self)
        g_blog.tigger_action("save_category", self)

    def delete(self):
        for entry in Entry.all().filter('categorie_keys =', self):
            entry.categorie_keys.remove(self.key())
            entry.put()
        for cat in Category.all().filter('parent_cat =', self):
            cat.delete()
        db.Model.delete(self)
        g_blog.tigger_action("delete_category", self)

    def ID(self):
        try:
            id = self.key().id()
            if id:
                return id
        except:
            pass

        if self.uid :
            return self.uid
        else:
            #旧版本Category没有ID,为了与wordpress兼容
            from random import randint
            uid = randint(0, 99999999)
            cate = Category.all().filter('uid =', uid).get()
            while cate:
                uid = randint(0, 99999999)
                cate = Category.all().filter('uid =', uid).get()
            self.uid = uid
            print uid
            self.put()
            return uid

    @classmethod
    def get_from_id(cls, id):
        cate = Category.get_by_id(id)
        if cate:
            return cate
        else:
            cate = Category.all().filter('uid =', id).get()
            return cate

    @property
    def children(self):
        key = self.key()
        return [c for c in Category.all().filter('parent_cat =', self)]


    @classmethod
    def allTops(self):
        return [c for c in Category.all() if not c.parent_cat]

class Archive(db.Model):
    monthyear = db.StringProperty(multiline=False)
    year = db.StringProperty(multiline=False)
    month = db.StringProperty(multiline=False)
    entrycount = db.IntegerProperty(default=0)
    date = db.DateTimeProperty(auto_now_add=True)

class Tag(db.Model):
    tag = db.StringProperty(multiline=False)
    slug = db.StringProperty(multiline=False)
    tagcount = db.IntegerProperty(default=0)
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


class Link(db.Model):
    href = db.StringProperty(multiline=False, default='')
    linktype = db.StringProperty(multiline=False, default='blogroll')
    linktext = db.StringProperty(multiline=False, default='')
    linkcomment = db.StringProperty(multiline=False, default='')
    createdate = db.DateTimeProperty(auto_now=True)

    @property
    def get_icon_url(self):
        "get ico url of the wetsite"
        ico_path = '/favicon.ico'
        ix = self.href.find('/', len('http://') )
        return (ix>0 and self.href[:ix] or self.href ) + ico_path

    def put(self):
        db.Model.put(self)
        g_blog().tigger_action("save_link", self)


    def delete(self):
        db.Model.delete(self)
        g_blog().tigger_action("delete_link", self)

class Entry(db.Model):
    author = db.UserProperty()
    author_name = db.StringProperty()
    published = db.BooleanProperty(default=False)
    content = db.TextProperty(default='')
    readtimes = db.IntegerProperty(default=0)
    title = db.StringProperty(multiline=False, default='')
    date = db.DateTimeProperty(auto_now_add=True)
    mod_date = db.DateTimeProperty(auto_now_add=True)
    tags = db.StringListProperty()
    categorie_keys = db.ListProperty(db.Key)
    slug = db.StringProperty(multiline=False, default='')
    link = db.StringProperty(multiline=False, default='')
    monthyear = db.StringProperty(multiline=False)
    entrytype = db.StringProperty(multiline=False, default='post', choices=[
            'post', 'page'])
    entry_parent = db.IntegerProperty(default=0)#When level=0 show on main menu.
    menu_order = db.IntegerProperty(default=0)
    commentcount = db.IntegerProperty(default=0)
    trackbackcount = db.IntegerProperty(default=0)

    allow_comment = db.BooleanProperty(default=True) #allow comment
    #allow_pingback=db.BooleanProperty(default=False)
    allow_trackback = db.BooleanProperty(default=True)
    password = db.StringProperty()

    #compatible with wordpress
    is_wp = db.BooleanProperty(default=False)
    post_id = db.IntegerProperty()
    excerpt = db.StringProperty(multiline=True)

    #external page
    is_external_page = db.BooleanProperty(default=False)
    target = db.StringProperty(default="_self")
    external_page_address = db.StringProperty()

    #keep in top
    sticky = db.BooleanProperty(default=False)


    postname = ''
    _relatepost = None

    @property
    def content_excerpt(self):
        return self.get_content_excerpt(_('..more').decode('utf8'))

    def meta_description(self):
        return trim_excerpt(self.content)

    def get_content(self):
        return self.content#parse(self.content)
    def get_author_user(self):
        if not self.author:
            self.author = g_blog.owner
        return User.all().filter('email =', self.author.email()).get()

    def get_content_excerpt(self, more='..more'):
        if g_blog.show_excerpt:
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

    def setpostname(self, newval):
        #check and fix double slug
        if newval:
            slugcount = Entry.all()\
                              .filter('entrytype', self.entrytype)\
                              .filter('date <', self.date)\
                              .filter('slug =', newval)\
                              .filter('published', True)\
                              .count()
            if slugcount > 0:
                self.postname = newval+str(slugcount)
            else:
                self.postname = newval
        else:
            self.postname = ""




    @property
    def fullurl(self):
        return g_blog.baseurl+'/'+self.link;

    @property
    def categories(self):
        try:
            return db.get(self.categorie_keys)
        except:
            return []

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

    def get_comments_by_page(self, index, psize):
        return self.comments().fetch(psize, offset=(index-1) * psize)

    @property
    def strtags(self):
        return ','.join(self.tags)

    @property
    def edit_url(self):
        return '/admin/%s?key=%s&action=edit'%(self.entrytype, self.key())

    def comments(self,order,ctype,count=0):
        if g_blog.comments_order:
            return Comment.all().filter('entry =', self).order('-date')
        else:
            return Comment.all().filter('entry =', self).order('date')

    def purecomments(self):
        if g_blog.comments_order:
            return Comment.all().filter('entry =', self).filter('ctype =', 0).order('-date')
        else:
            return Comment.all().filter('entry =', self).filter('ctype =', 0).order('date')

    def trackcomments(self):
        if g_blog.comments_order:
            return Comment.all().filter('entry =', self).filter('ctype IN', [1, 2]).order('-date')
        else:
            return Comment.all().filter('entry =', self).filter('ctype IN', [1, 2]).order('date')

    def commentsTops(self):
        return [c for c  in self.purecomments() if c.parent_key() == None]

    def delete_comments(self):
        cmts = Comment.all().filter('entry =', self)
        for comment in cmts:
            comment.delete()
        self.commentcount = 0
        self.trackbackcount = 0
    def update_commentno(self):
        cmts = Comment.all().filter('entry =', self).order('date')
        i = 1
        for comment in cmts:
            comment.no = i
            i += 1
            comment.store()

    def update_archive(self, cnt=1):
        """Checks to see if there is a month-year entry for the
        month of current blog, if not creates it and increments count"""
        my = self.date.strftime('%B %Y') # September-2008
        sy = self.date.strftime('%Y') #2008
        sm = self.date.strftime('%m') #09


        archive = Archive.all().filter('monthyear', my).get()
        if self.entrytype == 'post':
            if not archive:
                archive = Archive(monthyear=my, year=sy, month=sm, entrycount=1)
                self.monthyear = my
                archive.put()
            else:
                # ratchet up the count
                archive.entrycount += cnt
                archive.put()
        g_blog.entrycount += cnt
        g_blog.put()

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
        @is_pub:Check if need publish id
        """
        g_blog.tigger_action("pre_save_post", self, is_publish)
        my = self.date.strftime('%B %Y') # September 2008
        self.monthyear = my
        old_publish = self.published
        self.mod_date = datetime.now()

        if is_publish:
            if not self.is_wp:
                self.put()
                self.post_id = self.key().id()

            #fix for old version
            if not self.postname:
                self.setpostname(self.slug)


            vals = {'year':self.date.year, 'month':str(self.date.month).zfill(2), 'day':self.date.day,
                    'postname':self.postname, 'post_id':self.post_id}


            if self.entrytype == 'page':
                if self.slug:
                    self.link = self.postname
                else:
                    #use external page address as link
                    if self.is_external_page:
                        self.link = self.external_page_address
                    else:
                        self.link = g_blog.default_link_format%vals
            else:
                if g_blog.link_format and self.postname:
                    self.link = g_blog.link_format.strip()%vals
                else:
                    self.link = g_blog.default_link_format%vals

        self.published = is_publish
        self.put()

        if is_publish:
            if g_blog.sitemap_ping:
                Sitemap_NotifySearch()

        if old_publish and not is_publish:
            self.update_archive(-1)
        if not old_publish and is_publish:
            self.update_archive(1)

        self.removecache()

        self.put()
        g_blog.tigger_action("save_post", self, is_publish)




    def removecache(self):
        memcache.delete('/')
        memcache.delete('/'+self.link)
        memcache.delete('/sitemap')
        memcache.delete('blog.postcount')
        g_blog.tigger_action("clean_post_cache", self)

    @property
    def next(self):
        return Entry.all().filter('entrytype =', 'post').filter("published =", True).order('date').filter('date >', self.date).fetch(1)


    @property
    def prev(self):
        return Entry.all().filter('entrytype =', 'post').filter("published =", True).order('-date').filter('date <', self.date).fetch(1)

    @property
    def relateposts(self):
        if  self._relatepost:
            return self._relatepost
        else:
            if self.tags:
                self._relatepost = Entry.gql("WHERE published=True and tags IN :1 and post_id!=:2 order by post_id desc ", self.tags, self.post_id).fetch(5)
            else:
                self._relatepost = []
            return self._relatepost

    @property
    def trackbackurl(self):
        if self.link.find("?") > -1:
            return g_blog.baseurl+"/"+self.link+"&code="+str(self.key())
        else:
            return g_blog.baseurl+"/"+self.link+"?code="+str(self.key())

    def getbylink(self):
        pass

    def delete(self):
        g_blog.tigger_action("pre_delete_post", self)
        if self.published:
            self.update_archive(-1)
        self.delete_comments()
        db.Model.delete(self)
        g_blog.tigger_action("delete_post", self)


USER_LEVEL_AUTHOR=1
USER_LEVEL_ADMIN=3
class User(db.Model):
    #: db.UserProperty(required=False) - google user
    user = db.UserProperty(required=False)
    #: db.StringProperty() - display name
    dispname = db.StringProperty()
    #: db.StringProperty()
    email = db.StringProperty()
    #: db.LinkProperty()
    website = db.LinkProperty()



    #: User level.
    #:  * ``USER_LEVEL_AUTHOR=1``
    #:  * ``USER_LEVEL_ADMIN=3``
    level=db.IntegerProperty(default=USER_LEVEL_AUTHOR)
    password = db.StringProperty()

    def __unicode__(self):
        return self.dispname

    def __str__(self):
        return self.__unicode__().encode('utf-8')

    @property
    def isAdmin(self):
        return self.level & 2

    @property
    def isAuthor(self):
        return self.level & 1


MESSAGE_HOLD=0
MESSAGE_APPROVE=1
MESSAGE_SPAM=2
MESSAGE_TRASH=3

##class CommentEntry(db.Model):
##    """
##    The object which can be commented.
##    This class store the entry's comment count, title and url.
##    Use this entry's keyname as a unique comment entry key.
##    """
##    comment_entry_key=db.StringProperty()
##    count=db.IntegerProperty(default=0)
##    title=db.StringProperty()
##    link=db.StringProperty()

class Message(db.Model):
    """
    message object.

    ..  warning::
        In micolog 0.8. message don't belongs to any entry.
        Every thing can be messaged if it has a unique message entry key.
    """
    #: db.StringProperty() - The unique key of a message.
    message_entry_key=db.StringProperty()
    #: db.SelfReference() - Parent message.
    message_parent=db.SelfReference()
    #: db.DateTimeProperty(auto_now_add=True) - The date of the message created.
    date = db.DateTimeProperty(auto_now_add=True)
    #: db.TextProperty(required=True)- message content.
    content = db.TextProperty(required=True)
    #: db.StringProperty() - Author of this message.
    author = db.StringProperty()
    #: db.EmailProperty() - Email address
    email = db.EmailProperty()
    #: db.URLProperty() - Web url
    weburl = db.URLProperty()
    status = db.IntegerProperty(default=MESSAGE_APPROVE)
    """
    db.IntegerProperty(default=MESSAGE_APPROVE)

    Comment status:
        * MESSAGE_HOLD=0
        * MESSAGE_APPROVE=1
        * MESSAGE_SPAM=2
        * MESSAGE_TRASH=3
    """
    #: db.BooleanProperty(default=False)
    #: Whether need send mail to messageer when a reply occurred
    reply_notify_mail = db.BooleanProperty(default=False)
    #: db.StringProperty() - Ip address.
    ip = db.StringProperty()

##    #ctype = db.IntegerProperty(default=0)
##    """
##    db.IntegerProperty(default=MESSAGE_TYPE_NORMAL)
##
##    Comment Type.
##        * MESSAGE_TYPE_NORMAL = 0
##        * MESSAGE_TYPE_TRACKBACK = 1
##        * MESSAGE_TYPE_PINGBACK = 2
##    """

##    #: Comment No.
##    no = db.IntegerProperty(default=0)
##    Comment order.
##    message_order = db.IntegerProperty(default=1)
##
##    @property
##    def mpindex(self):
##        count = self.entry.messagecount
##        no = self.no
##        if g_blog.messages_order:
##            no = count-no+1
##        index = no / g_blog.messages_per_page
##        if no % g_blog.messages_per_page or no == 0:
##            index += 1
##        return index

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


##    def gravatar_url(self):
##
##        # Set your variables here
##        if g_blog.avatar_style == 0:
##            default = g_blog.baseurl+'/static/images/homsar.jpeg'
##        else:
##            default = 'identicon'
##
##        if not self.email:
##            return default
##
##        size = 50
##
##        try:
##            # construct the url
##            imgurl = "http://www.gravatar.com/avatar/"
##            imgurl += hashlib.md5(self.email.lower()).hexdigest()+"?"+ urllib.urlencode({
##                    'd':default, 's':str(size), 'r':'G'})
##
##            return imgurl
##        except:
##            return default

    def put(self):
        """
        Save message to db.
        """
        g_blog().tigger_action("pre_message", self)
        db.Model.put(self)
        g_blog().tigger_action("save_message", self)

    def delete(self):
        """
        Delete message.
        """
        db.Model.delete(self)
        g_blog.tigger_action("delete_message", self)

    @property
    def children(self):
        """Children messages."""
        messages = Message.all().filter("message_parent =",self)

    def store(self, **kwargs):
        """
        This method used by function pickle(). It make data simple.
        """
        rpc = datastore.GetRpcFromKwargs(kwargs)
        self._populate_internal_entity()
        return datastore.Put(self._entity, rpc=rpc)

class Media(db.Model):
    """
    Media object. Used to store files. Such as: gif,jpeg,txt ... and so on.
    """

    #: db.StringProperty() - name for media
    name = db.StringProperty()
    #: db.StringProperty() - media type. Such as ``image\jpeg`` ``image\gif``
    mtype = db.StringProperty()
    #: db.BlobProperty() - bits for media object.
    bits = db.BlobProperty()
    #: db.DateTimeProperty(auto_now_add=True) - media upload date.
    date = db.DateTimeProperty(auto_now_add=True)
    #: db.IntegerProperty(default=0) - download times of this media.
    download = db.IntegerProperty(default=0)

    @property
    def size(self):
        """
        Get media object size.
        """
        return len(self.bits)



class OptionSet(db.Model):
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

    name = db.StringProperty() #: db.StringProperty() - key name
    value = db.TextProperty() #: db.TextProperty() - key value

    @classmethod
    def getValue(cls, name, default=None):
        """
        Get value from db.
        """
        try:
            opt = OptionSet.get_by_key_name(name)
            return pickle.loads(str(opt.value))
        except:
            return default

    @classmethod
    def setValue(cls, name, value):
        """
        Save value to db.
        Args:
            name (str):  The name to use.
        """
        opt = OptionSet.get_or_insert(name)
        opt.name = name
        opt.value = pickle.dumps(value)
        opt.put()

    @classmethod
    def remove(cls, name):
        """
        Remove value form db.
        """
        opt = OptionSet.get_by_key_name(name)
        if opt:
            opt.delete()

##
##__current_blog=None
##def g_blog():
##    """
##    Global unique blog variable.
##    Only one blog instance can be created.
##    """
##    global __current_blog
##    if __current_blog==None:
##        key = "g_blog"
##        obj = memcache.get(key)
##        if obj is None:
##            obj = Blog.get_by_key_name('default')
##            if not obj:
##                obj = InitBlogData()
##            obj.rootdir = os.path.dirname(__file__)
##            obj.get_theme()
##            memcache.add(key, obj, 3600)
##        __current_blog=obj
##    return __current_blog
##
##def flush_g_blog():
##    memcache.remove("g_blog")
##    __current_blog=None
##
##def InitBlogData():
##    OptionSet.setValue('PluginActive', [u'googleAnalytics', u'wordpress', u'sys_plugin'])
##
##    blog = Blog(key_name='default')
##    blog.domain = os.environ['HTTP_HOST']
##    blog.baseurl = "http://"+g_blog.domain
##    blog.feedurl = g_blog.baseurl+"/feed"
##    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
##    lang = "zh-cn"
##    if os.environ.has_key('HTTP_ACCEPT_LANGUAGE'):
##        lang = os.environ['HTTP_ACCEPT_LANGUAGE'].split(',')[0]
##    from django.utils.translation import  activate, to_locale
##    blog.language = to_locale(lang)
##    from django.conf import settings
##    settings._target = None
##    activate(blog.language)
##    blog.save()
##
##    cate = Category(name=_("Uncategorized").decode('utf8'), slug=_("uncategorized").decode('utf8'))
##    cate.put()
##    entry = Entry(title=_("Hello world!").decode('utf8'))
##    entry.content = _('<p>Welcome to micolog. This is your first post. Edit or delete it, then start blogging!</p>').decode('utf8')
##    entry.categorie_keys = [cate.key()]
##    entry.save(True)
##    link = Link(href='http://xuming.net', linktext=_("Xuming's blog").decode('utf8'))
##    link.put()
##    return blog
##
