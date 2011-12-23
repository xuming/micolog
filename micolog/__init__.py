
import settings
import template
template.register_template_library('micolog.filter.myfilter')
import webapp2

import blog,theme,admin


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
                ('/post/(?P<postid>\d+)',blog.SinglePost),
                ('/page/(?P<page>\d+)', blog.SinglePost),
                ('/themes/[\\w\\-]+/templates/.*',theme.NotFound),
                ('/themes/(?P<prefix>[\\w\\-]+)/(?P<name>.+)', theme.GetFile),

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
                ('/do/(\w+)', blog.do_action),
                ('/e/(.*)',blog.Other),
                ('/([\\w\\-\\./%]+)', blog.SinglePost),
                ('.*',blog.Error404)
            ],debug=True)

