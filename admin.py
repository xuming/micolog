import cgi, os,sys
import wsgiref.handlers
from google.appengine.ext.webapp import template, \
    WSGIApplication
from google.appengine.api import users
import app.webapp as webapp2
from google.appengine.ext import db
from base import *
from datetime import datetime ,timedelta
import base64,random,math
from django.utils import simplejson

class Error404(BaseRequestHandler):
    #@printinfo
    def get(self,slug=None):
        self.render2('views/admin/404.html')

class admin_do_action(BaseRequestHandler):
    @requires_admin
    def get(self,slug=None):
        try:
            func=getattr(self,'action_'+slug)
            if func and callable(func):
                func()
            else:
                self.render2('views/admin/error.html',{'message':'This operate has not defined!'})
        except:
             self.render2('views/admin/error.html',{'message':'This operate has not defined!'})
    @requires_admin
    def post(self,slug=None):
        try:
            func=getattr(self,'action_'+slug)
            if func and callable(func):
                func()
            else:
                self.render2('views/admin/error.html',{'message':'This operate has not defined!'})
        except:
             self.render2('views/admin/error.html',{'message':'This operate has not defined!'})

    def action_test(self):
        self.write(os.environ)

    def action_cacheclear(self):
        memcache.flush_all()
        self.write('"Cache clear ok"')

    def action_updatecomments(self):
        for entry in Entry.all():
            cnt=entry.comments().count()
            if cnt<>entry.commentcount:
                entry.commentcount=cnt
                entry.put()
        self.write('"ok"')

    def action_updatelink(self):
        link_format=self.param('linkfmt')

        if link_format:
            link_format=link_format.strip()
            g_blog.link_format=link_format
            g_blog.save()
            for entry in Entry.all():
                vals={'year':entry.date.year,'month':str(entry.date.month).zfill(2),'day':entry.date.day,
                'postname':entry.slug,'post_id':entry.post_id}

                if entry.slug:
                    newlink=link_format%vals
                else:
                    newlink='?p=%(post_id)s'%vals

                if entry.link<>newlink:
                    entry.link=newlink
                    entry.put()
            self.write('"ok"')
        else:
            self.write('"Please input url format."')

    def action_init_blog(self,slug=None):

        for com in Comment.all():
            com.delete()

        for entry in Entry.all():
            entry.delete()

        g_blog.entrycount=0
        self.write('"Init succeed."')



class admin_import_next(BaseRequestHandler):
    @requires_admin
    def get(self,slug=None):
        if self.blog.import_wp:
            categories_list,entries=self.blog.import_wp
        if categories_list:
            next=categories_list.pop(0)
            if next:
                nicename=next['nicename']
                cat=Category.get_by_key_name('cat_'+nicename)
                if not cat:
                    cat=Category(key_name='cat_'+nicename)
                cat.name=next['name']
                cat.slug=nicename
                cat.put()
                self.write(simplejson.dumps(('category',next['name'],True)))
                return

        if entries:
            next=entries.pop(0)
            if next:
                entry=Entry()
                entry.title=next['title']
                entry.author=self.login_user
                entry.is_wp=True
                entry.date=datetime.strptime( next['pubDate'],"%a, %d %b %Y %H:%M:%S +0000")
                entry.entrytype=next['post_type']
                entry.content=next['encoded']
                entry.post_id=next['post_id']
                entry.slug=next['post_name']
                entry.entry_parent=next['post_parent']
                entry.menu_order=next['menu_order']


                for cat in next['categories']:
                    nicename=cat
                    c=Category.get_by_key_name('cat_'+nicename)
                    if c:
                        entry.categorie_keys.append(c.key())
                for tag in next['tags']:
                    entry.tags.append(tag)


                if next['published']:
                    key=entry.publish(True)
                else:
                    key=entry.save()

                for com in next['comments']:
                        comment=Comment(author=com['author'],
                                        content=com['content'],
                                        entry=entry,
                                        )
                        try:
                            comment.email=com['email']
                            comment.weburl=com['weburl']
                        except:
                            pass
                        comment.save()
                self.write(simplejson.dumps(('entry',next['title'],True)))
                return
        self.blog.import_wp=None
        self.write(simplejson.dumps(('Ok','Finished',False)))

