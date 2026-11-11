import sys
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sources import validate_url, single_video
from transcribe import resolve


class SourceTests(unittest.TestCase):
    def test_supported_platforms(self):
        for url in ['https://youtu.be/a', 'https://www.youtube.com/watch?v=a',
                    'https://www.instagram.com/reel/example/',
                    'https://www.facebook.com/watch/?v=123', 'https://fb.watch/abc/',
                    'https://m.facebook.com/reel/123']:
            self.assertEqual(validate_url(url), url)

    def test_untrusted_hosts_and_protocols(self):
        for url in ['https://instagram.com.evil.test/reel/a', 'file:///C:/test',
                    'javascript:alert(1)', 'https://user:pass@facebook.com/video', '']:
            with self.assertRaises(ValueError):
                validate_url(url)

    def test_post_collection_uses_first_playable(self):
        video = {'url': 'https://cdn.example/video.mp4', 'title': 'Video'}
        self.assertEqual(single_video({'entries': [None, {'title': 'Photo'}, video]}), video)

    def test_no_video_fails_clearly(self):
        for info in [None, {'entries': []}, {'title': 'No media'}]:
            with self.assertRaisesRegex(ValueError, 'video|audio'):
                single_video(info)

    def test_resolve_normalizes_instagram_collection(self):
        with patch('yt_dlp.YoutubeDL') as factory:
            factory.return_value.__enter__.return_value.extract_info.return_value = {
                'entries': [{'url': 'https://cdn.example/audio.mp4', 'title': 'Reel'}]}
            result = resolve('https://www.instagram.com/reel/example/', lambda: False)
            self.assertEqual(result['title'], 'Reel')
            self.assertTrue(factory.call_args.args[0]['noplaylist'])

    def test_blocked_source_points_to_fallback(self):
        from yt_dlp.utils import DownloadError
        with patch('yt_dlp.YoutubeDL') as factory:
            factory.return_value.__enter__.return_value.extract_info.side_effect = DownloadError('Login required')
            with self.assertRaisesRegex(RuntimeError, 'Computer audio'):
                resolve('https://www.facebook.com/watch/?v=123', lambda: False)


if __name__ == '__main__':
    unittest.main()
