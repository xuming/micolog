# -*- coding: utf-8 -*-
import os,logging
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from google.appengine.dist import use_library
use_library('django', '1.2')
from google.appengine.ext import db
from google.appengine.ext.db import Model as DBModel
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import datastore
from datetime import datetime
import urllib, hashlib,urlparse
import re,pickle
logging.info('module base reloaded')
from django.utils.translation import ugettext as _
rootpath=os.path.dirname(__file__)

def vcache(key="",time=3600):
    def _decorate(method):
        def _wrapper(*args, **kwargs):
            if not g_blog.enable_memcache:
                return method(*args, **kwargs)
            result=method(*args, **kwargs)
            memcache.set(key,result,time)
            return result
        return _wrapper
    return _decorate

class Theme:
    def __init__(self, name='default'):
        self.name = name
        self.mapping_cache = {}
        self.dir = '/themes/%s' % name
        self.viewdir=os.path.join(rootpath, 'view')
        self.server_dir = os.path.join(rootpath, 'themes',self.name)
        if os.path.exists(self.server_dir):
            self.isZip=False
        else:
            self.isZip=True
            self.server_dir += ".zip"
        #self.server_dir=os.path.join(self.server_dir,"templates")
        logging.debug('server_dir:%s'%self.server_dir)

    def __getattr__(self, name):
        if self.mapping_cache.has_key(name):
            return self.mapping_cache[name]
        else:
            path ="/".join((self.name,'templates', name + '.html'))
            logging.debug('path:%s'%path)
##			if not os.path.exists(path):
##				path = os.path.join(rootpath, 'themes', 'default', 'templates', name + '.html')
##				if not os.path.exists(path):
##					path = None
            self.mapping_cache[name]=path
            return path

class ThemeIterator:
    def __init__(self, theme_path='themes'):
        self.iterating = False
        self.theme_path = theme_path
        self.list = []

    def __iter__(self):
        return self

    def next(self):
        if not self.iterating:
            self.iterating = True
            self.list = os.listdir(self.theme_path)
            self.cursor = 0

        if self.cursor >= len(self.list):
            self.iterating = False
            raise StopIteration
        else:
            value = self.list[self.cursor]
            self.cursor += 1
            if value.endswith('.zip'):
                value=value[:-4]
            return value
            #return (str(value), unicode(value))

class LangIterator:
    def __init__(self,path='locale'):
        self.iterating = False
        self.path = path
        self.list = []
        for value in  os.listdir(self.path):
                if os.path.isdir(os.path.join(self.path,value)):
                    if os.path.exists(os.path.join(self.path,value,'LC_MESSAGES')):
                        try:
                            lang=open(os.path.join(self.path,value,'language')).readline()
                            self.list.append({'code':value,'lang':lang})
                        except:
                            self.list.append({'code':value,'lang':value})

    def __iter__(self):
        return self

    def next(self):
        if not self.iterating:
            self.iterating = True
            self.cursor = 0

        if self.cursor >= len(self.list):
            self.iterating = False
            raise StopIteration
        else:
            value = self.list[self.cursor]
            self.cursor += 1
            return value

    def getlang(self,language):
        from django.utils.translation import  to_locale
        for item in self.list:
            if item['code']==language or item['code']==to_locale(language):
                return item
        return {'code':'en_US','lang':'English'}

class BaseModel(db.Model):
    def __init__(self, parent=None, key_name=None, _app=None, **kwds):
        self.__isdirty = False
        DBModel.__init__(self, parent=None, key_name=None, _app=None, **kwds)

    def __setattr__(self,attrname,value):
        """
        DataStore api stores all prop values say "email" is stored in "_email" so
        we intercept the set attribute, see if it has changed, then check for an
        onchanged method for that property to call
        """
        if attrname.find('_') != 0:
            if hasattr(self,'_' + attrname):
                curval = getattr(self,'_' + attrname)
                if curval != value:
                    self.__isdirty = True
                    if hasattr(self,attrname + '_onchange'):
                        getattr(self,attrname + '_onchange')(curval,value)
        DBModel.__setattr__(self,attrname,value)

class Cache(db.Model):
    cachekey = db.StringProperty()
    content = db.TextProperty()