class admin_import(BaseRequestHandler):
    def __init__(self):
        self.current='import'
    @requires_admin
    def get(self,slug=None):
        gblog_init()
        self.render2('views/admin/import.html')

    @requires_admin
    def post(self):


        import  xml.etree.ElementTree as et


        link_format=self.param('link_format')

        if link_format:
            g_blog.link_format=link_format.strip()
            g_blog.save()

        try:

            wpfile=self.param('wpfile')

            doc=et.fromstring(wpfile)
            #use namespace
            wpns='{http://wordpress.org/export/1.0/}'

            contentns="{http://purl.org/rss/1.0/modules/content/}"
            et._namespace_map[wpns]='wp'
            et._namespace_map[contentns]='content'

            channel=doc.find('channel')
            #self.write('Blog:'+channel.findtext('title')+'<br>')
            categories=channel.findall(wpns+'category')
            categories_list=[]
            for cate in categories:
                #self.write('cate:'+cate.findtext(wpns+'cat_name')+'<br>')

                nicename=cate.findtext(wpns+'category_nicename')
                name=cate.findtext(wpns+'cat_name')
                categories_list.append({'nicename':nicename,'name':name})
            import time
            items=channel.findall('item')
            entries=[]
            for item in items:
                title=item.findtext('title')
                try:
                    #self.write(title+'<br>')

                    entry={}
                    entry['title']=item.findtext('title')
                    logging.info(title)
                    #entry['author']=self.login_user
                    #entry.is_wp=True
                    entry['pubDate']=item.findtext('pubDate')
                    entry['post_type']=item.findtext(wpns+'post_type')
                    entry['encoded']= item.findtext(contentns+'encoded')
                    entry['post_id']=int(item.findtext(wpns+'post_id'))
                    entry['post_name']=item.findtext(wpns+'post_name')
                    entry['post_parent']=int(item.findtext(wpns+'post_parent'))
                    entry['menu_order']=int(item.findtext(wpns+'menu_order'))

                    entry['tags']=[]
                    entry['categories']=[]


                    cats=item.findall('category')


                    for cat in cats:
                        if cat.attrib.has_key('nicename'):
                            cat_type=cat.attrib['domain']
                            if cat_type=='tag':
                                entry['tags'].append(cat.text)
                            else:
                                nicename=cat.attrib['nicename']
                                entry['categories'].append(nicename)

                    pub_status=item.findtext(wpns+'status')
                    if pub_status=='publish':
                        entry['published']=True
                    else:
                        entry['published']=False

                    entry['comments']=[]

                    comments=item.findall(wpns+'comment')

                    for com in comments:
                        try:
                            comment_approved=int(com.findtext(wpns+'comment_approved'))
                        except:
                            comment_approved=0
                        if comment_approved:


                            comment=dict(author=com.findtext(wpns+'comment_author'),
                                            content=com.findtext(wpns+'comment_content'),
                                            email=com.findtext(wpns+'comment_author_email'),
                                            weburl=com.findtext(wpns+'comment_author_url')
                                            )

                            entry['comments'].append(comment)
                    entries.append(entry)
                except :
                    import traceback

                    logging.error('Import ''%s'' error.'%traceback.format_exc(10))
            self.blog.import_wp=(categories_list,entries)
            self.render2('views/admin/import.html',
                        {'postback':True})
        except:
            self.render2('views/admin/import.html',{'error':'import faiure.'})



    @requires_admin
    def post_old(self):
        import  xml.etree.ElementTree as et
        wpfile=self.param('wpfile')
        doc=et.fromstring(wpfile)
        #use namespace
        wpns='{http://wordpress.org/export/1.0/}'

        contentns="{http://purl.org/rss/1.0/modules/content/}"
        et._namespace_map[wpns]='wp'
        et._namespace_map[contentns]='content'

        channel=doc.find('channel')
        self.write('Blog:'+channel.findtext('title')+'<br>')
        categories=channel.findall(wpns+'category')
        for cate in categories:
            self.write('cate:'+cate.findtext(wpns+'cat_name')+'<br>')

            nicename=cate.findtext(wpns+'category_nicename')
            cat=Category.get_by_key_name('cat_'+nicename)
            if not cat:
                cat=Category(key_name='cat_'+nicename)
            cat.name=cate.findtext(wpns+'cat_name')
            cat.slug=nicename
            cat.put()

