# -*- coding: utf-8 -*-
import os,logging
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext.db import Model as DBModel
from google.appengine.api import memcache
from google.appengine.api import mail
from google.appengine.api import urlfetch

from datetime import datetime
import urllib, hashlib,urlparse

logging.info('module base reloaded')

rootpath=os.path.dirname(__file__)

class Theme:
	def __init__(self, name='default'):
		self.name = name
		self.mapping_cache = {}
		self.dir = '/themes/%s' % name
		self.viewdir=os.path.join(rootpath, 'view')
		self.server_dir = os.path.join(rootpath, 'themes', self.name)
		logging.debug('server_dir:%s'%self.server_dir)

	def __getattr__(self, name):
	    if self.mapping_cache.has_key(name):
        	return self.mapping_cache[name]
	    else:
   	        path = os.path.join(self.server_dir, 'templates', name + '.html')
   	        logging.debug('path:%s'%path)
            if not os.path.exists(path):
        		path = os.path.join(rootpath, 'themes', 'default', 'templates', name + '.html')
        		if os.path.exists(path):
        			self.mapping_cache[name] = path
        			return path
            else:
        			self.mapping_cache[name] = path
        			return path
            return None


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
			return value
			#return (str(value), unicode(value))


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
        if (attrname.find('_') != 0):
            if hasattr(self,'_' + attrname):
                curval = getattr(self,'_' + attrname)
                if curval != value:
                    self.__isdirty = True
                    if hasattr(self,attrname + '_onchange'):
                        getattr(self,attrname + '_onchange')(curval,value)

        DBModel.__setattr__(self,attrname,value)

class Cache(db.Model):
    cachekey = db.StringProperty(multiline=False)
    content = db.TextProperty()

class Blog(db.Model):
    owner = db.UserProperty()
    author=db.StringProperty(default='admin')
    rpcuser=db.StringProperty(default='admin')
    rpcpassowrd=db.StringProperty(default='')
    description = db.TextProperty()
    baseurl = db.StringProperty(multiline=False,default=None)
    urlpath = db.StringProperty(multiline=False)
    title = db.StringProperty(multiline=False,default='Micolog')
    subtitle = db.StringProperty(multiline=False,default='This is a micro blog.')
    entrycount = db.IntegerProperty(default=0)
    posts_per_page= db.IntegerProperty(default=10)
    feedurl = db.StringProperty(multiline=False,default='/feed')
    blogversion = db.StringProperty(multiline=False,default='0.30')
    theme_name = db.StringProperty(multiline=False,default='default')
    enable_memcache = db.BooleanProperty(default = False)
    link_format=db.StringProperty(multiline=False,default='%(year)s/%(month)s/%(day)s/%(postname)s.html')
    comment_notify_mail=db.BooleanProperty(default=True)
    domain=db.StringProperty()
    show_excerpt=db.BooleanProperty(default=True)
    version=0.32
    timedelta=db.FloatProperty(default=8.0)# hours
    language=db.StringProperty(default="en-us")

    sitemap_entries=db.IntegerProperty(default=30)
    sitemap_include_category=db.BooleanProperty(default=False)
    sitemap_include_tag=db.BooleanProperty(default=False)
    sitemap_ping=db.BooleanProperty(default=False)




    theme=None

    #postcount=db.IntegerProperty(default=0)
    #pagecount=db.IntegerProperty(default=0)

    def save(self):
        self.put()

    def initialsetup(self):
        self.title = 'Your Blog Title'
        self.subtitle = 'Your Blog Subtitle'

    def get_theme(self):
        self.theme= Theme(self.theme_name);
        return self.theme

    def recentposts(self):
        return Entry.all().filter('entrytype =','post').order('-date').fetch(5)


class Category(db.Model):
    name=db.StringProperty(multiline=False)
    slug=db.StringProperty(multiline=False)
    @property
    def posts(self):
        return Entry.all().filter('entrytype =','post').filter('categorie_keys =',self)

    @property
    def count(self):
        return self.posts.count()


class Archive(db.Model):
    monthyear = db.StringProperty(multiline=False)
    """March-08"""
    entrycount = db.IntegerProperty(default=0)
    date = db.DateTimeProperty(auto_now_add=True)

class Tag(db.Model):
    tag = db.StringProperty(multiline=False)
    tagcount = db.IntegerProperty(default=0)
    @property
    def posts(self):
        return Entry.all('entrytype =','post').filter('tags =',self)

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
                else:
                    tag.delete()