class Blog(db.Model):
    owner = db.UserProperty()
    author=db.StringProperty(default='admin')
    rpcuser=db.StringProperty(default='admin')
    rpcpassword=db.StringProperty(default='')
    description = db.TextProperty()
    baseurl = db.StringProperty(default=None)
    urlpath = db.StringProperty()
    title = db.StringProperty(default='Micolog')
    subtitle = db.StringProperty(default='This is a micro blog.')
    entrycount = db.IntegerProperty(default=0)
    posts_per_page= db.IntegerProperty(default=10)
    feedurl = db.StringProperty(default='/feed')
    blogversion = db.StringProperty(default='0.30')
    theme_name = db.StringProperty(default='default')
    enable_memcache = db.BooleanProperty(default = False)
    link_format=db.StringProperty(default='%(year)s/%(month)s/%(day)s/%(postname)s.html')
    comment_notify_mail=db.BooleanProperty(default=True)
    #评论顺序
    comments_order=db.IntegerProperty(default=0)
    #每页评论数
    comments_per_page=db.IntegerProperty(default=20)
    #comment check type 0-No 1-算术 2-验证码 3-客户端计算
    comment_check_type=db.IntegerProperty(default=1)
    #0 default 1 identicon
    avatar_style=db.IntegerProperty(default=0)
    blognotice=db.TextProperty(default='')
    domain=db.StringProperty()
    show_excerpt=db.BooleanProperty(default=True)
    version=0.743
    timedelta=db.FloatProperty(default=8.0)# hours
    language=db.StringProperty(default="en-us")
    sitemap_entries=db.IntegerProperty(default=30)
    sitemap_include_category=db.BooleanProperty(default=False)
    sitemap_include_tag=db.BooleanProperty(default=False)
    sitemap_ping=db.BooleanProperty(default=False)
    default_link_format=db.StringProperty(default='?p=%(post_id)s')
    default_theme=Theme()
    allow_pingback=db.BooleanProperty(default=False)
    allow_trackback=db.BooleanProperty(default=False)
    admin_essential=db.BooleanProperty(default=False)
    theme=None
    langs=None
    application=None

    def __init__(self,
               parent=None,
               key_name=None,
               _app=None,
               _from_entity=False,
               **kwds):
        from micolog_plugin import Plugins
        self.plugins=Plugins(self)
        db.Model.__init__(self,parent,key_name,_app,_from_entity,**kwds)

    def tigger_filter(self,name,content,*arg1,**arg2):
        return self.plugins.tigger_filter(name,content,blog=self,*arg1,**arg2)

    def tigger_action(self,name,*arg1,**arg2):
        return self.plugins.tigger_action(name,blog=self,*arg1,**arg2)

    def tigger_urlmap(self,url,*arg1,**arg2):
        return self.plugins.tigger_urlmap(url,blog=self,*arg1,**arg2)

    def get_ziplist(self):
        return self.plugins.get_ziplist();

    def save(self):
        self.put()

    def get_theme(self):
        self.theme= Theme(self.theme_name);
        return self.theme

    def get_langs(self):
        self.langs=LangIterator()
        return self.langs

    def cur_language(self):
        return self.get_langs().getlang(self.language)

    def rootpath(self):
        return rootpath

    @vcache("blog.hotposts")
    def hotposts(self):
        return Entry.all().filter('entrytype =','post').filter("published =", True).order('-readtimes').fetch(7)

    @vcache("blog.recentposts")
    def recentposts(self):
        return Entry.all().filter('entrytype =','post').filter("published =", True).order('-date').fetch(7)

    @vcache("blog.postscount")
    def postscount(self):
        return Entry.all().filter('entrytype =','post').filter("published =", True).order('-date').count()

class Category(db.Model):
    uid=db.IntegerProperty()
    name=db.StringProperty()
    slug=db.StringProperty()
    parent_cat=db.SelfReferenceProperty()
    @property
    def posts(self):
        return Entry.all().filter('entrytype =','post').filter("published =", True).filter('categorie_keys =',self)

    @property
    def count(self):
        return self.posts.count()

    def put(self):
        db.Model.put(self)
        g_blog.tigger_action("save_category",self)

    def delete(self):
        for entry in Entry.all().filter('categorie_keys =',self):
            entry.categorie_keys.remove(self.key())
            entry.put()
        for cat in Category.all().filter('parent_cat =',self):
            cat.delete()
        db.Model.delete(self)
        g_blog.tigger_action("delete_category",self)

    def ID(self):
        try:
            id=self.key().id()
            if id:
                return id
        except:
            pass

        if self.uid :
            return self.uid
        else:
            #旧版本Category没有ID,为了与wordpress兼容
            from random import randint
            uid=randint(0,99999999)
            cate=Category.all().filter('uid =',uid).get()
            while cate:
                uid=randint(0,99999999)
                cate=Category.all().filter('uid =',uid).get()
            self.uid=uid
            print uid
            self.put()
            return uid

    @classmethod
    def get_from_id(cls,id):
        cate=Category.get_by_id(id)
        if cate:
            return cate
        else:
            cate=Category.all().filter('uid =',id).get()
            return cate

    @property
    def children(self):
        key=self.key()
        return [c for c in Category.all().filter('parent_cat =',self)]


    @classmethod
    def allTops(self):
        return [c for c in Category.all() if not c.parent_cat]

