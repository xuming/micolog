import os,logging
import template
template.register_template_library('micolog.filter.myfilter')
#template.register_template_library('micolog.filter.filter')
template.register_template_library('micolog.filter.recurse')
import webapp2
from webapp2_extras import routes
import blog,theme,admin,cache
from google.appengine.ext import zipserve

admin_app=webapp2.WSGIApplication(
            [
                ('/admin/{0,1}',admin.admin_main),
                ('/admin/setup',admin.admin_setup),
                ('/admin/entries/(post|page)',admin.admin_entries),
                ('/admin/links',admin.admin_links),
                ('/admin/categories',admin.admin_categories),
                ('/admin/comments',admin.admin_comments),
                ('/admin/link',admin.admin_link),
                ('/admin/category',admin.admin_category),
                ('/admin/(post|page)',admin.admin_entry),

                ('/admin/status',admin.admin_status),
                ('/admin/authors',admin.admin_authors),
                ('/admin/author',admin.admin_author),
                ('/admin/import',admin.admin_import),
                ('/admin/tools',admin.admin_tools),
                ('/admin/plugins',admin.admin_plugins),
                ('/admin/plugins/(\w+)',admin.admin_plugins_action),
                ('/admin/sitemap',admin.admin_sitemap),
                ('/admin/export/micolog.xml',admin.WpHandler),
                ('/admin/do/(\w+)',admin.admin_do_action),
                ('/admin/lang',admin.setlanguage),
                ('/admin/theme/edit/(\w+)',admin.admin_ThemeEdit),
                ('/admin/upload', admin.Upload),
                ('/admin/filemanager',admin.FileManager),
                ('/admin/uploadex', admin.UploadEx),

                ('.*',admin.Error404)
            ],debug=True)


micolog_app = webapp2.WSGIApplication(
            [
                ('/', blog.MainPage),
                webapp2.Route('/post/<postid:\d+>', blog.SinglePost),
                webapp2.Route('/page/<page:\d+>', blog.SinglePost),
                ('/themes/[\\w\\-]+/templates/.*',theme.NotFound),
                ('/themes/(?P<prefix>[\\w\\-]+)/(?P<name>.+)', theme.GetFile),
                ('/tinymce/(.*)', zipserve.make_zip_handler('tinymce.zip')),
                ('/media/([^/]*)/{0,1}.*',blog.getMedia),
                ('/checkimg/', blog.CheckImg),
                ('/checkcode/', blog.CheckCode),
                ('/skin',blog.ChangeTheme),
                ('/feed', blog.FeedHandler),
                ('/feed/comments',blog.CommentsFeedHandler),
                ('/sitemap', blog.SitemapHandler),
                ('/sitemap\.xml', blog.SitemapHandler),
                ('/post_comment',blog.Post_comment),
                ('/category/(.*)',blog.entriesByCategory),
                ('/(\d{4})/(\d{1,2})',blog.archive_by_month),
                ('/tag/(.*)',blog.entriesByTag),

                webapp2.Route('/do/<slug:\w+>', blog.do_action),
                #('/e/(.*)',blog.Other),
                ('/([\\w\\-\\./%]+)', blog.SinglePost),

                ('.*',blog.Error404)
            ],debug=True)



def main():
    #webapp2.template.register_template_library('filter.filter')
    #webapp2.template.register_template_library('filter.recurse')

    from model import Blog
    g_blog=Blog.getBlog()
    if not g_blog:
            g_blog=Blog(id='default')
            g_blog.put()
            g_blog.InitBlogData()

    g_blog.application=micolog_app
    g_blog.plugins.register_handlerlist(micolog_app)
    from django.utils.translation import  activate
    activate(g_blog.language)
    logging.getLogger().setLevel(logging.DEBUG)
#if __name__ == "__main__":
main()