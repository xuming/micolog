# -*- coding: utf-8 -*-
"""
Model for micolog.
This module define the struct of gae db store.
"""
import os, logging
from google.appengine.api import memcache
from model import Blog, Category, Entry,OptionSet,Link

try:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    from django.utils.translation import  activate
    from django.conf import settings
    settings._target = None
    activate(g_blog().language)
except:
    pass


def main():
    """
    App Caching: http://code.google.com/appengine/docs/python/runtime.html#App_Caching
    App Engine does not call it when loading the request handler for the first time on a server
    """
    pass

if __name__ == "__main__":
    main()

