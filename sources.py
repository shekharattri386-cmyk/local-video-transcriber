"""Input validation and single-video selection shared by UI and engine."""
from urllib.parse import urlsplit


def validate_url(value):
    parsed = urlsplit(value.strip())
    domains = ('youtube.com', 'youtu.be', 'instagram.com', 'facebook.com', 'fb.watch', 'fb.com')
    host = (parsed.hostname or '').lower()
    if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
        raise ValueError('Paste an https:// video link from YouTube, Instagram, or Facebook.')
    if not any(host == domain or host.endswith('.' + domain) for domain in domains):
        raise ValueError('Supported links: YouTube, Instagram, Facebook, and fb.watch.')
    return value.strip()


def single_video(info):
    if not info:
        raise ValueError('The site returned no video. Try Computer audio while playing it in your browser.')
    if info.get('entries') is not None:
        for entry in info['entries']:
            if entry and (entry.get('url') or entry.get('formats')):
                print('This post contains multiple items; using the first playable video.', flush=True)
                return single_video(entry)
        raise ValueError('No playable video in this post. Photo-only posts cannot be transcribed.')
    if not info.get('url'):
        raise ValueError('No playable audio URL. Try Computer audio while playing the video in your browser.')
    return info
