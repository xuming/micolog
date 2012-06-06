# -*- coding: utf-8 -*-
"""
    A Python HTML filtering library - html_filter.py, v 1.15.4

    Translated to Python by Samuel Adam <samuel.adam@gmail.com>
    http://amisphere.com/contrib/python-html-filter/
    
    
    Original PHP code ( lib_filter.php, v 1.15 ) by Cal Henderson  <cal@iamcal.com>
    
    http://iamcal.com/publish/articles/php/processing_html/
    http://iamcal.com/publish/articles/php/processing_html_part_2/
    
    This code is licensed under a Creative Commons Attribution-ShareAlike 2.5 License
    http://creativecommons.org/licenses/by-sa/2.5/

"""
    
import re
from cgi import escape
from HTMLParser import HTMLParser

class html_filter:
    """
    html_filter removes HTML tags that do not belong to a white list
                closes open tags and fixes broken ones
                removes javascript injections and black listed URLs
                makes text URLs and emails clickable
                adds rel="no-follow" to links except for white list
                
    default settings are based on Flickr's "Some HTML is OK"
    http://www.flickr.com/html.gne
                

    HOWTO
    
    1. Basic example
    
        from html_filter import html_filter
        filter = html_filter()
        
        #change settings to meet your needs
        filter.strip_comments = False
        filter.allowed['br'] = ()
        filter.no_close += 'br',
        
        raw_html = '<p><strong><br><!-- Text to filter !!!<div></p>'
        
        # go() is a shortcut to apply the most common methods
        filtered_html = filter.go(raw_html)
        
        # returns <strong><br />&lt;!-- Text to filter !!!</strong>
    
    
    2. You can only use one method at a time if you like
        
        from html_filter import html_filter
        filter = html_filter()
                
        please_dont_scream_this_is_a_pop_contest = filter.fix_case('HARD ROCK ALELUYAH!!!')
        # returns Hard rock aleluyah!!!
        
        filter.break_words_longer_than = 30
        wordwrap_text = filter.break_words('MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM...')
        # adds html entity "&#8203;" (zero width space) each 30 characters
    
    """
    
    def __init__(self):

        ### START Default Config ###
        
        # tags and attributes that are allowed
        self.allowed = {
            'a': ('href', 'target'), 
            'b': (), 
            'blockquote': (), 
            'em': (), 
            'i': (), 
            'img': ('src', 'width', 'height', 'alt', 'title'), 
            'strong': (), 
            'u': (), 
        }
    
        # tags which should always be self-closing (e.g. "<img />")
        self.no_close = (
            'img',
        )
        
        # tags which must always have seperate opening and closing tags (e.g. "<b></b>")
        self.always_close = (
            'a', 
            'b', 
            'blockquote', 
            'em', 
            'i', 
            'strong', 
            'u', 
        )

        # tags which should be removed if they contain no content (e.g. "<b></b>" or "<b />")
        self.remove_blanks = (
            'a', 
            'b', 
            'blockquote', 
            'em', 
            'i', 
            'strong', 
            'u', 
        )
        
        # attributes which should be checked for valid protocols
        self.protocol_attributes = (
            'src', 
            'href', 
        )
    
        # protocols which are allowed
        self.allowed_protocols = (
            'http', 
            'https', 
            'ftp', 
            'mailto', 
        )
        
        # forbidden urls ( regular expressions ) are replaced by #
        self.forbidden_urls = (
            r'^/delete-account',     
            r'^domain.ext/delete-account',     
        )

        # should we make urls clickable ?
        self.make_clickable_urls = True     

        # should we add a rel="nofollow" to the links ?
        self.add_no_follow = True
        
        # except for those domains
        self.follow_for = (
               'allowed-domain.ext',
       )
        
        # should we remove comments?
        self.strip_comments = True
        
        # should we removes blanks from beginning and end of data ?
        self.strip_data = True
    
        # should we try and make a b tag out of "b>"
        self.always_make_tags = False  
    
        # entity control options
        self.allow_numbered_entities = True
    
        self.allowed_entities = (
            'amp', 
            'gt', 
            'lt', 
            'quot', 
        )
        
        # should we "break" words longer than x chars ( 0 means "No", minimum is 8 chars )
        self.break_words_longer_than = 0        
        
        ### END Default Config ###

        # INIT
        
        self.tag_counts = {}

        # pre-compile some regexp patterns
        self.pat_entities = re.compile(r'&([^&;]*)(?=(;|&|$))')
        self.pat_quotes = re.compile(r'(>|^)([^<]+?)(<|$)', re.DOTALL|re.IGNORECASE)
        self.pat_valid_entity = re.compile(r'^#([0-9]+)$', re.IGNORECASE)
        self.pat_decode_entities_dec = re.compile(r'(&)#(\d+);?')
        self.pat_decode_entities_hex = re.compile(r'(&)#x([0-9a-f]+);?', re.IGNORECASE)
        self.pat_decode_entities_hex2 = re.compile(r'(%)([0-9a-f]{2});?', re.IGNORECASE)
        self.pat_entities2 = re.compile(r'&([^&;]*);?', re.IGNORECASE)
        self.pat_raw_url = re.compile('(('+'|'.join(self.allowed_protocols)+')://)(([a-z0-9](?:[a-z0-9\\-]*[a-z0-9])?\\.)+(com\\b|edu\\b|biz\\b|gov\\b|in(?:t|fo)\\b|mil\\b|net\\b|org\\b|[a-z][a-z]\\b)|((25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9])\\.(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9]|0)\\.(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9]|0)\\.(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[0-9])))(:\\d+)?(/[-a-z0-9_:\\\\@&?=+,\\.!/~*\'%\\$]*)*(?<![.,?!])(?!((?!(?:<a )).)*?(?:</a>))(?!((?!(?:<!--)).)*?(?:-->))', re.IGNORECASE)
        
