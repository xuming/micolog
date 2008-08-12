import cgi, os
import wsgiref.handlers
from google.appengine.ext.webapp import template, \
    WSGIApplication
from google.appengine.api import users
import app.webapp as webapp2
from google.appengine.ext import db
from base import *
from datetime import datetime ,timedelta
import base64


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
                filter("published =", True).order('-date')


        show_prev =entries and  (not (page == 0))
        show_next =entries and  ( not (page == max_page))


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
        cats=Category.all().filter('slug =',slug)
        if cats:
            entrys=Entry.all().filter('categorie_keys =',cats[0].key())
            entrys,links=Pager(query=entrys).fetch(page_index)
            self.render('category',{'entrys':entrys,'category':cats[0],'pager':links})

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
        slug=urllib.unquote(urllib.unquote(slug))
        entrys=Entry.all().filter('tags =',slug)
        entrys,links=Pager(query=entrys).fetch(page_index)
        self.render('tag',{'entrys':entrys,'tag':slug,'pager':links})



class SinglePost(BasePublicPage):
    #@printinfo
    def get(self,slug=None,postid=None):
        if postid:
            entries = Entry.all().filter("published =", True).filter('post_id =', postid).fetch(1)
        else:
            entries = Entry.all().filter("published =", True).filter('link =', slug).fetch(1)
        if not entries or len(entries) == 0:
            return self.error(404)

        entry=entries[0]
        comments=Comment.all().filter("entry =",entry)

        commentuser=self.request.cookies.get('commentuser', '')
        commentuser=base64.b64decode(commentuser).split('#@#')
        if entry.entrytype=='post':
            self.render('single',
                        {'entry':entry,
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

class admin_import(BaseRequestHandler):
    @requires_admin
    def get(self,slug=None):
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
        items=channel.findall('item')
        for item in items:
            self.write(item.findtext('title'))
            entry=Entry()
            entry.title=item.findtext('title')
            logging.info(entry.title)
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
                    nicename=cat.attrib['nicename']
                    if cat_type=='tag':
                        entry.tags.append(cat.text)
                    else:
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
                comment_approved=int(com.findtext(wpns+'comment_approved'))
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




def main():
    application = webapp2.WSGIApplication2(
                    [('/skin',ChangeTheme),
                     ('/themes/[\\w\\-]+/templates/.*',Error404),
                     ('/feed', FeedHandler),
                     ('/post_comment',Post_comment),
                     ('/page/(?P<page>\d+)', MainPage),
                     ('/admin/import',admin_import),
                     ('/category/(.*)',EntrysByCategory),
                     ('/tag/(.*)',EntrysByTag),

                     ('/', MainPage),
                     ('/([\\w\\-\\./]+)', SinglePost),


                     ('.*',Error404),

                     ],debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
    main()