# -*- coding: utf-8 -*-
import logging
from django import template
from model import *
import  django.template.defaultfilters as defaultfilters
import urllib
register = template.Library()
from datetime import *

@register.filter
def datetz(date,format):  #datetime with timedelta
	t=timedelta(seconds=3600*g_blog.timedelta)
	return defaultfilters.date(date+t,format)

@register.filter
def TimestampISO8601(t):
	"""Seconds since epoch (1970-01-01) --> ISO 8601 time string."""
	return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t))

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
def excerpt_more(entry,value='..more'):
	return entry.get_content_excerpt(value.decode('utf8'))

@register.filter
def dict_value(v1,v2):
	return v1[v2]


from app.html_filter import html_filter

plog_filter = html_filter()
plog_filter.allowed = {
		'a': ('href', 'target', 'name'),
		'b': (),
		'blockquote': (),
		'pre': (),
		'em': (),
		'i': (),
		'img': ('src', 'width', 'height', 'alt', 'title'),
		'strong': (),
		'u': (),
		'font': ('color', 'size'),
		'p': (),
		'h1': (),
		'h2': (),
		'h3': (),
		'h4': (),
		'h5': (),
		'h6': (),
		'table': (),
		'tr': (),
		'th': (),
		'td': (),
		'ul': (),
		'ol': (),
		'li': (),
		'br': (),
		'hr': (),
		}

plog_filter.no_close += ('br',)
plog_filter.allowed_entities += ('nbsp','ldquo', 'rdquo', 'hellip',)
plog_filter.make_clickable_urls = False # enable this will get a bug about a and img

@register.filter
def do_filter(data):
	return plog_filter.go(data)

'''
tag like {%mf header%}xxx xxx{%endmf%}
'''
@register.tag("mf")
def do_mf(parser, token):
	nodelist = parser.parse(('endmf',))
	parser.delete_first_token()
	return MfNode(nodelist,token)

class MfNode(template.Node):
	def __init__(self, nodelist,token):
		self.nodelist = nodelist
		self.token=token

	def render(self, context):
		tokens= self.token.split_contents()
		if len(tokens)<2:
			raise TemplateSyntaxError, "'mf' tag takes one argument: the filter name is needed"
		fname=tokens[1]
		output = self.nodelist.render(context)
		return g_blog.tigger_filter(fname,output)