class Archive(db.Model):
    monthyear = db.StringProperty()
    year = db.StringProperty()
    month = db.StringProperty()
    entrycount = db.IntegerProperty(default=0)
    date = db.DateTimeProperty(auto_now_add=True)

class Tag(db.Model):
    tag = db.StringProperty()
    tagcount = db.IntegerProperty(default=0)
    @property
    def posts(self):
        return Entry.all('entrytype =','post').filter("published =", True).filter('tags =',self)

    @classmethod
    def add(cls,value):
        if value:
            tag= Tag.get_by_key_name(value)
            if not tag:
                tag=Tag(key_name=value)
                tag.tag=value

            tag.tagcount+=1
            tag.put()
            return tag
        else:
            return None

    @classmethod
    def remove(cls,value):
        if value:
            tag= Tag.get_by_key_name(value)
            if tag:
                if tag.tagcount>1:
                    tag.tagcount-=1
                    tag.put()
                else:
                    tag.delete()

class Link(db.Model):
    href = db.StringProperty(default='')
    linktype = db.StringProperty(default='blogroll')
    linktext = db.StringProperty(default='')
    linkcomment = db.StringProperty(default='')
    createdate=db.DateTimeProperty(auto_now=True)

    @property
    def get_icon_url(self):
        """get ico url of the wetsite"""
        ico_path = '/favicon.ico'
        ix = self.href.find('/',len('http://') )
        return (ix>0 and self.href[:ix] or self.href ) + ico_path

    def put(self):
        db.Model.put(self)
        g_blog.tigger_action("save_link",self)


    def delete(self):
        db.Model.delete(self)
        g_blog.tigger_action("delete_link",self)

