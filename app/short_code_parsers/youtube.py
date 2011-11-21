from django.template import Template, Context
from django.conf import settings
from urlparse import urlparse 

def parse(kwargs, content):
    if content[0:7] == 'http://':
        d = dict([x.split("=") for x in urlparse(content)[4].split("&")])
        video_id = ''
        if d.has_key('v'):
            video_id = d['v']
    else:
        video_id = content
    
    width = int(kwargs.get('width', getattr(settings, 'SHORTCODES_YOUTUBE_WIDTH', 425)))
    height = int(kwargs.get('height', 0))
    if height == 0:
        height = int(round(width / 425.0 * 344.0))
    
    html = '<object width="{{ width }}" height="{{ height }}">'
    html += '<param name="movie" value="http://www.youtube.com/v/{{ video_id }}&hl=en&fs=1"></param>'
    html += '<param name="allowFullScreen" value="true"></param>'
    html += '<param name="allowscriptaccess" value="always"></param>'
    html += '<embed src="http://www.youtube.com/v/{{ video_id }}&hl=en&fs=1" type="application/x-shockwave-flash" allowscriptaccess="always" allowfullscreen="true" width="{{ width }}" height="{{ height }}"></embed>'
    html += '</object>'

    template = Template(html)
    context = Context(
        {
            'video_id': video_id,
            'width': width,
            'height': height
        }
    )
    
    if id:
        return template.render(context)
    else:
        return 'Video not found'