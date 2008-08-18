import cgi, os,sys
import wsgiref.handlers
from google.appengine.ext.webapp import template, \
    WSGIApplication
from google.appengine.api import users
import app.webapp as webapp2
from google.appengine.ext import db
from base import *
from datetime import datetime ,timedelta
import base64
from django.utils import simplejson


def doRequestHandle(old_handler,new_handler,**args):
        new_handler.initialize(old_handler.request,old_handler.response)
        return  new_handler.get(**args)

class MainPage(BasePublicPage):
    def get(self,page=0):


        postid=self.param('p')
        if postid:
            try:
                postid=int(postid)
                return doRequestHandle(self,SinglePost(),postid=postid)  #singlepost.get(postid=postid)
            except:
                return self.error(404)


        page=int(page)
       	max_page = (self.blog.entrycount - 1) / self.blog.posts_per_page


        if page < 0 or page > max_page:
				return	self.error(404)

        entries = Entry.all().filter('entrytype =','post').\
                filter("published =", True).order('-date').\
                fetch(self.blog.posts_per_page, offset = page * self.blog.posts_per_page)


        show_prev =entries and  (not (page == 0))
        show_next =entries and  ( not (page == max_page))

        logging.debug('this is ok')


        self.render('index',{'entries':entries,
       	                'show_prev' : show_prev,
				        'show_next' : show_next,
				        'pageindex':page
                            })


class EntrysByCategory(BasePublicPage):
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
            entrys=Entry.all().filter('categorie_keys =',cats[0].key())
            entrys,links=Pager(query=entrys).fetch(page_index)
            self.render('category',{'entrys':entrys,'category':cats[0],'pager':links})
        else:
            self.error(414,slug)

class EntrysByTag(BasePublicPage):
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

        entrys=Entry.all().filter('tags =',slug)
        entrys,links=Pager(query=entrys).fetch(page_index)
        self.render('tag',{'entrys':entrys,'tag':slug,'pager':links})



class SinglePost(BasePublicPage):
    #@printinfo
    def get(self,slug=None,postid=None):

        if postid:
            entries = Entry.all().filter("published =", True).filter('post_id =', postid).fetch(1)
        else:
            slug=urldecode(slug)
            entries = Entry.all().filter("published =", True).filter('link =', slug).fetch(1)
        if not entries or len(entries) == 0:
            return self.error(404)

        entry=entries[0]
        comments=Comment.all().filter("entry =",entry)

        commentuser=self.request.cookies.get('commentuser', '')
        if commentuser:
            commentuser=base64.b64decode(commentuser).split('#@#')
        else:
            commentuser=['','','']

        if entry.entrytype=='post':
            self.render('single',
                        {
                        'entry':entry,
                        'comments':comments,
                        'user_name':commentuser[0],
                        'user_email':commentuser[1],
                        'user_url':commentuser[2],
                        })

        else:
            self.render('page',
                        {'entry':entry,
                        'comments':comments,
                        'user_name':commentuser[0],
                        'user_email':commentuser[1],
                        'user_url':commentuser[2],


                        })


class FeedHandler(BaseRequestHandler):
    def get(self,tags=None):
        entries = Entry.all().filter('entrytype =','post').order('-date').fetch(10)
        if entries and entries[0]:
            last_updated = entries[0].date
            last_updated = last_updated.strftime("%Y-%m-%dT%H:%M:%SZ")
        for e in entries:
            e.formatted_date = e.date.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.response.headers['Content-Type'] = 'application/atom+xml'
        self.render2('views/atom.xml',{'entries':entries,'last_updated':last_updated})

class Error404(BaseRequestHandler):
    #@printinfo
    def get(self,slug=None):
         self.error(404)

class Post_comment(BaseRequestHandler):
    #@printinfo
    def post(self,slug=None):
        if self.is_admin:
            name=self.blog.author
            email=self.login_user.email()
            url=self.blog.baseurl
        else:
            name=self.param('author')
            email=self.param('email')
            url=self.param('url')
        key=self.param('key')
        content=self.param('comment')
        if not (name and email and content):
            self.error(-101,'Please input name, email and comment .')
        else:
            comment=Comment(author=name,
                            content=content,
                            email=email,
                            entry=Entry.get(key),
                            weburl=url)

            info_str=base64.b64encode('#@#'.join([name.encode('utf8'),email.encode('utf8'),url.encode('utf8')]))

            self.response.headers.add_header( 'Set-Cookie',
            'commentuser=%s;expires=%s;domain=%s;path=/'
                %( info_str,
                   (datetime.now()+timedelta(days=100)).strftime("%a, %d-%b-%Y %H:%M:%S GMT"),
                   ''
                   )
            )

            comment.put()
            self.redirect(self.referer)

class ChangeTheme(BaseRequestHandler):
    @requires_admin
    def get(self,slug=None):
       theme=self.param('t')
       g_blog.theme_name=theme
       g_blog.get_theme()
       self.redirect('/')

class admin_init_blog(BaseRequestHandler):
    @requires_admin
    def get(self,slug=None):

        for com in Comment.all():
            com.delete()

        for entry in Entry.all():
            entry.delete()

        g_blog.entrycount=0
        self.write('"Init succeed."')

class admin_updatelink(BaseRequestHandler):
    @requires_admin
    def get(self,slug=None):
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

class admin_import_next(BaseRequestHandler):
    @requires_admin
    def get(self,slug=None):
        if self.blog.import_wp:
            categories_list,entrys=self.blog.import_wp
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

        if entrys:
            next=entrys.pop(0)
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
                        comment.put()
                self.write(simplejson.dumps(('entry',next['title'],True)))
                return
        self.blog.import_wp=None
        self.write(simplejson.dumps(('Ok','Finished',False)))

class admin_import(BaseRequestHandler):
    @requires_admin
    def get(self,slug=None):
        gblog_init()
        self.render2('views/admin/import.html')

    @requires_admin
    def post(self):
        import  xml.etree.ElementTree as et


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
        entrys=[]
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
                entrys.append(entry)
            except :
                import traceback

                logging.error('Import ''%s'' error.'%traceback.format_exc(10))

##        self.write('<script> entrys='+simplejson.dumps(entrys)+'</script>')
##        self.render2('views/admin/import.html',
##                    {'categories':simplejson.dumps(categories_list),
##                     'entrys':simplejson.dumps(entrys),
##                     'postback':True})
        #memcache.set('import_wp',simplejson.dumps([categories_list,entrys]),1000)
        self.blog.import_wp=(categories_list,entrys)
        self.render2('views/admin/import.html',
                    {'postback':True})


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





def main():
    webapp.template.register_template_library('filter')
    application = webapp2.WSGIApplication2(
                    [('/skin',ChangeTheme),
                     ('/feed', FeedHandler),
                     ('/post_comment',Post_comment),
                     ('/page/(?P<page>\d+)', MainPage),
                     ('/admin/import',admin_import),
                     ('/admin/import_next',admin_import_next),
                     ('/admin/init_blog',admin_init_blog),
                     ('/admin/updatelink',admin_updatelink),

                     ('/category/(.*)',EntrysByCategory),
                     ('/tag/(.*)',EntrysByTag),
                     ('/', MainPage),
                     ('/([\\w\\-\\./]+)', SinglePost),
                     ('.*',Error404),
                     ],debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
    main()