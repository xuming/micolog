# -*- coding: utf-8 -*-
# Django settings for the example project.
"""
Settings For Micolog
"""
import os
#from django.conf import settings as djangoSetting

#os.environ['DJANGO_SETTINGS_MODULE'] = 'micolog.settings'
##djangoSetting.configure(
##    DEBUG=True,
##    TEMPLATE_DEBUG=False,
##    LOCALE_PATHS = 'locale',
##    USE_I18N = False,
##    ROOT_PATH=os.path.dirname(__file__),
##    ENABLE_MEMCACHE=True,
##    TEMPLATE_LOADERS = ('django.template.loaders.filesystem.load_template_source',
##                    'micolog.zip_loader.load_template_source')
##
##
##)

DEBUG=False
TEMPLATE_DEBUG=False
LOCALE_PATHS = 'locale'
USE_I18N = True
ROOT_PATH= os.path.dirname(__file__)
ENABLE_MEMCACHE=True

LANGUAGE_CODE = 'zh-CN'

#TEMPLATE_LOADERS = ('django.template.loaders.filesystem.load_template_source',
#                   'micolog.zip_loader.load_template_source')


ENABLE_MEMCACHE=True
NOTIFICATION_SITES = [
  ('http', 'www.google.com', 'webmasters/sitemaps/ping', {}, '', 'sitemap')
  ]