class Entry(BaseModel):
    author = db.UserProperty()
    author_name = db.StringProperty()
    published = db.BooleanProperty(default=False)
    content = db.TextProperty(default='')
    readtimes = db.IntegerProperty(default=0)
    title = db.StringProperty(default='')
    date = db.DateTimeProperty(auto_now_add=True)
    mod_date = db.DateTimeProperty(auto_now_add=True)
    tags = db.StringListProperty()
    categorie_keys=db.ListProperty(db.Key)
    slug = db.StringProperty(default='')
    link= db.StringProperty(default='')
    monthyear = db.StringProperty()
    entrytype = db.StringProperty(default='post',choices=[
        'post','page'])
    entry_parent=db.IntegerProperty(default=0)       #When level=0 show on main menu.
    menu_order=db.IntegerProperty(default=0)
    commentcount = db.IntegerProperty(default=0)
    trackbackcount = db.IntegerProperty(default=0)

    allow_comment = db.BooleanProperty(default=True) #allow comment
    #allow_pingback=db.BooleanProperty(default=False)
    allow_trackback=db.BooleanProperty(default=True)
    password=db.StringProperty()

    #compatible with wordpress
    is_wp=db.BooleanProperty(default=False)
    post_id= db.IntegerProperty()
    excerpt=db.StringProperty(multiline=True)

    #external page
    is_external_page=db.BooleanProperty(default=False)
    target=db.StringProperty(default="_self")
    external_page_address=db.StringProperty()

    #keep in top
    sticky=db.BooleanProperty(default=False)

    postname=''
    _relatepost=None

    @property
    def content_excerpt(self):
        return self.get_content_excerpt(_('..more'))

    def get_author_user(self):
        if not self.author:
            self.author=g_blog.owner
        return User.all().filter('email =',self.author.email()).get()

    def get_content_excerpt(self,more='..more'):
        if g_blog.show_excerpt:
            if self.excerpt:
                return self.excerpt+' <a href="/%s">%s</a>'%(self.link,more)
            else:
                sc=self.content.split('<!--more-->')
                if len(sc)>1:
                    return sc[0]+u' <a href="/%s">%s</a>'%(self.link,more)
                else:
                    return sc[0]
        else:
            return self.content

    def slug_onchange(self,curval,newval):
        if not (curval==newval):
            self.setpostname(newval)

    def setpostname(self,newval):
             #check and fix double slug
            if newval:
                slugcount=Entry.all()\
                          .filter('entrytype',self.entrytype)\
                          .filter('date <',self.date)\
                          .filter('slug =',newval)\
                          .filter('published',True)\
                          .count()
                if slugcount>0:
                    self.postname=newval+str(slugcount)
                else:
                    self.postname=newval
            else:
                self.postname=""

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

    def settags(self,values):
        if not values:tags=[]
        if type(values)==type([]):
            tags=values
        else:
            tags=values.split(',')

        if not self.tags:
            removelist=[]
            addlist=tags
        else:
            #search different  tags
            removelist=[n for n in self.tags if n not in tags]
            addlist=[n for n in tags if n not in self.tags]
        for v in removelist:
            Tag.remove(v)
        for v in addlist:
            Tag.add(v)
        self.tags=tags

    def get_comments_by_page(self,index,psize):
        return self.comments().fetch(psize,offset = (index-1) * psize)

    @property
    def strtags(self):
        return ','.join(self.tags)

    @property
    def edit_url(self):
        return '/admin/%s?key=%s&action=edit'%(self.entrytype,self.key())

    def comments(self):
        if g_blog.comments_order:
            return Comment.all().filter('entry =',self).order('-date')
        else:
            return Comment.all().filter('entry =',self).order('date')

    def purecomments(self):
        if g_blog.comments_order:
            return Comment.all().filter('entry =',self).filter('ctype =',0).order('-date')
        else:
            return Comment.all().filter('entry =',self).filter('ctype =',0).order('date')

    def trackcomments(self):
        if g_blog.comments_order:
            return Comment.all().filter('entry =',self).filter('ctype IN',[1,2]).order('-date')
        else:
            return Comment.all().filter('entry =',self).filter('ctype IN',[1,2]).order('date')
    def commentsTops(self):
        return [c for c  in self.purecomments() if c.parent_key()==None]

    def delete_comments(self):
        cmts = Comment.all().filter('entry =',self)
        for comment in cmts:
            comment.delete()
        self.commentcount = 0
        self.trackbackcount = 0
    def update_commentno(self):
        cmts = Comment.all().filter('entry =',self).order('date')
        i=1
        for comment in cmts:
            if comment.no != i:
                comment.no = i
                comment.store()
            i+=1

    def update_archive(self,cnt=1):
        """Checks to see if there is a month-year entry for the
        month of current blog, if not creates it and increments count"""
        my = self.date.strftime('%B %Y') # September-2008
        sy = self.date.strftime('%Y') #2008
        sm = self.date.strftime('%m') #09


        archive = Archive.all().filter('monthyear',my).get()
        if self.entrytype == 'post':
            if not archive:
                archive = Archive(monthyear=my,year=sy,month=sm,entrycount=1)
                self.monthyear = my
                archive.put()
            else:
                # ratchet up the count
                archive.entrycount += cnt
                archive.put()
        g_blog.entrycount+=cnt
        g_blog.put()


    def save(self,is_publish=False):
        """
        Use this instead of self.put(), as we do some other work here
        @is_pub:Check if need publish id
        """
        g_blog.tigger_action("pre_save_post",self,is_publish)
        my = self.date.strftime('%B %Y') # September 2008
        self.monthyear = my
        old_publish=self.published
        self.mod_date=datetime.now()

        if is_publish:
            if not self.is_wp:
                self.put()
                self.post_id=self.key().id()

            #fix for old version
            if not self.postname:
                self.setpostname(self.slug)


            vals={'year':self.date.year,'month':str(self.date.month).zfill(2),'day':self.date.day,
                'postname':self.postname,'post_id':self.post_id}


            if self.entrytype=='page':
                if self.slug:
                    self.link=self.postname
                else:
                    #use external page address as link
                    if self.is_external_page:
                       self.link=self.external_page_address
                    else:
                       self.link=g_blog.default_link_format%vals
            else:
                if g_blog.link_format and self.postname:
                    self.link=g_blog.link_format.strip()%vals
                else:
                    self.link=g_blog.default_link_format%vals

        self.published=is_publish
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
        g_blog.tigger_action("save_post",self,is_publish)

    def removecache(self):
        memcache.delete('/')
        memcache.delete('/'+self.link)
        memcache.delete('/sitemap')
        memcache.delete('blog.postcount')
        g_blog.tigger_action("clean_post_cache",self)

    @property
    def next(self):
        return Entry.all().filter('entrytype =','post').filter("published =", True).order('date').filter('date >',self.date).fetch(1)


    @property
    def prev(self):
        return Entry.all().filter('entrytype =','post').filter("published =", True).order('-date').filter('date <',self.date).fetch(1)

    @property
    def relateposts(self):
        if  self._relatepost:
            return self._relatepost
        else:
            if self.tags:
                try: self._relatepost= Entry.gql("WHERE published=True and tags IN :1 and post_id!=:2 order by post_id desc ",self.tags,self.post_id).fetch(5)
                except: self._relatepost= []
            else:
                self._relatepost= []
            return self._relatepost

    @property
    def trackbackurl(self):
        if self.link.find("?")>-1:
            return g_blog.baseurl+"/"+self.link+"&code="+str(self.key())
        else:
            return g_blog.baseurl+"/"+self.link+"?code="+str(self.key())

    def getbylink(self):
        pass

    def delete(self):
        g_blog.tigger_action("pre_delete_post",self)
        if self.published:
            self.update_archive(-1)
        self.delete_comments()
        db.Model.delete(self)
        g_blog.tigger_action("delete_post",self)


