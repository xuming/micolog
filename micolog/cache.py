# -*- coding: utf-8 -*-
###################################################
#this file is under GPL v3 license
#Author: Rex  fdrex1987@gmail.com
#the code of format_date is from Micolog's code
##################################################
import logging
import pickle
import settings
from google.appengine.ext import db
from google.appengine.api import memcache
from datetime import datetime,timedelta

class ObjCache(db.Model):
    ###缓存值
    value = db.BlobProperty()
    ###标签
    tags = db.StringListProperty()
    ###是否只是缓存在内存中
    mem_only=db.BooleanProperty(default=False)
    ###缓存时间
    cachetime = db.DateTimeProperty(auto_now=True)
    ###过期时间
    overtime=db.DateTimeProperty()
    ###过期秒数
    time=db.IntegerProperty()

    ###缓存Key
    @property
    def cache_key(self):
        return self.key().name()

    def invalidate(self):
        logging.debug('ObjCache invalidate called: ' + self.cache_key)
        memcache.delete(self.cache_key)
        self.delete()

    def update(self, new_value_obj):
        logging.debug('ObjCache update called: ' + self.cache_key)
        memcache.set(self.cache_key,new_value_obj)
        if not self.mem_only:
            self.cachetime=datetime.now()
            self.overtime=self.cachetime+timedelta(0,self.time)
            self.value = pickle.dumps(new_value_obj)
            self.put()

    @staticmethod
    def get_cache_value(key_name,mem_only=False):
        result = memcache.get(key_name)
        if mem_only:
            logging.debug("mem_only.")
            return result

        if result is not None:
            logging.debug("Find cache value of "+key_name+" in memcache.")
            return result
        try:
            result =ObjCache.get_by_key_name(key_name)#  ObjCache.all().filter('cache_key =',key_name).get()
            if result is not None:
                if result.overtime<datetime.now():
                    logging.debug("ObjCache "+key_name+"is overtime.")
                    return None
                logging.debug("Find cache value of "+key_name+" in ObjCache.")
                return pickle.loads(result.value)
            else:
                return None
        except Exception, e:
            logging.error(e.message)
            return None

##    @staticmethod
##    def update_basic_info(
##        update_categories=False,
##        update_tags=False,
##        update_links=False,
##        update_comments=False,
##        update_archives=False,
##        update_pages=False):
##
##        from model import Entry,Archive,Comment,Category,Tag,Link
##        basic_info = ObjCache.get(is_basicinfo=True)
##        if basic_info is not None:
##            info = ObjCache.get_cache_value(basic_info.cache_key)
##            if update_pages:
##                info['menu_pages'] = Entry.all().filter('entrytype =','page')\
##                            .filter('published =',True)\
##                            .filter('entry_parent =',0)\
##                            .order('menu_order').fetch(limit=1000)
##            if update_archives:
##                info['archives'] = Archive.all().order('-year').order('-month').fetch(12)
##            if update_comments:
##                info['recent_comments'] = Comment.all().order('-date').fetch(5)
##            if update_links:
##                info['blogroll'] = Link.all().filter('linktype =','blogroll').fetch(limit=1000)
##            if update_tags:
##                info['alltags'] = Tag.all().order('-tagcount').fetch(limit=100)
##            if update_categories:
##                info['categories'] = Category.all().fetch(limit=1000)
##
##            logging.debug('basic_info updated')
##            basic_info.update(info)

    @staticmethod
    def create(key, value_obj,time=0,mem_only=False,**kwargs):
        try:
            memcache.set(key,value_obj,time)
            l = []
            for s in kwargs:
                l.append(u'%s=%s'%(s,unicode(kwargs[s])))

            #当memcache only 模式时不保存数据到数据库
            if mem_only:
                value=None
            else:
                value=pickle.dumps(value_obj)
            objcache=ObjCache.get_or_insert(key)
            objcache.cachetime=datetime.now()
            objcache.value=value
            objcache.tags=l
            objcache.time=time
            if time==0:
                objcache.overtime=datetime.max
            else:
                objcache.overtime=datetime.now()+timedelta(0,time)
            objcache.mem_only=mem_only
            objcache.put()

            logging.debug("ObjCache created with key: " + key + " and with tags: " + unicode(l))
        except Exception:
            logging.exception('Exception in cache.create.')

    @staticmethod
    def flush_multi(**kwargs):
        logging.debug('ObjCache.flush_multi called with parameters: '+unicode(kwargs))
        flush = ObjCache.all()
        for key in kwargs:
            flush = flush.filter('tags =',key+'='+unicode(kwargs[key]))
        for obj in flush:
            obj.invalidate()

    @staticmethod
    def filter(**kwargs):
        logging.debug('ObjCache.filter with parameters: '+unicode(kwargs))
        result = ObjCache.all()
        for key in kwargs:
            result = result.filter('tags =',key+'='+unicode(kwargs[key]))
        return result

    @staticmethod
    def get(**kwargs):
        logging.debug('ObjCache.get with parameters: '+unicode(kwargs))
        result = ObjCache.all()
        for key in kwargs:
            result = result.filter('tags =',key+'='+unicode(kwargs[key]))
        result = result.get()
        if result:
            logging.debug('ObjCache.get result: ' + unicode(result.cache_key))
        return result

    @classmethod
    def flush_all(cls):
        '''
        This is faster than invalidate with default parameter values since memcache only need one call
        '''
        logging.debug('ObjCache flush all called')
        memcache.flush_all()
        i=0
        try:
            for cache in ObjCache.all():
                i = i+1
                cache.delete()
            logging.debug('ObjCache.flush_all: '+unicode(i)+" items flushed")
        except Exception:
            logging.exception('Exception in ObjCache.flush_all')
            logging.debug('ObjCache.flush_all: '+unicode(i)+" items flushed")

