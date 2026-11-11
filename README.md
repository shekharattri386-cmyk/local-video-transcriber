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

This is a fresh-machine installation guide: you do not need the original developer's Python environment, model cache, Codex installation, or paid AI account. However, the current app is **not supported on every operating system**.

- Windows 10/11 on **x86-64 (Intel/AMD)**. Windows ARM, macOS and Linux are not supported/tested by this desktop package. The launcher, process handling and WASAPI capture are Windows-specific.
- Python **3.12** with Tkinter, or [uv](https://docs.astral.sh/uv/) to acquire Python 3.12. Python 3.13+ is not supported because the loopback resampler uses `audioop`.
- [FFmpeg](https://ffmpeg.org/download.html) on PATH.
- [Node.js](https://nodejs.org/) **22 or newer** on PATH for yt-dlp's YouTube JavaScript support; a current LTS release is recommended. See [yt-dlp's runtime requirements](https://github.com/yt-dlp/yt-dlp/wiki/EJS).
- Microsoft Visual C++ Redistributable **v14 x64** (2015–2022 or its current compatible update). This is often preinstalled, but is required by native dependencies; see [CTranslate2's Windows installation requirements](https://opennmt.net/CTranslate2/installation.html).
- PowerShell and a writable installation folder, such as a folder under Documents. Avoid installing into Program Files.
- Git if using `git clone`; alternatively download and extract the repository ZIP from GitHub's **Code → Download ZIP** menu.
- For GPU mode: an NVIDIA CUDA-compatible GPU and current driver. GPU dependencies are installed into the virtual environment. Tested on an RTX 4060 Laptop GPU with 8 GB VRAM.
- Internet for installation, model download and video links; several GB of free disk space for dependencies, the cached model and pending audio.

### Hardware planning

These are practical starting recommendations, not measured minimum requirements:

| Resource | Guidance |
|---|---|
| RAM | 16 GB recommended for comfortable use alongside a browser; lower-memory configurations have not been benchmarked |
| Free storage | Start with at least 10 GB free for packages, download caches, model weights and temporary audio; long sessions may need more |
| NVIDIA GPU | 8 GB VRAM is the tested configuration; smaller GPUs have not been validated |
| CPU-only computer | Supported installation option; speed depends on the CPU and may fall behind live playback |
| AMD/Intel graphics | Use CPU mode in this package; it does not configure ROCm, DirectML or Intel GPU inference |
| Playback device | Computer-audio mode needs an enabled default Windows speaker/headphone device and functioning audio drivers |

No microphone, API key, Hugging Face account, Codex, Docker, or separately installed PyTorch is required for the normal workflow. GPU setup installs the NVIDIA runtime libraries used by the application, but **does not install or update your NVIDIA display driver**. A separate full CUDA development toolkit is not part of this install procedure.

You can install prerequisites with Windows Package Manager:

```powershell
winget install --id Python.Python.3.12 -e
winget install --id Gyan.FFmpeg -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id Microsoft.VCRedist.2015+.x64 -e
winget install --id Git.Git -e
```

Reopen PowerShell afterward so PATH changes take effect.

If `winget` is unavailable, use the publishers' installers: [Python 3.12 Windows releases](https://www.python.org/downloads/windows/), [FFmpeg](https://ffmpeg.org/download.html), [Node.js](https://nodejs.org/), [Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist), and [Git for Windows](https://git-scm.com/download/win). With the Python installer, include the Python launcher, pip and Tcl/Tk. Add FFmpeg's `bin` folder to PATH. Git is optional when using the ZIP download.

### Check prerequisites before setup

For the Python-installer route, run these in a newly opened PowerShell:

```powershell
py -3.12 --version
py -3.12 -c "import tkinter, audioop; print('Python GUI and audio modules available')"
ffmpeg -version
node --version
git --version
```

Python should report 3.12.x, Node should report v22 or later, and FFmpeg should print its version. Skip the Git check if you downloaded the ZIP. With uv, check `uv --version` instead of the two Python commands; Setup.ps1 will create and validate its Python 3.12 environment. For NVIDIA mode, also run `nvidia-smi`; if it fails, install/update the NVIDIA driver or use CPU mode.

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

### What Setup.ps1 installs

| Installed or checked by the script | Must be installed separately |
|---|---|
| Creates `.venv` with Python 3.12 (uv can acquire Python; otherwise uses `py -3.12`) | PowerShell and either uv or Python 3.12 with its launcher |
| Installs faster-whisper, NumPy, yt-dlp with its default extras, PyAudioWPatch and their Python dependencies | FFmpeg and Node.js; setup checks that both are on PATH even for CPU installs |
| Adds cuBLAS, CUDA NVRTC and cuDNN Python packages in GPU mode | NVIDIA driver for GPU mode; Microsoft Visual C++ runtime |
| With `-DownloadModel`, downloads Whisper turbo and runs an inference check on the selected device | Internet access and sufficient free disk space |

Setup does not copy any recordings or transcripts from another machine. It does not automatically create a desktop shortcut. It leaves the GUI's initial device selection on `cuda`, so **select `cpu` after a CPU-only installation**.

### Verify installation

From the repository folder:

```powershell
& .venv\Scripts\python.exe -m pip --version
```

The pip check is optional: uv-created environments may not include pip. The checks that matter are:

```powershell
& .venv\Scripts\python.exe -c "import tkinter, numpy, faster_whisper, yt_dlp, pyaudiowpatch; print('Application dependencies import successfully')"
& .venv\Scripts\python.exe transcribe.py --prepare --device cpu
```

For an NVIDIA installation, replace `cpu` with `cuda` in the second command. Model preparation must finish with `Model ready (...)`. It may download weights on first use. Then launch Start.cmd and transcribe a short local recording; confirm that text and SRT files appear under `transcripts/`. This checks the actual machine, beyond package installation alone.

### Moving to another computer

Clone/download the source on the new computer and rerun prerequisites and Setup.ps1. Do not copy `.venv` or the desktop shortcut: the environment and shortcut refer to machine-specific paths. Model weights are downloaded automatically; optionally copy the complete `models/` folder to the same relative location to reuse the cache. Transfer `transcripts/` separately only if you want your existing output files on the new machine.

For reproducibility, the original verified environment used Python 3.12.13, FFmpeg 8.1.1, Node.js 26.12.1 and an NVIDIA RTX 4060 Laptop GPU with 8 GB VRAM. These are tested versions, not a requirement to own identical hardware. Automated Windows CI verifies code/tests; it does not certify every hardware or driver combination.

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
- **DLL load failed / missing runtime:** install or repair the x64 Visual C++ Redistributable. For CUDA/cuDNN errors, rerun GPU setup and check `nvidia-smi`; use `--prepare --device cuda` to test actual inference.
- **Python not found / wrong Python:** install Python 3.12 with its launcher or use uv. If this folder already contains a `.venv` created with another Python version, rename it to `.venv-old` and rerun Setup.ps1; do not reuse an incompatible environment.
- **Model download fails:** check network/proxy access to Hugging Face and free disk space, then rerun `--prepare`. An internet connection is needed until the model is cached.
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