#

    def go(self, data):
        
        data = self.strip_whitespace(data)
        data = self.escape_comments(data)
        data = self.balance_html(data)
        data = self.clickable_urls(data)
        data = self.check_tags(data)
        data = self.process_remove_blanks(data)
        data = self.validate_entities(data)
        data = self.break_words(data)
        

        
        return data
          
#

    def strip_whitespace(self, data):
        if self.strip_data:
            data = data.strip()
        return data
#
    
    def escape_comments(self, data):
        pat = re.compile(r'<!--(.*?)-->', re.IGNORECASE)
        data = re.sub(pat, self.f0, data)
        return data
    def f0(self, m):
        return '<!--'+escape(m.group(1), True)+'-->'
    
#
    
    def balance_html(self, data):
        # try and form html
        if self.always_make_tags:
            data = re.sub(r'>>+', r'>', data)
            data = re.sub(r'<<+', r'<', data)
            data = re.sub(r'^>', r'', data)
            data = re.sub(r'<([^>]*?)(?=<|$)', r'<\1>', data)
            data = re.sub(r'(^|>)([^<]*?)(?=>)', r'\1<\2', data)
        else:
            data = data.replace('<>', '&lt;&gt;') # <> as text
            data = self.re_sub_overlap(r'<([^>]*?)(?=<|$)', r'&lt;\1', data)
            data = self.re_sub_overlap(r'(^|>)([^<]*?)(?=>)', r'\1\2&gt;<', data)
            data = re.sub(r'<(\s)+?', r'&lt;\1', data) # consider "< a href" as "&lt; a href"
            # this filter introduces an error, so we correct it
            data = data.replace('<>', '')
        return data

    # python re.sub() doesn't overlap matches
    def re_sub_overlap(self, pat, repl, data, i=0):
        data_temp = re.sub(pat, repl, data[i:])
        if data_temp != data[i:]:
            data = data[:i] + data_temp
            i += 1
            data = self.re_sub_overlap(pat, repl, data, i)
        return data

#

    def clickable_urls(self, data):
        if self.make_clickable_urls:
            # urls
#            pat = re.compile('(('+'|'.join(self.allowed_protocols)+')://)(([a-z0-9](?:[a-z0-9\\-]*[a-z0-9])?\\.)+(com\\b|edu\\b|biz\\b|gov\\b|in(?:t|fo)\\b|mil\\b|net\\b|org\\b|[a-z][a-z]\\b)|((25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9])\\.(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9]|0)\\.(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9]|0)\\.(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[0-9])))(:\\d+)?(/[-a-z0-9_:\\\\@&?=+,\\.!/~*\'%\\$]*)*(?<![.,?!])(?!((?!(?:<a )).)*?(?:</a>))(?!((?!(?:<!--)).)*?(?:-->))', re.IGNORECASE)
            data = re.sub(self.pat_raw_url, self.f7, data)
            # emails
            if 'mailto' in self.allowed_protocols:
                pat = re.compile(r'((([a-z]|[0-9]|!|#|$|%|&|\'|\*|\+|\-|/|=|\?|\^|_|`|\{|\||\}|~)+(\.([a-z]|[0-9]|!|#|$|%|&|\'|\*|\+|\-|/|=|\?|\^|_|`|\{|\||\}|~)+)*)@((((([a-z]|[0-9])([a-z]|[0-9]|\-){0,61}([a-z]|[0-9])\.))*([a-z]|[0-9])([a-z]|[0-9]|\-){0,61}([a-z]|[0-9])\.(com|edu|gov|int|mil|net|org|biz|info|name|pro|aero|coop|museum|arpa|[a-z]{2}))|(((([0-9]){1,3}\.){3}([0-9]){1,3}))|(\[((([0-9]){1,3}\.){3}([0-9]){1,3})\])))(?!((?!(?:<a )).)*?(?:</a>))(?!((?!(?:<!--)).)*?(?:-->))', re.IGNORECASE)
                data = re.sub(pat, self.f8, data)
        return data
    
    def f7(self, m):          
        return '<a href="'+m.group(0)+'">'+m.group(0)+'</a>'
    def f8(self, m):          
        return '<a href="mailto:'+m.group(0)+'">'+m.group(0)+'</a>'
           