class Link(db.Model):
    href = db.StringProperty(multiline=False,default='')
    linktype = db.StringProperty(multiline=False,default='blogroll')
    linktext = db.StringProperty(multiline=False,default='')
    createdate=db.DateTimeProperty(auto_now=True)

class Entry(BaseModel):
    author = db.UserProperty()
    published = db.BooleanProperty(default=False)
    content = db.TextProperty(default='')
    title = db.StringProperty(multiline=False,default='')
    date = db.DateTimeProperty(auto_now_add=True)
    tags = db.StringListProperty()#old version used
    categorie_keys=db.ListProperty(db.Key)
    slug = db.StringProperty(multiline=False,default='')
    link= db.StringProperty(multiline=False,default='')
    monthyear = db.StringProperty(multiline=False)
    entrytype = db.StringProperty(multiline=False,default='post',choices=[
        'post','page'])
    entry_parent=db.IntegerProperty(default=0)#When level=0 show on main menu.
    menu_order=db.IntegerProperty(default=0)
    commentcount = db.IntegerProperty(default=0)

    #compatible with wordpress
    is_wp=db.BooleanProperty(default=False)
    post_id= db.IntegerProperty()
    excerpt=db.StringProperty(multiline=True)
    postname=''
    _relatepost=None

    @property
    def content_excerpt(self):
        return self.get_content_excerpt(_('..more').decode('utf8'))

    def get_content_excerpt(self,more='..more'):
        if g_blog.show_excerpt:
            if self.excerpt:
                return self.excerpt+' <a href="%s">%s</a>'%(self.link,more)
            else:
                sc=self.content.split('<!--more-->')
                if len(sc)>1:
                    return sc[0]+u' <a href="%s">%s</a>'%(self.link,more)
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




    def fullurl(self):
        return g_blog.baseurl+'/'+self.link;

    @property
    def categories(self):
        try:
            return db.get(self.categorie_keys)
        except:
            return []

    def settags(self,values):
        if not values:return
        if type(values)==type([]):
            tags=values
        else:
            tags=values.split(',')
        logging.info('tags:   ok')



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
        self.tags=tags;


##    def get_categories(self):
##        return ','.join([cate for cate in self.categories])
##
##    def set_categories(self, cates):
##        if cates:
##            catestemp = [db.Category(cate.strip()) for cate in cates.split(',')]
##            self.catesnew = [cate for cate in catestemp if not cate in self.categories]
##            self.categorie = tagstemp
##    scates = property(get_categories,set_categories)
    @property
    def strtags(self):
        return ','.join(self.tags)

    @property
    def edit_url(self):
        return '/admin/%s?key=%s&action=edit'%(self.entrytype,self.key())

    def comments(self):
        return Comment.all().filter('entry =',self).order('date')

    def update_archive(self):
        """Checks to see if there is a month-year entry for the
        month of current blog, if not creates it and increments count"""
        my = self.date.strftime('%b-%Y') # May-2008
        archive = Archive.all().filter('monthyear',my).fetch(10)
        if self.entrytype == 'post':
            if archive == []:
                archive = Archive(monthyear=my)
                self.monthyear = my
                archive.put()
            else:
                # ratchet up the count
                archive[0].entrycount += 1
                archive[0].put()


    def save(self):
        """
        Use this instead of self.put(), as we do some other work here
        """


        my = self.date.strftime('%b-%Y') # May-2008
        self.monthyear = my



        return self.put()

    def publish(self,newval=True):
        if newval:

            if not self.is_saved():
                self.save()

            if not self.is_wp:
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
                    self.link='?p=%(post_id)s'%vals
            else:
                if g_blog.link_format and self.postname:
                    self.link=g_blog.link_format.strip()%vals
                else:
                    self.link='?p=%(post_id)s'%vals



            if not self.published:
                 g_blog.entrycount+=1
            self.published=True

            g_blog.save()
            self.save()
        else:
            self.published=false
            if self.published:
                g_blog.entrycount-=1
            g_blog.save()
            self.save()
        self.removecache()
        if g_blog.sitemap_ping:
            Sitemap_NotifySearch()

    def removecache(self):
        memcache.delete('/')
        memcache.delete('/'+self.link)
        memcache.delete('/sitemap')

    @property
    def next(self):
        logging.info('test______________')
        return Entry.all().filter('entrytype =','post').order('post_id').filter('post_id >',self.post_id).fetch(1)


    @property
    def prev(self):
        return Entry.all().filter('entrytype =','post').order('-post_id').filter('post_id <',self.post_id).fetch(1)

    @property
    def relateposts(self):
        if  self._relatepost:
            return self._relatepost
        else:
            if self.tags:
                self._relatepost= Entry.gql("WHERE tags IN :1 and post_id!=:2 order by post_id desc ",self.tags,self.post_id).fetch(5)
            else:
                self._relatepost= []
            return self._relatepost