##        tags=channel.findall(wpns+'tag')
##        for tag in tags:
##            self.write('tag:'+tag.findtext(wpns+'tag_name')+'<br>')
##            ntag=Tag()
##            ntag.tag=tag.findtext(wpns+'tag_name')
##            ntag.put()
        import time
        items=channel.findall('item')
        for item in items:
            title=item.findtext('title')
            try:
                self.write(title+'<br>')

                entry=Entry()
                entry.title=item.findtext('title')
                logging.info(title)
                entry.author=self.login_user
                entry.is_wp=True
                entry.date=datetime.strptime( item.findtext('pubDate'),"%a, %d %b %Y %H:%M:%S +0000")
                entry.entrytype=item.findtext(wpns+'post_type')
                entry.content=item.findtext(contentns+'encoded')
                entry.post_id=int(item.findtext(wpns+'post_id'))
                entry.slug=item.findtext(wpns+'post_name')
                entry.entry_parent=int(item.findtext(wpns+'post_parent'))
                entry.menu_order=int(item.findtext(wpns+'menu_order'))


                cats=item.findall('category')

                for cat in cats:
                    if cat.attrib.has_key('nicename'):
                        cat_type=cat.attrib['domain']
                        if cat_type=='tag':
                            entry.tags.append(cat.text)
                        else:
                            nicename=cat.attrib['nicename']
                            c=Category.get_by_key_name('cat_'+nicename)
                            if c:
                                entry.categorie_keys.append(c.key())

                pub_status=item.findtext(wpns+'status')
                if pub_status=='publish':
                    key=entry.publish(True)
                else:
                    key=entry.save()

                comments=item.findall(wpns+'comment')

                for com in comments:
                    try:
                        comment_approved=int(com.findtext(wpns+'comment_approved'))
                    except:
                        comment_approved=0
                    if comment_approved:

                        comment=Comment(author=com.findtext(wpns+'comment_author'),
                                        content=com.findtext(wpns+'comment_content'),
                                        entry=entry,
                                        )
                        try:
                            comment.email=com.findtext(wpns+'comment_author_email')
                            comment.weburl=com.findtext(wpns+'comment_author_url')
                        except:
                            pass
                        comment.put()
            except :
                import traceback

                self.write('Import ''%s'' error.<br>'%title)
                logging.error('Import ''%s'' error.'%traceback.format_exc(10))

class admin_setup(BaseRequestHandler):
    def __init__(self):
        self.current='config'

    @requires_admin
    def get(self,slug=None):
        vals={'themes':ThemeIterator()}
        self.render2('views/admin/setup.html',vals)

    @requires_admin
    def post(self):
        str_options= self.param('str_options').split(',')
        for name in str_options:
            value=self.param(name)
            setattr(g_blog,name,value)

        bool_options= self.param('bool_options').split(',')
        for name in bool_options:
            value=self.param(name)=='on'
            setattr(g_blog,name,value)

        int_options= self.param('int_options').split(',')
        for name in int_options:
            try:
                value=int( self.param(name))
                setattr(g_blog,name,value)
            except:
                pass

        g_blog.owner=self.login_user
        g_blog.save()
        gblog_init()
        vals={'themes':ThemeIterator()}
        self.render2('views/admin/setup.html',vals)

