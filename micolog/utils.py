# -*- coding: UTF-8 -*-
"""
Common class and functions used by micolog.
"""
import re

def slugify(inStr):
    """Conver string to slug.
    example::

        >>> slugify('this is a test')
        return 'this-is-a-test'

    """
    inStr = inStr.replace('-', '')
    removelist = ["a", "an", "as", "at", "before", "but", "by", "for", "from", "is", "in", "into", "like", "of", "off", "on", "onto", "per", "since", "than", "the", "this", "that", "to", "up", "via", "with"];
    for a in removelist:
        aslug = re.sub(r'\b'+a+r'\b', '', inStr)
    #aslug = re.sub('[^\w\s-]', '', aslug).strip().lower()
    aslug = re.sub('\s+', '-', aslug)
    return aslug

def strip_tags(text, valid_tags={}):
    """strip tags, remove invalid tag attrs.
    example::

        >>> strip_tags('this <a href="">xxx</a>')
        u'this xxx'

        >>> strip_tags('this <a href="">xxx</a>',{'a':'href'})
        u'this <a href="">xxx</a>'

    """
    from app.BeautifulSoup import BeautifulSoup, Comment

    soup = BeautifulSoup(text)
    for comment in soup.findAll(text=lambda text: isinstance(text, Comment)):
        comment.extract()
    for tag in soup.findAll(True):
        if tag.name in valid_tags:
            valid_attrs = valid_tags[tag.name]
            tag.attrs = [(attr, val.replace('javascript:', ''))
                for attr, val in tag.attrs if attr in valid_attrs]
        else:
            tag.hidden = True
    return soup.renderContents().decode('utf8')

def trim_excerpt(text):
    """Remove html tags and truncate the text. Max length is 120.
    example::

        >>> trim_excerpt_without_filters('this is a test <br>sss')
        u'this is a test sss'

    """
    MAXIMUM_DESCRIPTION_LENGTH = 120
    text = text.replace(']]>', ']]&gt;')
    text = re.sub( '|\[(.+?)\](.+?\[/\\1\])?|s', '', text )
    text = strip_tags(text)
    text = text.replace("\n", " ")
    max = MAXIMUM_DESCRIPTION_LENGTH

    if (max < len(text)):
        while( text[max] != ' ' and max > MAXIMUM_DESCRIPTION_LENGTH ):
            max -= 1
    text = text[:max]
    return text.strip()

def urldecode(value):
    """Decode the url string.
    """
    return  urllib.unquote(urllib.unquote(value)).decode('utf8')

def urlencode(value):
    """Encode the url string.
    """
    return urllib.quote(value.encode('utf8'))

def format_date(dt):
    """
    Format date as ``'%a, %d %b %Y %H:%M:%S GMT'``
    """
    return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')

def sid():
    """Get unique string as id. This id is based on the time of now.
    example::

        >>> sid()
        '110129154345718000'

    """
    import datetime
    now = datetime.datetime.now()
    return now.strftime('%y%m%d%H%M%S')+str(now.microsecond)