class User(db.Model):
    user = db.UserProperty(required = False)
    dispname = db.StringProperty()
    email=db.StringProperty()
    website = db.LinkProperty()
    isadmin=db.BooleanProperty(default=False)
    isAuthor=db.BooleanProperty(default=True)
    #rpcpwd=db.StringProperty()

    def __unicode__(self):
        #if self.dispname:
            return self.dispname
        #else:
        #	return self.user.nickname()

    def __str__(self):
        return self.__unicode__().encode('utf-8')

COMMENT_NORMAL=0
COMMENT_TRACKBACK=1
COMMENT_PINGBACK=2
class Comment(db.Model):
    entry = db.ReferenceProperty(Entry)
    date = db.DateTimeProperty(auto_now_add=True)
    content = db.TextProperty(required=True)
    author=db.StringProperty()
    email=db.EmailProperty()
    weburl=db.URLProperty()
    status=db.IntegerProperty(default=0)
    reply_notify_mail=db.BooleanProperty(default=False)
    ip=db.StringProperty()
    ctype=db.IntegerProperty(default=COMMENT_NORMAL)
    no=db.IntegerProperty(default=0)
    comment_order=db.IntegerProperty(default=1)

    @property
    def mpindex(self):
        count=self.entry.commentcount
        no=self.no
        if g_blog.comments_order:
            no=count-no+1
        index=no / g_blog.comments_per_page
        if no % g_blog.comments_per_page or no==0:
            index+=1
        return index

    @property
    def shortcontent(self,len=20):
        scontent=self.content
        scontent=re.sub(r'<br\s*/>',' ',scontent)
        scontent=re.sub(r'<[^>]+>','',scontent)
        scontent=re.sub(r'(@[\S]+)-\d{2,7}',r'\1:',scontent)
        return scontent[:len].replace('<','&lt;').replace('>','&gt;')


    def gravatar_url(self):
        # Set your variables here
        if g_blog.avatar_style==0:
            default = g_blog.baseurl+'/static/images/homsar.jpeg'
        else:
            default='identicon'

        if not self.email:
            return default

        size = 50

        try:
            # construct the url
            imgurl = "http://www.gravatar.com/avatar/"
            imgurl +=hashlib.md5(self.email.lower()).hexdigest()+"?"+ urllib.urlencode({
                'd':default, 's':str(size),'r':'G'})
            return imgurl
        except:
            return default

    def save(self):
        self.put()
        self.comment_order=self.entry.commentcount
        self.entry.commentcount+=1
        if (self.ctype == COMMENT_TRACKBACK) or (self.ctype == COMMENT_PINGBACK):
            self.entry.trackbackcount+=1
        self.entry.put()
        memcache.delete("/"+self.entry.link)
        return True

    def delit(self):
        self.entry.commentcount-=1
        if self.entry.commentcount<0:
            self.entry.commentcount = 0
        if (self.ctype == COMMENT_TRACKBACK) or (self.ctype == COMMENT_PINGBACK):
            self.entry.trackbackcount-=1
        if self.entry.trackbackcount<0:
            self.entry.trackbackcount = 0
        self.entry.put()
        self.delete()

    def put(self):
        g_blog.tigger_action("pre_comment",self)
        db.Model.put(self)
        g_blog.tigger_action("save_comment",self)

    def delete(self):
        db.Model.delete(self)
        g_blog.tigger_action("delete_comment",self)

    @property
    def children(self):
        key=self.key()
        comments=Comment.all().ancestor(self)
        return [c for c in comments if c.parent_key()==key]

    def store(self, **kwargs):
        rpc = datastore.GetRpcFromKwargs(kwargs)
        self._populate_internal_entity()
        return datastore.Put(self._entity, rpc=rpc)

