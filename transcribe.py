"""Local video/link/computer-audio transcription. No cloud speech API."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import wave

ROOT = Path(__file__).resolve().parent
os.environ.setdefault('HF_HOME', str(ROOT / 'models'))
os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')
os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
DLL_HANDLES = []


def prepare_gpu():
    if os.name == 'nt':
        for folder in (Path(sys.prefix) / 'Lib/site-packages/nvidia').glob('*/bin'):
            os.environ['PATH'] = str(folder) + os.pathsep + os.environ['PATH']
            DLL_HANDLES.append(os.add_dll_directory(str(folder)))


def stamp(seconds, srt=False):
    ms = max(0, round(seconds * 1000))
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    sec, ms = divmod(ms, 1000)
    return f'{hours:02}:{minutes:02}:{sec:02}{"," if srt else "."}{ms:03}'


def load_model(device):
    prepare_gpu()
    from faster_whisper import WhisperModel
    import numpy as np
    print(f'Loading Whisper turbo on {device}...', flush=True)
    model = WhisperModel('turbo', device=device,
                         compute_type='int8_float16' if device == 'cuda' else 'int8',
                         download_root=str(ROOT / 'models'), cpu_threads=6)
    # Exercise the decoder too: loading alone cannot detect missing CUDA DLLs.
    list(model.transcribe(np.zeros(16000, dtype=np.float32), language='en')[0])
    print(f'Model ready ({device}).', flush=True)
    return model


def resolve(url, stop):
    from sources import validate_url, single_video
    url = validate_url(url)
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError
    options = {'noplaylist': True, 'quiet': True,
               'format': 'bestaudio[protocol^=m3u8]/best[protocol^=m3u8]/bestaudio/best',
               'js_runtimes': {'node': {}}, 'socket_timeout': 20,
               'retries': 2, 'extractor_retries': 2}
    while not stop():
        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
            return single_video(info)
        except DownloadError as exc:
            if 'will begin' not in str(exc) and 'not started' not in str(exc):
                raise RuntimeError('The site could not provide playable video. It may require sign-in, '
                                   'be unavailable, or block direct extraction. Switch to Computer audio '
                                   'and play the video in your browser, or use a local video file.') from exc
            print('This event has not started. Checking again in 60 seconds...', flush=True)
            for _ in range(60):
                if stop():
                    return None
                time.sleep(1)
    return None


def run(args):
    stop_path = Path(args.stop_file) if args.stop_file else None
    stop = lambda: bool(stop_path and stop_path.exists())
    if not args.prepare:
        if args.file and not Path(args.file).is_file():
            raise ValueError('The selected local file does not exist.')
        if not args.file and not args.system_audio:
            from sources import validate_url
            validate_url(args.url)
    model = load_model(args.device)
    if args.prepare:
        return
    if stop():
        return
    if args.system_audio:
        source = None
        info = {'title': 'Computer audio', 'live_status': 'system_audio'}
        print('Capturing ALL sound on the default Windows playback device. '
              'Play your video there; keep other apps quiet. This does not capture the microphone.', flush=True)
    elif args.file:
        source = str(Path(args.file).resolve())
        info = {'title': Path(source).name, 'live_status': 'local_file'}
    else:
        info = resolve(args.url, stop)
        if info is None:
            print('Stopped before the stream began.', flush=True)
            return
        source = info['url']
    print(f'Source: {info.get("title")} ({info.get("live_status")})', flush=True)
    folder = ROOT / 'transcripts' / dt.datetime.now().strftime('%Y-%m-%d_%H-%M-%S_%f')
    chunks = folder / 'audio-pending'
    chunks.mkdir(parents=True)
    metadata = {key: info.get(key) for key in ('id', 'title', 'live_status', 'webpage_url')}
    metadata.update(started_at=dt.datetime.now().astimezone().isoformat(),
                    timestamp_basis='Audio elapsed since capture began; not original live broadcast time',
                    model='turbo', device=args.device, language=args.language)
    (folder / 'session.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(f'OUTPUT: {folder}', flush=True)
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg and not args.system_audio:
        raise RuntimeError('FFmpeg was not found on PATH. Install FFmpeg and restart this app.')
    command = [ffmpeg, '-hide_banner', '-loglevel', 'warning', '-y']
    if not args.file and not args.system_audio:
        command += ['-rw_timeout', '20000000', '-reconnect', '1', '-reconnect_streamed', '1',
                    '-reconnect_delay_max', '5']
        headers = info.get('http_headers', {})
        if headers:
            command += ['-headers', ''.join(f'{k}: {v}\r\n' for k, v in headers.items())]
    command += ['-i', source]
    if args.seconds:
        command += ['-t', str(args.seconds)]
    command += ['-map', '0:a:0', '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le',
                '-f', 'segment', '-segment_time', str(args.chunk_seconds),
                '-reset_timestamps', '1', str(chunks / '%08d.wav')]
    if args.system_audio:
        command = [sys.executable, '-W', 'ignore::DeprecationWarning', '-u',
                   str(ROOT / 'capture_audio.py'), '--output', str(chunks),
                   '--chunk-seconds', str(args.chunk_seconds)]
        if args.seconds:
            command += ['--seconds', str(args.seconds)]
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    elapsed = 0.0
    count = 0
    processed = set()
    interrupted = False
    process = None
    with (folder / 'capture.log').open('w', encoding='utf-8') as log, \
         (folder / 'transcript.txt').open('w', encoding='utf-8', buffering=1) as txt, \
         (folder / 'subtitles.srt').open('w', encoding='utf-8', buffering=1) as srt:
        txt.write(f'{info.get("title")}\nTimestamps: elapsed audio from capture start.\n\n')

        def consume(path):
            nonlocal elapsed, count
            # FFmpeg finalizes each WAV header when closing the segment.
            with wave.open(str(path), 'rb') as audio:
                duration = audio.getnframes() / audio.getframerate()
                if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 16000):
                    raise RuntimeError('Expected mono 16-bit 16 kHz PCM from FFmpeg.')
                import numpy as np
                samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype='<i2').astype(np.float32) / 32768.0
            if duration <= 0:
                return
            started = time.monotonic()
            segments, detected = model.transcribe(samples, language=args.language or None,
                                                  beam_size=3, vad_filter=True,
                                                  condition_on_previous_text=False)
            for segment in segments:
                text = segment.text.strip()
                if not text:
                    continue
                start = elapsed + max(0, segment.start)
                end = elapsed + min(duration, segment.end)
                if end <= start:
                    continue
                count += 1
                line = f'[{stamp(start)}] {text}'
                print(line, flush=True)
                txt.write(line + '\n')
                srt.write(f'{count}\n{stamp(start, True)} --> {stamp(end, True)}\n{text}\n\n')
            elapsed += duration
            print(f'Processed {duration:.1f}s audio in {time.monotonic()-started:.1f}s '
                  f'(language: {detected.language}).', flush=True)
            processed.add(path.name)
            path.unlink()

        try:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                       stderr=log, creationflags=creationflags)
            print(f'Capturing audio; text updates about every {args.chunk_seconds} seconds. '
                  'Use Stop to finish and save.', flush=True)
            stop_sent = None
            while True:
                if stop() and stop_sent is None:
                    interrupted = True
                    stop_sent = time.monotonic()
                    if process.poll() is None:
                        try:
                            process.stdin.write(b'q\n')
                            process.stdin.flush()
                        except (BrokenPipeError, OSError):
                            pass
                if stop_sent and process.poll() is None and time.monotonic()-stop_sent > 8:
                    process.terminate()
                    process.wait(timeout=10)
                done = process.poll() is not None
                pending = sorted(p for p in chunks.glob('*.wav') if p.name not in processed)
                ready = pending if done else pending[:-1]
                for path in ready:
                    try:
                        consume(path)
                    except (EOFError, wave.Error):
                        if interrupted:
                            print(f'Incomplete final audio retained: {path.name}', flush=True)
                        else:
                            raise
                if done:
                    if process.returncode != 0 and not interrupted:
                        raise RuntimeError(f'Audio capture failed (code {process.returncode}). '
                                           f'See {folder / "capture.log"}. Existing text is saved. '
                                           'For a blocked link, use Computer audio and play the video in your browser.')
                    break
                time.sleep(0.25)
        finally:
            if process and process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            if process and process.stdin:
                process.stdin.close()
    if not any(chunks.iterdir()):
        chunks.rmdir()
    print(f'Saved {count} subtitle segments ({elapsed:.1f}s audio) to {folder}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument('--url', help='YouTube, Instagram, Facebook video/live link')
    inputs.add_argument('--file', help='Transcribe a local audio/video file instead')
    inputs.add_argument('--system-audio', action='store_true', help='Capture default Windows playback audio')
    parser.add_argument('--language', default='', help='Language code, e.g. en or hi; blank = detect')
    parser.add_argument('--device', choices=['cuda', 'cpu'], default='cuda')
    parser.add_argument('--chunk-seconds', type=int, default=30)
    parser.add_argument('--seconds', type=int, help='Stop after this many seconds of captured audio')
    parser.add_argument('--stop-file', help='Stop when this file appears')
    parser.add_argument('--prepare', action='store_true', help='Download and verify the model only')
    args = parser.parse_args()
    if not args.prepare and not (args.url or args.file or args.system_audio):
        parser.error('Choose --url, --file, or --system-audio.')
    if args.chunk_seconds < 5 or (args.seconds is not None and args.seconds < 1):
        parser.error('Chunk duration must be at least 5 seconds; capture limit must be positive.')
    try:
        run(args)
    except KeyboardInterrupt:
        print('Interrupted. Previously written transcript remains saved.', flush=True)
        return 130
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