class admin_entry(BaseRequestHandler):
    def __init__(self):
        self.current='write'


    @requires_admin
    def get(self,slug='post'):
        action=self.param("action")
        entry=None
        cats=Category.all()
        if action and  action=='edit':
                try:
                    key=self.param('key')
                    entry=Entry.get(key)

                except:
                    pass
        else:
            action='add'

        def mapit(cat):
            return {'name':cat.name,'slug':cat.slug,'select':entry and cat.key() in entry.categorie_keys}

        vals={'action':action,'entry':entry,'entrytype':slug,'cats':map(mapit,cats)}
        self.render2('views/admin/entry.html',vals)

    @requires_admin
    def post(self,slug='post'):
        action=self.param("action")
        title=self.param("post_title")
        content=self.param('content')
        tags=self.param("tags")
        cats=self.request.get_all('cats')
        key=self.param('key')
        published=self.param('publish')
        entry_slug=self.param('slug')
        def mapit(cat):
            return {'name':cat.name,'slug':cat.slug,'select':cat.slug in cats}

        vals={'action':action,'postback':True,'cats':Category.all(),'entrytype':slug,'cats':map(mapit,Category.all()),
              'entry':{'title':title,'content':content,'strtags':tags,'key':key,'published':published,
              'slug':entry_slug}}
        if not (title and content):
            vals.update({'result':False, 'msg':'Please input title and content.'})
            self.render2('views/admin/entry.html',vals)
        else:
            if action=='add':
               entry= Entry(title=title,content=content,tags=tags.split(','))
               entry.entrytype=slug
               entry.slug=entry_slug
               newcates=[]

               if cats:

                   for cate in cats:
                        c=Category.all().filter('slug =',cate)
                        if c:
                            newcates.append(c[0].key())
               entry.categorie_keys=newcates;
               if published:
                    entry.publish()
               else:
                   entry.published=False
                   entry.save()
               vals.update({'action':'edit','result':True,'msg':'Saved ok','entry':entry})
               self.render2('views/admin/entry.html',vals)
            elif action=='edit':
                try:
                    entry=Entry.get(key)
                    entry.title=title
                    entry.content=content
                    entry.tags=tags.split(',')
                    newcates=[]
                    if cats:

                        for cate in cats:
                            c=Category.all().filter('slug =',cate)
                            if c:
                                newcates.append(c[0].key())
                    entry.categorie_keys=newcates;
                    if published:
                        entry.publish()
                    else:
                        entry.published=False
                        entry.save()
                    vals.update({'result':True,'msg':'Saved ok','entry':entry})
                    self.render2('views/admin/entry.html',vals)

                except:
                    vals.update({'result':False,'msg':'Error:Entry can''t been saved.'})
                    self.render2('views/admin/entry.html',vals)


class admin_entries(BaseRequestHandler):
    @requires_admin
    def get(self,slug='post'):
        try:
            page_index=int(self.param('page'))
        except:
            page_index=1




        entries=Entry.all().filter('entrytype =',slug).order('-date')
        entries,links=Pager(query=entries,items_per_page=15).fetch(page_index)

        self.render2('views/admin/'+slug+'s.html',
         {
           'current':slug+'s',
           'entries':entries,
           'pager':links
          }
        )

    @requires_admin
    def post(self,slug='post'):
        try:
            linkcheck= self.request.get_all('checks')
            for id in linkcheck:
                kid=int(id)
                entry=Entry.get_by_id(kid)
                entry.delete()
        finally:

            self.redirect('/admin/entries/'+slug)


class admin_categories(BaseRequestHandler):
    @requires_admin
    def get(self,slug=None):
        try:
            page_index=int(self.param('page'))
        except:
            page_index=1




        cats=Category.all()
        entries,pager=Pager(query=cats,items_per_page=15).fetch(page_index)

        self.render2('views/admin/categories.html',
         {
           'current':'categories',
           'cats':cats,
           'pager':pager
          }
        )

    @requires_admin
    def post(self,slug=None):
        try:
            linkcheck= self.request.get_all('checks')
            for key in linkcheck:

                cat=Category.get(key)
                cat.delete()
        finally:
            self.redirect('/admin/categories')

class admin_comments(BaseRequestHandler):
    @requires_admin
    def get(self,slug=None):
        try:
            page_index=int(self.param('page'))
        except:
            page_index=1




        comments=Comment.all().order('-date')
        entries,pager=Pager(query=comments,items_per_page=15).fetch(page_index)

        self.render2('views/admin/comments.html',
         {
           'current':'comments',
           'comments':comments,
           'pager':pager
          }
        )

    @requires_admin
    def post(self,slug=None):
        try:
            linkcheck= self.request.get_all('checks')
            for key in linkcheck:

                comment=Comment.get(key)
                comment.delit()
        finally:
            self.redirect('/admin/comments')