class Media(db.Model):
    name =db.StringProperty()
    mtype=db.StringProperty()
    bits=db.BlobProperty()
    date=db.DateTimeProperty(auto_now_add=True)
    download=db.IntegerProperty(default=0)

    @property
    def size(self):
        return len(self.bits)

class OptionSet(db.Model):
    name=db.StringProperty()
    value=db.TextProperty()
    #blobValue=db.BlobProperty()
    #isBlob=db.BooleanProperty()

    @classmethod
    def getValue(cls,name,default=None):
        try:
            opt=OptionSet.get_by_key_name(name)
            return pickle.loads(str(opt.value))
        except:
            return default

    @classmethod
    def setValue(cls,name,value):
        opt=OptionSet.get_or_insert(name)
        opt.name=name
        opt.value=pickle.dumps(value)
        opt.put()

    @classmethod
    def remove(cls,name):
        opt= OptionSet.get_by_key_name(name)
        if opt:
            opt.delete()

NOTIFICATION_SITES = [
  ('http', 'www.google.com', 'webmasters/sitemaps/ping', {}, '', 'sitemap')
  ]


def Sitemap_NotifySearch():
    """ Send notification of the new Sitemap(s) to the search engines. """


    url=g_blog.baseurl+"/sitemap"

    # Cycle through notifications
    # To understand this, see the comment near the NOTIFICATION_SITES comment
    for ping in NOTIFICATION_SITES:
      query_map			 = ping[3]
      query_attr			= ping[5]
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

def InitBlogData():
    global g_blog
    OptionSet.setValue('PluginActive',[u'googleAnalytics', u'wordpress', u'sys_plugin'])

    g_blog = Blog(key_name = 'default')
    g_blog.domain=os.environ['HTTP_HOST']
    g_blog.baseurl="http://"+g_blog.domain
    g_blog.feedurl=g_blog.baseurl+"/feed"
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    g_blog.admin_essential = False
    if os.environ.has_key('HTTP_ACCEPT_LANGUAGE'):
        lang=os.environ['HTTP_ACCEPT_LANGUAGE'].split(',')[0]
    from django.utils.translation import  activate,to_locale
    g_blog.language=to_locale(lang)
    g_blog.admin_essential=False
    from django.conf import settings
    settings._target = None
    activate(g_blog.language)
    g_blog.save()

    entry=Entry(title="Hello world!".decode('utf8'))
    entry.content='<p>Welcome to micolog %s. This is your first post. Edit or delete it, then start blogging!</p>'%g_blog.version
    entry.save(True)
    link=Link(href='http://xuming.net',linktext="Xuming's blog".decode('utf8'))
    link.put()
    link=Link(href='http://eric.cloud-mes.com/',linktext="Eric Guo's blog".decode('utf8'))
    link.put()
    return g_blog

def gblog_init():
    global g_blog
    try:
       if g_blog :
           return g_blog
    except:
        pass
    g_blog = Blog.get_by_key_name('default')
    if not g_blog:
        g_blog=InitBlogData()

    g_blog.get_theme()
    g_blog.rootdir=os.path.dirname(__file__)
    return g_blog

try:
    g_blog=gblog_init()

    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    from django.utils.translation import activate
    from django.conf import settings
    settings._target = None
    activate(g_blog.language)
except:
    pass



