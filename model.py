import os,logging
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext.db import Model as DBModel
from datetime import datetime

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
			return (str(value), unicode(value))


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
    rpcpassowrd=db.StringProperty(default='mlog')
    description = db.TextProperty()
    baseurl = db.StringProperty(multiline=False,default='http://yourapp.appspot.com')
    urlpath = db.StringProperty(multiline=False)
    title = db.StringProperty(multiline=False,default='Mlog')
    subtitle = db.StringProperty(multiline=False,default='Your Blog Subtitle')
    entrycount = db.IntegerProperty(default=0)
    posts_per_page= db.IntegerProperty(default=10)
    feedurl = db.StringProperty(multiline=False,default='http://feeds.feedburner.com/yoursitesname')
    blogversion = db.StringProperty(multiline=False,default='1.00')
    theme_name = db.StringProperty(multiline=False,default='default')
    enable_memcache = db.BooleanProperty(default = False)
    link_format=db.StringProperty(multiline=False,default='%(year)s/%(month)s/%(day)s/%(postname)s.html')
    theme=None

    def save(self):
        self.put()

    def initialsetup(self):
        self.title = 'Your Blog Title'
        self.subtitle = 'Your Blog Subtitle'

    def get_theme(self):
        self.theme= Theme(self.theme_name);
        return self.theme


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

class Link(db.Model):
    href = db.StringProperty(multiline=False,default='')
    linktype = db.StringProperty(multiline=False,default='blogroll')
    linktext = db.StringProperty(multiline=False,default='')

class Entry(BaseModel):
    author = db.UserProperty()
    published = db.BooleanProperty(default=False)
    content = db.TextProperty(default='')
    title = db.StringProperty(multiline=False,default='')
    date = db.DateTimeProperty(auto_now_add=True)
    tags = db.StringListProperty()
    categorie_keys=db.ListProperty(db.Key)
    slug = db.StringProperty(multiline=False,default='')
    link= db.StringProperty(multiline=False,default='')
    monthyear = db.StringProperty(multiline=False)
    entrytype = db.StringProperty(multiline=False,default='post',choices=[
        'post','page'])
    entry_parent=db.IntegerProperty(default=0)#When level=0 show on main menu.
    menu_order=db.IntegerProperty()
    commentcount = db.IntegerProperty(default=0)

    #compatible with wordpress
    is_wp=db.BooleanProperty(default=False)
    post_id= db.IntegerProperty()





    def fullurl(self):
        return g_blog.baseurl+'/'+self.link;

    @property
    def categories(self):
        try:
            return db.get(self.categorie_keys)
        except:
            return []

##    def get_categories(self):
##        return ','.join([cate for cate in self.categories])
##
##    def set_categories(self, cates):
##        if cates:
##            catestemp = [db.Category(cate.strip()) for cate in cates.split(',')]
##            self.catesnew = [cate for cate in catestemp if not cate in self.categories]
##            self.categorie = tagstemp
##    scates = property(get_categories,set_categories)


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

            vals={'year':self.date.year,'month':str(self.date.month).zfill(2),'day':self.date.day,
                'postname':self.slug,'post_id':self.post_id}


            if self.entrytype=='page':
                if self.slug:
                    self.link=self.slug
                else:
                    self.link='?p=%(post_id)s'%vals
            else:
                if g_blog.link_format and self.slug:
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

class User(db.Model):
	user = db.UserProperty(required = True)
	dispname = db.StringProperty()
	website = db.LinkProperty()
	isadmin=db.BooleanProperty(default=False)

	def __unicode__(self):
		if self.dispname:
			return self.dispname
		else:
			return self.user.nickname()

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
    def save(self):
        self.entry.commentcount+=1
        self.entry.put()
        self.put()

    def delete(self):

        self.entry.commentcount-=1
        self.entry.put()
        self.delete()


#setting
g_blog=None
def gblog_init():
    logging.info('module setting reloaded')
    global g_blog
    g_blog = Blog.get_by_key_name('default')
    if not g_blog:
    	g_blog = Blog(key_name = 'default')

    g_blog.put()

    g_blog.get_theme()

    g_blog.rootdir=os.path.dirname(__file__)

    logging.info(g_blog.rootdir)
gblog_init()

