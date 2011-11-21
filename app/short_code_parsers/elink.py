from django.template import Template, Context
from django.conf import settings

def parse(kwargs, content):
    caption = kwargs.get('caption')
    if caption:
        return  '<a class="external" href="'+content+'">'+caption+'</a>'
    else:
        return  '<a class="external" href="'+content+'">'+content+'</a>'
	