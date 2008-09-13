import logging
from django import template
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
