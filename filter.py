import logging
from django import template
import urllib
register = template.Library()


@register.filter
def urlencode(value):
    return urllib.quote(value.encode('utf8'))