class User(db.Model):
	user = db.UserProperty(required = False)
	dispname = db.StringProperty()
	email=db.StringProperty()
	website = db.LinkProperty()
	isadmin=db.BooleanProperty(default=False)
	isAuthor=db.BooleanProperty(default=True)
	rpcpwd=db.StringProperty()

	def __unicode__(self):
		#if self.dispname:
			return self.dispname
		#else:
		#	return self.user.nickname()

	def __str__(self):
		return self.__unicode__().encode('utf-8')

class Comment(db.Model):
    entry = db.ReferenceProperty(Entry)
    date = db.DateTimeProperty(auto_now_add=True)
    content = db.TextProperty(required=True)
    author=db.StringProperty()
    email=db.EmailProperty()
    weburl=db.URLProperty()
    status=db.IntegerProperty(default=0)

    @property
    def shortcontent(self,len=20):
        return self.content[:len]

    def gravatar_url(self):

        # Set your variables here
        default = g_blog.baseurl+'/static/images/homsar.jpeg'
        if not self.email:
            return default

        size = 50

        # construct the url
        imgurl = "http://www.gravatar.com/avatar/"
        imgurl +=hashlib.md5(self.email).hexdigest()+"?"+ urllib.urlencode({
        	'd':default, 's':str(size),'r':'G'})
        return imgurl


    def save(self):


        self.put()
        self.entry.commentcount+=1
        self.entry.put()
        memcache.delete("/"+self.entry.link)
        sbody=_('''New comment on your post "%s"
Author : %s
E-mail : %s
URL    : %s
Comment:
%s
You can see all comments on this post here:
%s
''')
        if g_blog.comment_notify_mail and g_blog.owner and not users.is_current_user_admin() :
            sbody=sbody%(self.entry.title,self.author,self.email,self.weburl,self.content,
            g_blog.baseurl+"/"+self.entry.link+"#comment-"+str(self.key().id()))
            mail.send_mail_to_admins(g_blog.owner.email(),'Comments:'+self.entry.title, sbody,reply_to=self.email)
            logging.info('send %s . entry: %s'%(g_blog.owner.email(),self.entry.title))

    def delit(self):

        self.entry.commentcount-=1
        self.entry.put()
        self.delete()

class Media(db.Model):
   name =db.StringProperty()
   mtype=db.StringProperty()
   bits=db.BlobProperty()
   date=db.DateTimeProperty(auto_now_add=True)


NOTIFICATION_SITES = [
  ('http', 'www.google.com', 'webmasters/sitemaps/ping', {}, '', 'sitemap')
  ]




def Sitemap_NotifySearch():
    """ Send notification of the new Sitemap(s) to the search engines. """


    url=g_blog.baseurl+"/sitemap"

    # Cycle through notifications
    # To understand this, see the comment near the NOTIFICATION_SITES comment
    for ping in NOTIFICATION_SITES:
      query_map             = ping[3]
      query_attr            = ping[5]
      query_map[query_attr] = url
      query = urllib.urlencode(query_map)
      notify = urlparse.urlunsplit((ping[0], ping[1], ping[2], query, ping[4]))

      # Send the notification
      logging.info('Notifying search engines. %s'%ping[1])
      logging.info('url: %s'%notify)

      try:
        urlfetch.fetch(notify)

      except :
        logging.error('Cannot contact: %s' % ping[1])

g_blog=None
def InitBlogData():
    import settings
    global g_blog
    g_blog = Blog(key_name = 'default')
    g_blog.domain=os.environ['HTTP_HOST']
    g_blog.baseurl="http://"+g_blog.domain
    g_blog.feedurl=g_blog.baseurl+"/feed"
    g_blog.language=settings.LANGUAGE_CODE
    g_blog.save()
    entry=Entry(title=_("Hello world!").decode('utf8'))
    entry.content=_('<p>Welcome to micolog. This is your first post. Edit or delete it, then start blogging!</p>').decode('utf8')
    entry.publish()

def gblog_init():
    logging.info('module setting reloaded')
    global g_blog

    g_blog = Blog.get_by_key_name('default')
    if not g_blog:
        g_blog=InitBlogData()



    g_blog.get_theme()

    g_blog.rootdir=os.path.dirname(__file__)

    logging.info(g_blog.rootdir)

gblog_init()