#other_kwargs中参数的值，会自动包含在key中
def object_cache(key_prefix='',
                 time=0,
                 cache_key=(),
                 cache_control='cache',
                 mem_only=False,
                 **other_kwargs):
    '''
    available options for cache control are: no_cache, cache
    default option is cache
    '''

    def _decorate(method):
        def _wrapper(*args, **kwargs):
            #return method(*args, **kwargs)
            key = 'obj_'+key_prefix

            for keyname in args[1:]:
                key=key +'_'+str(keyname)

            for keyname in kwargs:
                key = key+'_'+str(kwargs[keyname])

            if type(cache_key)==tuple:
                for keyname in cache_key:
                    key = key+'_'+str(keyname)
            else:
                key=key+'_'+str(cache_key)


            if cache_control == 'no_cache':
                logging.debug('object_cache: no_cache for '+key)
                return method(*args, **kwargs)

            result = ObjCache.get_cache_value(key,mem_only)
            if result is not None:
                logging.debug('object_cache: result found for '+key)
                return result

            logging.debug('object_cache: result not found for '+key)
            result = method(*args, **kwargs)
            ObjCache.create(key,result,time=time,mem_only=mem_only,**other_kwargs)
            return result

        return _wrapper

    return _decorate

def object_memcache(key_prefix='',time=3600,cache_key=(),
                 cache_control = 'cache',**other_kwargs):
    '''
    available options for cache control are: no_cache, cache
    default option is cache
    '''
    return object_cache(key_prefix='mem_'+key_prefix,time=time,cache_key=cache_key,
                 cache_control = cache_control,mem_only=True,**other_kwargs)

@object_cache(key_prefix='get_query_count',is_count=True)
def get_query_count(query,*args, **kwargs):
    if hasattr(query,'__len__'):
        return len(query)
    else:
        return query.count()

def format_date(dt):
    return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')

def request_cache(key_prefix='',
                  time=0,
                  cache_control = 'cache',
                  mem_only=False,
                  **other_kwargs):
    '''
    available options for cache control are: no_cache, cache
    default option is cache
    '''
    def _decorate(method):
        def _wrapper(*args, **kwargs):
            if settings.DEBUG:
                return method(*args, **kwargs)
            request=args[0].request
            response=args[0].response

            key = 'request_'+str(args[0].isPhone())+key_prefix+'_'+request.path_qs

            cache_args = other_kwargs
            cache_args['is_htmlpage'] = True


            if cache_control == 'no_cache':
                logging.debug('request_cache: no_cache for '+key)
                if 'last-modified' not in response.headers:
                        response.last_modified = format_date(datetime.utcnow())
                method(*args, **kwargs)
                return

            html= ObjCache.get_cache_value(key,mem_only)
            if html:
                logging.debug('request_cache: found cache for '+key)
                try:
                    response.last_modified =html[1]
                    _len=len(html)
                    if _len>=3:
                        response.set_status(html[2])
                    if _len>=4:
                        for h_key,value in html[3].items():
                            response.headers[h_key]=value
                    response.out.write(html[0])
                    return
                except Exception,e:
                    logging.error(e.message)

            logging.debug('request_cache: not found cache for '+key)
            if 'last-modified' not in response.headers:
                response.last_modified = format_date(datetime.utcnow())

            method(*args, **kwargs)
            result=response.body
            status_code = response.status_int
            html = (result,response.last_modified,status_code,response.headers)
            ObjCache.create(key,html,time=0, mem_only=mem_only,**cache_args)
            return

        return _wrapper
    return _decorate

def request_memcache(key_prefix='',time = 3600,
                   cache_control = 'cache',**other_kwargs
                 ):
    '''
    available options for cache control are: no_cache, cache
    default option is cache
    '''
    return request_cache(key_prefix='mem_'+key_prefix,
                  time=time,
                  cache_control = cache_control,
                  mem_only=True,
                  **other_kwargs);