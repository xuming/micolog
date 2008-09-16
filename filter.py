import logging
from django import template
from model import *
import urllib
register = template.Library()


@register.filter
def urlencode(value):
    return urllib.quote(value.encode('utf8'))

@register.filter
def check_current(v1,v2):
    if v1==v2:
        return "current"
    else:
        return ""

@register.filter
def dict_value(v1,v2):
    return v1[v2]



