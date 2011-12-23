# -*- coding: utf-8 -*-
# Django settings for the example project.
"""
Settings For Micolog
"""
import os

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
DEBUG = True
TEMPLATE_DEBUG = False

ENABLE_MEMCACHE=True


##LANGUAGE_CODE = 'zh-CN'
##LANGUAGE_CODE = 'fr'
LOCALE_PATHS = 'locale'
USE_I18N = True
ROOT_PATH=os.path.dirname(__file__)
TEMPLATE_LOADERS = ('django.template.loaders.filesystem.load_template_source',
                    'ziploader.zip_loader.load_template_source')

NOTIFICATION_SITES = [
  ('http', 'www.google.com', 'webmasters/sitemaps/ping', {}, '', 'sitemap')
  ]