class admin_links(BaseRequestHandler):
    @requires_admin
    def get(self,slug=None):
        self.render2('views/admin/links.html',
         {
          'current':'links',
          'links':Link.all().filter('linktype =','blogroll')#.order('-createdate')
          }
        )
    def post(self):
        linkcheck= self.request.get_all('linkcheck')
        for link_id in linkcheck:
            kid=int(link_id)
            link=Link.get_by_id(kid)
            link.delete()
        self.redirect('/admin/links')

class admin_link(BaseRequestHandler):
    @requires_admin
    def get(self,slug=None):
        action=self.param("action")
        vals={'current':'links'}
        if action and  action=='edit':
                try:
                    action_id=int(self.param('id'))
                    link=Link.get_by_id(action_id)
                    vals.update({'link':link})
                except:
                    pass
        else:
            action='add'
        vals.update({'action':action})

        self.render2('views/admin/link.html',vals)

    def post(self):
        action=self.param("action")
        name=self.param("link_name")
        url=self.param("link_url")

        vals={'action':action,'postback':True,'current':'links'}
        if not (name and url):
            vals.update({'result':False,'msg':'Please input name and url.'})
            self.render2('views/admin/link.html',vals)
        else:
            if action=='add':
               link= Link(linktext=name,href=url)
               link.put()
               vals.update({'result':True,'msg':'Saved ok'})
               self.render2('views/admin/link.html',vals)
            elif action=='edit':
                try:
                    action_id=int(self.param('id'))
                    link=Link.get_by_id(action_id)
                    link.linktext=name
                    link.href=url
                    link.put()
                    #goto link manage page
                    self.redirect('/admin/links')

                except:
                    vals.update({'result':False,'msg':'Error:Link can''t been saved.'})
                    self.render2('views/admin/link.html',vals)

class admin_category(BaseRequestHandler):
    def __init__(self):
        self.current='categories'
    @requires_admin
    def get(self,slug=None):
        action=self.param("action")
        category=None
        if action and  action=='edit':
                try:
                    key=self.param('key')
                    category=Category.get(key)

                except:
                    pass
        else:
            action='add'
        vals={'action':action,'category':category}
        self.render2('views/admin/category.html',vals)

    @requires_admin
    def post(self):
        action=self.param("action")
        name=self.param("name")
        slug=self.param("slug")

        vals={'action':action,'postback':True}
        if not (name and slug):
            vals.update({'result':False,'msg':'Please input name and slug.'})
            self.render2('views/admin/category.html',vals)
        else:
            if action=='add':
               cat= Category(name=name,slug=slug    )
               cat.put()
               vals.update({'result':True,'msg':'Saved ok'})
               self.render2('views/admin/category.html',vals)
            elif action=='edit':
                try:
                    key=self.param('key')
                    cat=Category.get(key)
                    cat.name=name
                    cat.slug=slug
                    cat.put()
                    self.redirect('/admin/categories')

                except:
                    vals.update({'result':False,'msg':'Error:Category can''t been saved.'})
                    self.render2('views/admin/category.html',vals)

class admin_status(BaseRequestHandler):
    @requires_admin
    def get(self):
        self.render2('views/admin/status.html',{'cache':memcache.get_stats(),'current':'status','environ':os.environ})


def main():
    webapp.template.register_template_library('filter')
    application = webapp2.WSGIApplication2(
                    [
                    ('/admin/{0,1}',admin_setup),
                    ('/admin/setup',admin_setup),
                    ('/admin/entries/(post|page)',admin_entries),
                    ('/admin/links',admin_links),
                    ('/admin/categories',admin_categories),
                    ('/admin/comments',admin_comments),
                    ('/admin/link',admin_link),
                    ('/admin/category',admin_category),
                     ('/admin/(post|page)',admin_entry),
                     ('/admin/status',admin_status),


                     ('/admin/import',admin_import),
                     ('/admin/import_next',admin_import_next),
                     ('/admin/do/(\w+)',admin_do_action),

                     ('.*',Error404),
                     ],debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
    main()