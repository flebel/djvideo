import re
from django.conf import settings
from django.template import Context, Library, Node, Variable, loader, \
    TemplateSyntaxError

register = Library()

def _get_variable_or_string(name):
    if name[0] in '"\'':
        return name[1:-1]
    else:
        return Variable(name)

ACCEPTED_KEYS = ('title', 'width', 'height', 'autoplay', 'mime_type')

DEFAULT_CONTEXT = {
    'height': 360,
    'width': 480,
    'autoplay': True,
    'settings': settings
    }

OGG_MIME_TYPES = ('application/ogg', 'video/ogg', 'audio/ogg')
QUICKTIME_MIME_TYPES = ('video/mp4', 'video/quicktime', 'video/x-m4v',
                        'video/mpeg', 'video/m4v', 'video/mov',
                        'video/x-mp4')

SUPPORTS_VIDEO_TAG = [
    (re.compile('(Firefox|Shiretoko)/3\.[1-9].*'), OGG_MIME_TYPES),
    (re.compile('Chrome/3\.0\.1(8[2-9]|9)'), # Chrome comes first because it
     OGG_MIME_TYPES + QUICKTIME_MIME_TYPES), # also reports as Safari
    (re.compile('Safari/(52[6-9]|5[3-9][0-9])\.'), QUICKTIME_MIME_TYPES)
    ]

EMBED_MAPPING = {
    'video/mp4': 'quicktime.html',
    'video/quicktime': 'quicktime.html',
    'video/x-m4v': 'quicktime.html',
    'video/mpeg': 'quicktime.html',
    'video/m4v': 'quicktime.html',
    'video/mov': 'quicktime.html',
    'video/x-mp4': 'quicktime.html',
    'application/x-shockwave-flash': 'flash.html',
    'video/x-flv': 'flash.html',
    'video/flv': 'flash.html',
}

if getattr(settings, 'XSPF_PLAYER_URL'):
    EMBED_MAPPING.update({
    'audio/mpeg': 'mp3.html',
    'audio/x-m4a': 'mp3.html',
    'audio/mp4': 'mp3.html',
    'audio/mp3': 'mp3.html',
    })

if getattr(settings, 'FLOWPLAYER_SWF_URL', False) and \
        getattr(settings, 'FLOWPLAYER_JS_URL', False):
    EMBED_MAPPING.update({
            'video/mp4': 'flowplayer.html',
            'video/x-mp4': 'flowplayer.html',
            'video/m4v': 'flowplayer.html',
            'video/x-m4v': 'flowplayer.html',
            'video/x-flv': 'flowplayer.html',
            'video/flv': 'flowplayer.html',

            })

YOUTUBE_VIDEO_RE = re.compile(r'http://(www.)?youtube.com/watch\?v=(?P<id>.+)')

class VideoNode(Node):
    def __init__(self, context):
        self.context = context

    def render(self, context):
        new_context = Context()
        new_context.dicts.extend(context.dicts)

        for key, value in self.context.items():
            if isinstance(value, Variable):
                new_context[key] = value.resolve(context)
            else:
                new_context[key] = value

        match = YOUTUBE_VIDEO_RE.match(new_context['url'])
        if match:
            url = 'http://www.youtube.com/v/%s&hl=en&fs=1' % match.group('id')
            new_context['url'] = url
            new_context['mime_type'] = 'video/flv'

        mime_type = new_context.get('mime_type')
        template_name = EMBED_MAPPING.get(mime_type, 'default.html')
        template = loader.get_template('djvideo/%s' % template_name)
        rendered = template.render(new_context)
        user_agent = context['request'].META.get('HTTP_USER_AGENT')
        for regexp, mime_types in SUPPORTS_VIDEO_TAG:
            if mime_type in mime_types:
                if regexp.search(user_agent):
                    new_context['fallback'] = rendered
                    template = loader.get_template('djvideo/videotag.html')
                    return template.render(new_context)
        return rendered


@register.tag
def video(parser, token):
    token_contents = token.split_contents()
    tag_name = token_contents[0]
    context = DEFAULT_CONTEXT.copy()
    if len(token_contents) < 2:
        raise TemplateSyntaxError(
            '%s tag requires at least one argument' % tag_name)
    context['url'] = _get_variable_or_string(token_contents[1])
    for parts in token_contents[2:]:
        name, value = parts.split('=')
        if name not in ACCEPTED_KEYS:
            raise TemplateSyntaxError(
                '%s tag does not accept the %r keyword' % (
                    tag_name, name))
        context[name.strip()] = _get_variable_or_string(value)

    return VideoNode(context)