#

    def check_tags(self, data):
        # compile loop regexps
        self.pat_end_tag = re.compile(r'^/([a-z0-9]+)', re.DOTALL|re.IGNORECASE)
        self.pat_start_tag = re.compile(r'^([a-z0-9]+)(.*?)(/?)$', re.DOTALL|re.IGNORECASE)
        self.pat_matches_2 = re.compile(r'([a-z0-9]+)=(["\'])(.*?)\2', re.DOTALL|re.IGNORECASE)           # <foo a="b" />
        self.pat_matches_1 = re.compile(r'([a-z0-9]+)(=)([^"\s\']+)', re.DOTALL|re.IGNORECASE)            # <foo a=b />
        self.pat_matches_3 = re.compile(r'([a-z0-9]+)=(["\'])([^"\']*?)\s*$', re.DOTALL|re.IGNORECASE)    # <foo a="b />
        self.pat_comments = re.compile(r'^!--(.*)--$', re.DOTALL|re.IGNORECASE)
        self.pat_param_protocol = re.compile(r'^([^:]+):', re.DOTALL|re.IGNORECASE)
        
        pat = re.compile(r'<(.*?)>', re.DOTALL) 
        data = re.sub(pat, self.f1, data)

        for tag in self.tag_counts:
            count = self.tag_counts[tag]
            for i in range(count):
                data += '</'+tag+'>'
        self.tag_counts = {}

        return data
    
    def f1(self, m):
        return self.process_tag(m.group(1))
        
#

    def process_tag(self, data):

        # ending tags        
        m = re.match(self.pat_end_tag, data)
        if m:
            name = m.group(1).lower()
            if name in self.allowed:
                if name not in self.no_close:
                    if self.tag_counts.has_key(name):
                        self.tag_counts[name] -= 1
                        return '</' + name + '>'
            else:
                return ''
        
        # starting tags
        m = re.match(self.pat_start_tag, data)
        if m:
            name = m.group(1).lower()
            body = m.group(2)
            ending = m.group(3)
            
            if name in self.allowed:
                params = ''
                matches_2 = re.findall(self.pat_matches_2, body)    # <foo a="b" />
                matches_1 = re.findall(self.pat_matches_1, body)    # <foo a=b />
                matches_3 = re.findall(self.pat_matches_3, body)    # <foo a="b />
                
                matches = {}
                
                for match in matches_3:
                    matches[match[0].lower()] = match[2]
                for match in matches_1:
                    matches[match[0].lower()] = match[2]
                for match in matches_2:
                    matches[match[0].lower()] = match[2]
                    
                for pname in matches:
                    if pname in self.allowed[name]:
                        value = matches[pname]
                        if pname in self.protocol_attributes:
                            processed_value = self.process_param_protocol(value)
                            # add no_follow
                            if self.add_no_follow and name== 'a' and pname == 'href' and processed_value == value:
                                processed_value = re.sub(self.pat_raw_url, self.f9, processed_value)
                            value = processed_value
                        params += ' '+pname+'="'+value+'"'
                
                if name in self.no_close:
                    ending = ' /'
                
                if name in self.always_close:
                    ending = ''

                if not ending:
                    if self.tag_counts.has_key(name):
                        self.tag_counts[name] += 1
                    else:
                        self.tag_counts[name] = 1
                
                if ending:
                    ending = ' /'
                    
                return '<'+name+params+ending+'>'
            
            else:
                return ''
                    
        # comments
        m = re.match(self.pat_comments, data)
        
        if m:
            if self.strip_comments:
                return ''
            else:
                return '<'+data+'>'

        # garbage, ignore it
        return ''

    def f9(self, m):
        if m.group(3) not in self.follow_for:
            return m.group()+'" rel="no-follow'
        return m.group()
