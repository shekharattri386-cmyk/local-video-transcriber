# Local Video Transcriber

A Windows desktop app for transcribing video links, saved recordings, and computer playback audio locally with Whisper turbo. Saves timestamped text and SRT subtitles. Supports NVIDIA GPU inference and a slower CPU option.

## Input modes

| Mode | Use |
|---|---|
| Video link | YouTube videos/Shorts/live streams, Instagram video posts/reels, and Facebook video/reel/live links, when yt-dlp can resolve the media |
| Local file | Saved audio or video such as MP4, MKV, MOV, WAV, MP3, M4A and WebM |
| Computer audio | Windows WASAPI loopback: transcribe sound playing on the default speakers/headphones, including browser video |

Direct extraction is not guaranteed for every site or video. Login requirements, anti-bot protections, website changes and unsupported live formats can prevent it. Instagram Live is not guaranteed through a direct URL. Computer audio is the fallback for videos you can play normally in your browser; it does not import browser cookies or bypass access restrictions.

## Requirements

- Windows 10/11, 64-bit. The desktop launcher and loopback mode are Windows-specific.
- Python **3.12** with Tkinter, or [uv](https://docs.astral.sh/uv/) to acquire Python 3.12. Python 3.13+ is not supported because the loopback resampler uses `audioop`.
- [FFmpeg](https://ffmpeg.org/download.html) on PATH.
- [Node.js](https://nodejs.org/) on PATH for yt-dlp's YouTube JavaScript support; use a current supported release.
- For GPU mode: an NVIDIA CUDA-compatible GPU and current driver. GPU dependencies are installed into the virtual environment. Tested on an RTX 4060 Laptop GPU with 8 GB VRAM.
- Internet for installation, model download and video links; several GB of free disk space for dependencies, the cached model and pending audio.

You can install prerequisites with Windows Package Manager:

```powershell
winget install --id Python.Python.3.12 -e
winget install --id Gyan.FFmpeg -e
winget install --id OpenJS.NodeJS.LTS -e
```

Reopen PowerShell afterward so PATH changes take effect.

## Install and launch

```powershell
git clone https://github.com/shekharattri386-cmyk/local-video-transcriber.git
cd local-video-transcriber
powershell -ExecutionPolicy Bypass -File .\Setup.ps1 -DownloadModel
```

For a machine without a suitable NVIDIA GPU:

```powershell
powershell -ExecutionPolicy Bypass -File .\Setup.ps1 -CpuOnly -DownloadModel
```

Then double-click **Start.cmd**. CPU installations must select **cpu** in the app. Omitting `-DownloadModel` defers the download until the first run. This setup command uses a process-scoped PowerShell execution-policy option; it does not change your machine's policy permanently.

The setup uses pinned direct dependencies. `requirements-windows-gpu.lock.txt` records all package versions from the tested Windows GPU environment; it is a reference snapshot rather than a cross-platform lockfile.

## Use

1. Choose **Video link**, **Local file**, or **Computer audio**.
2. Paste a direct video URL or browse for a file. Computer audio needs no URL.
3. Choose `cuda` or `cpu`. Leave language blank for detection, or enter a code such as `en` or `hi`.
4. Click **Start transcription**. For computer audio, wait for the Capturing message, then play your video.
5. Click **Stop and save**, then **Open transcripts**.

Computer audio captures **all playback sound on the default Windows device**, including notifications and other apps. It does not capture the microphone. Keep other apps quiet and ensure the browser uses that same playback device. Restart capture if you change devices. Stop this mode yourself when the video ends.

Recorded links and local files finish automatically and may process faster than playback. Live capture begins near the current live position; it does not request the beginning of an ongoing broadcast. Supported upcoming-event errors trigger a retry every minute. Multi-item posts use the first playable video rather than transcribing an entire feed or playlist.

## Outputs

Every run creates a timestamped directory under `transcripts/`:

```text
transcripts/<session>/
  transcript.txt
  subtitles.srt
  session.json
  capture.log
```

Timestamps are elapsed captured audio, not the original live broadcast's timecode or wall-clock time. Processing uses roughly 30-second chunks; allow additional buffering and inference time. Chunk boundaries, mixed languages and unclear audio can produce omissions, repetition or recognition mistakes. This is transcription, not translation or speaker identification.

Completed audio chunks are removed after transcription. Incomplete/pending audio may remain after a failure. Previously written text remains saved. Long recordings can temporarily accumulate pending audio on disk. The app does not prevent Windows from sleeping.

## Command line

```powershell
& .venv\Scripts\python.exe transcribe.py --url 'https://www.youtube.com/watch?v=VIDEO_ID'
& .venv\Scripts\python.exe transcribe.py --file 'C:\recordings\meeting.mp4' --language en
& .venv\Scripts\python.exe transcribe.py --system-audio
& .venv\Scripts\python.exe transcribe.py --system-audio --seconds 60
& .venv\Scripts\python.exe transcribe.py --prepare --device cuda
```

The GUI's Stop button requests graceful capture shutdown. CLI Ctrl+C preserves already-written text but may skip pending audio. For offline local-file/computer-audio use after model download, set `$env:HF_HUB_OFFLINE = '1'` before launching the command.

## Privacy

Speech recognition runs on your computer; audio is not uploaded to a cloud speech API. Link mode contacts the source service. Model downloads use Hugging Face. The repository contains no recordings, transcripts, model weights, browser sessions or credentials. `capture.log` may include temporary media URLs, so inspect logs before sharing them.

## Troubleshooting

- **Direct link fails:** use Computer audio with normal browser playback, or transcribe a local recording.
- **No computer audio:** check default playback device and application audio routing; make sure video audio is enabled.
- **GPU error:** close other GPU-heavy apps, verify drivers, or select CPU. Whisper turbo can be much slower on CPU.
- **Network/expired stream URL:** capture attempts reconnects; if it fails, restart. A new session is saved separately.
- **Extractor changes:** update yt-dlp with `uv pip install --python .venv/Scripts/python.exe --upgrade 'yt-dlp[default]'`, or the equivalent `python -m pip` command inside the environment.
- **Missing environment:** run Setup.ps1 before Start.cmd. Recreate the environment after moving the installation to another machine.

## Development and validation

```powershell
& .venv\Scripts\python.exe -m unittest discover -s tests -v
& .venv\Scripts\python.exe -m py_compile app.py transcribe.py sources.py capture_audio.py
```

CI runs source-validation/resolver tests and compilation on Windows/Python 3.12. It does not need credentials, a GPU, model weights or audio hardware and does not test live platform availability.

Manual checks performed on the original Windows installation: GPU speech transcription, a 45-second Instagram reel sample, WASAPI speech capture/resampling/transcription, and stopping during silence. Facebook live extraction has not been verified with a specific stream. Tests do not imply universal website support.

## Components

- `app.py`: Tkinter interface and transcription-process controller.
- `sources.py`: supported-link validation and single-video selection.
- `transcribe.py`: source resolution, audio segmentation, Whisper inference and incremental text/SRT output.
- `capture_audio.py`: Windows loopback capture with silence handling and graceful stop.

Built with [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [yt-dlp](https://github.com/yt-dlp/yt-dlp), [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch), FFmpeg and NumPy. Model weights and dependencies have their own licenses; they are downloaded separately. Application source is MIT licensed.
