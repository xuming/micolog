# -*- coding: utf-8 -*-
import cgi, os

import wsgiref.handlers

# Google App Engine imports.
##import app.webapp as webapp2

from datetime import timedelta
import random
from django.utils import simplejson
import filter as myfilter
from app.safecode import Image
from app.gmemsess import Session
from base import *
from model import *
from django.utils.translation import ugettext as _

##os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
##from django.utils.translation import  activate
##from django.conf import settings
##settings._target = None
##activate(g_blog.language)
from google.appengine.ext import zipserve

class BasePublicPage(BaseRequestHandler):
    def initialize(self, request, response):
        BaseRequestHandler.initialize(self,request, response)
##        m_pages=Entry.all().filter('entrytype =','page')\
##            .filter('published =',True)\
##            .filter('entry_parent =',0)\
##            .order('menu_order')
##        blogroll=Link.all().filter('linktype =','blogroll')
##        archives=Archive.all().order('-year').order('-month').fetch(12)
##        alltags=Tag.all()
##        self.template_vals.update(
##            dict(menu_pages=m_pages, categories=Category.all(), blogroll=blogroll, archives=archives, alltags=alltags,
##                 recent_comments=Comment.all().order('-date').fetch(5)))

##    def m_list_pages(self):
##        menu_pages=None
##        entry=None
##        if self.template_vals.has_key('menu_pages'):
##            menu_pages= self.template_vals['menu_pages']
##        if self.template_vals.has_key('entry'):
##            entry=self.template_vals['entry']
##        ret=''
##        current=''
##        for page in menu_pages:
##            if entry and entry.entrytype=='page' and entry.key()==page.key():
##                current= 'current_page_item'
##            else:
##                current= 'page_item'
##            #page is external page ,and page.slug is none.
##            if page.is_external_page and not page.slug:
##                ret+='<li class="%s"><a href="%s" target="%s" >%s</a></li>'%( current,page.link,page.target, page.title)
##            else:
##                ret+='<li class="%s"><a href="/%s" target="%s">%s</a></li>'%( current,page.link, page.target,page.title)
##        return ret



class MainPage(BasePublicPage):
    def head(self,page=1):
        pass


    @cache()
    def get(self,page=1):
        self.write("ok")
##
##        postid=self.param('p')
##        if postid:
##            try:
##                postid=int(postid)
##                return doRequestHandle(self,SinglePost(),postid=postid)  #singlepost.get(postid=postid)
##            except:
##                return self.error(404)
##        if g_blog.allow_pingback :
##            self.response.headers['X-Pingback']="%s/rpc"%str(g_blog.baseurl)
##        self.doget(page)

    def post(self):
        postid=self.param('p')
        if postid:
            try:
                postid=int(postid)
                return doRequestPostHandle(self,SinglePost(),postid=postid)  #singlepost.get(postid=postid)
            except:
                return self.error(404)


    @cache()
    def doget(self,page):
        page=int(page)
        entrycount=g_blog.postscount()
        max_page = entrycount / g_blog.posts_per_page + ( entrycount % g_blog.posts_per_page and 1 or 0 )

        if page < 1 or page > max_page:
                return	self.error(404)

        entries = Entry.all().filter('entrytype =','post').\
                filter("published =", True).order('-sticky').order('-date').\
                fetch(self.blog.posts_per_page, offset = (page-1) * self.blog.posts_per_page)


        show_prev =entries and  (not (page == 1))
        show_next =entries and  (not (page == max_page))
        #print page,max_page,g_blog.entrycount,self.blog.posts_per_page

        return self.render('index',
                           dict(entries=entries, show_prev=show_prev, show_next=show_next, pageindex=page, ishome=True,
                                pagecount=max_page, postscounts=entrycount))



if __name__ == "__main__":
    main()