#

    def process_param_protocol(self, data):

        data = self.decode_entities(data)
        
        m = re.match(self.pat_param_protocol, data)
        if m:
            if not m.group(1) in self.allowed_protocols:
                start = len(m.group(1)) + 1
                data = '#' + data[start:]
        
        # remove forbidden urls
        for pat in self.forbidden_urls:
            m = re.search(pat, data)
            if m:
                data = '#'
        
        return data

#

    def process_remove_blanks(self, data):
        
        for tag in self.remove_blanks:
            data = re.sub(r'<'+tag+'(\s[^>]*)?></'+tag+'>', r'', data)
            data = re.sub(r'<'+tag+'(\s[^>]*)?/>', r'', data)
            
        return data
    
#

    def strip_tags(self, html):
        result = []
        parser = HTMLParser()
        parser.handle_data = result.append
        parser.feed(html)
        parser.close()
        return ''.join(result)
    

    def fix_case(self, data):
        
        # compile loop regexps
        self.pat_case_inner = re.compile(r'(^|[^\w\s\';,\\-])(\s*)([a-z])')
        
        data_notags = self.strip_tags(data)
        data_notags = re.sub(r'[^a-zA-Z]', r'', data_notags)
        
        if len(data_notags) < 5:
            return data

        m = re.search(r'[a-z]', data_notags)
        if m:
            return data
        
        pat = re.compile(r'(>|^)([^<]+?)(<|$)', re.DOTALL)
        data = re.sub(pat, self.f2, data)

        return data

    def f2(self, m):
        return m.group(1)+self.fix_case_inner(m.group(2))+m.group(3)
    
    def fix_case_inner(self, data):
        return re.sub(self.pat_case_inner, self.f3, data.lower())
    
    def f3(self, m):
        return m.group(1)+m.group(2)+m.group(3).upper()

#

    def validate_entities(self, data):        
        # validate entities throughout the string
        data = re.sub(self.pat_entities, self.f4, data)
        # validate quotes outside of tags
        data = re.sub(self.pat_quotes, self.f5, data)
        return data

    def f4(self, m):
        return self.check_entity(m.group(1), m.group(2))
    
    def f5(self, m):
        return m.group(1)+m.group(2).replace('"', '&quot;')+m.group(3)

#

    def check_entity(self, preamble, term):
        
        if term != ';':
            return '&amp;'+preamble
        
        if self.is_valid_entity(preamble):
            return '&'+preamble
        
        return '&amp;'+preamble

    def is_valid_entity(self, entity):
        
        m = re.match(self.pat_valid_entity, entity)
        if m:
            if int(m.group(1)) > 127:
                return True
            
            return self.allow_numbered_entities
        
        if entity in self.allowed_entities:
            return True
        
        return False

#

    # within attributes, we want to convert all hex/dec/url escape sequences into
    # their raw characters so that we can check we don't get stray quotes/brackets
    # inside strings
    
    def decode_entities(self, data):
        
        data = re.sub(self.pat_decode_entities_dec, self.decode_dec_entity, data)
        data = re.sub(self.pat_decode_entities_hex, self.decode_hex_entity, data)
        data = re.sub(self.pat_decode_entities_hex2, self.decode_hex_entity, data)
        
        data = self.validate_entities(data)
        
        return data
    
    
    def decode_hex_entity(self, m):
        
        return self.decode_num_entity(m.group(1), int(m.group(2), 16))

    def decode_dec_entity(self, m):
        
        return self.decode_num_entity(m.group(1), int(m.group(2)))

    def decode_num_entity(self, orig_type, d):
        
        if d < 0:
            d = 32 # space
        
        if d > 127:
            if orig_type == '%':
                return '%' + hex(d)[2:]
            if orig_type == '&':
                return '&#'+str(d)+';'
            
        return escape(chr(d))

#

    def break_words(self, data):
        if self.break_words_longer_than > 0:
            pat = re.compile(r'(>|^)([\s]*)([^<]+?)([\s]*)(<|$)', re.DOTALL)
            data = re.sub(pat, self.f6, data)
        return data

    def f6(self, m):
        return m.group(1)+m.group(2)+self.break_text(m.group(3))+m.group(4)+m.group(5)
    
    def break_text(self, text):
        ret = ''
        entity_max_length = 8
        if self.break_words_longer_than < entity_max_length:
            width = entity_max_length
        else:
            width = self.break_words_longer_than
            
        for word in text.split(' '):
            if len(word) > width:
                word = word.replace('&#8203;','')
                m = re.search(self.pat_entities2, word[width-entity_max_length:width+entity_max_length])
                if m:
                    width = width - entity_max_length + m.end()
                ret += word[0:width] + '&#8203;' + self.break_text(word[width:]) # insert "Zero Width" Space - helps wordwrap
            else:
                ret += word + ' '
        return ret.strip()
    
