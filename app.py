"""Small desktop controller; inference runs in a separate local process."""
from pathlib import Path
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import uuid

ROOT = Path(__file__).resolve().parent


class App:
    def __init__(self, root):
        self.root = root
        self.process = None
        self.messages = queue.Queue()
        self.stop_file = None
        root.title('Video Transcriber — YouTube / Instagram / Facebook')
        root.geometry('960x690')
        panel = ttk.Frame(root, padding=16)
        panel.pack(fill='both', expand=True)
        ttk.Label(panel, text='Local video transcription', font=('Segoe UI', 18, 'bold')).pack(anchor='w')
        ttk.Label(panel, text='Runs on your computer • Saves text + SRT subtitles • Updates every ~30 seconds').pack(anchor='w', pady=(4, 14))
        modes = ttk.Frame(panel)
        modes.pack(fill='x', pady=(0, 10))
        self.mode = tk.StringVar(value='link')
        for label, value in [('Video link', 'link'), ('Local file', 'file'), ('Computer audio', 'audio')]:
            ttk.Radiobutton(modes, text=label, variable=self.mode, value=value, command=self.update_mode).pack(side='left', padx=(0, 20))
        self.input_label = ttk.Label(panel, text='YouTube, Instagram, or Facebook video/reel/live URL')
        self.input_label.pack(anchor='w')
        self.url = tk.StringVar(value='')
        self.local_file = tk.StringVar(value='')
        source_row = ttk.Frame(panel)
        source_row.pack(fill='x', pady=(4, 8))
        self.source_entry = ttk.Entry(source_row, textvariable=self.url)
        self.source_entry.pack(side='left', fill='x', expand=True)
        self.browse_button = ttk.Button(source_row, text='Browse...', command=self.browse, state='disabled')
        self.browse_button.pack(side='left', padx=(8, 0))
        self.help_text = tk.StringVar(value='Direct links work when the site permits extraction. If blocked, use Computer audio.')
        ttk.Label(panel, textvariable=self.help_text, wraplength=900).pack(anchor='w', pady=(0, 12))
        options = ttk.Frame(panel)
        options.pack(fill='x')
        ttk.Label(options, text='Language code (blank = detect):').pack(side='left')
        self.language = tk.StringVar()
        ttk.Entry(options, textvariable=self.language, width=8).pack(side='left', padx=8)
        ttk.Label(options, text='Device:').pack(side='left', padx=(20, 8))
        self.device = tk.StringVar(value='cuda')
        ttk.Combobox(options, textvariable=self.device, values=['cuda', 'cpu'], state='readonly', width=8).pack(side='left')
        buttons = ttk.Frame(panel)
        buttons.pack(fill='x', pady=14)
        self.start_button = ttk.Button(buttons, text='Start transcription', command=self.start)
        self.start_button.pack(side='left')
        self.stop_button = ttk.Button(buttons, text='Stop and save', command=self.stop, state='disabled')
        self.stop_button.pack(side='left', padx=8)
        ttk.Button(buttons, text='Open transcripts', command=self.open_outputs).pack(side='left')
        self.status = tk.StringVar(value='Ready. Choose a source. Recorded videos finish automatically; live capture runs until stopped.')
        ttk.Label(panel, textvariable=self.status).pack(anchor='w', pady=(0, 8))
        from tkinter.scrolledtext import ScrolledText
        self.output = ScrolledText(panel, wrap='word', font=('Consolas', 10), state='disabled')
        self.output.pack(fill='both', expand=True)
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(150, self.poll)

    def update_mode(self):
        mode = self.mode.get()
        self.source_entry.configure(textvariable=self.local_file if mode == 'file' else self.url,
                                    state='disabled' if mode == 'audio' else 'normal')
        self.browse_button.configure(state='normal' if mode == 'file' else 'disabled')
        labels = {'link': 'YouTube, Instagram, or Facebook video/reel/live URL',
                  'file': 'Local audio or video file', 'audio': 'Default Windows playback device (no URL needed)'}
        hints = {'link': 'Direct links work when the site permits extraction. If blocked, use Computer audio.',
                 'file': 'Select an audio/video recording. Transcription finishes at the end of the file.',
                 'audio': 'Captures ALL sound playing on your default speakers/headphones, not the microphone. '
                          'Start here, then play the video in your browser. Keep other apps quiet; use Stop when finished.'}
        self.input_label.configure(text=labels[mode])
        self.help_text.set(hints[mode])

    def browse(self):
        filename = filedialog.askopenfilename(title='Choose a video or audio recording',
                    filetypes=[('Video and audio', '*.mp4 *.mkv *.mov *.webm *.avi *.mp3 *.wav *.m4a *.flac *.ogg'), ('All files', '*.*')])
        if filename:
            self.local_file.set(filename)

    def start(self):
        mode = self.mode.get()
        if mode == 'link':
            from sources import validate_url
            try:
                inputs = ['--url', validate_url(self.url.get())]
            except ValueError as exc:
                messagebox.showerror('Video link needed', str(exc))
                return
        elif mode == 'file':
            filename = self.local_file.get().strip()
            if not filename or not Path(filename).is_file():
                messagebox.showerror('File needed', 'Choose an existing video or audio file.')
                return
            inputs = ['--file', filename]
        else:
            inputs = ['--system-audio']
        controls = ROOT / 'work'
        controls.mkdir(exist_ok=True)
        self.stop_file = controls / f'{uuid.uuid4().hex}.stop'
        command = [sys.executable, '-u', str(ROOT / 'transcribe.py'), *inputs,
                   '--language', self.language.get().strip(), '--device', self.device.get(),
                   '--stop-file', str(self.stop_file)]
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        try:
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        text=True, encoding='utf-8', errors='replace', env=env,
                                        creationflags=subprocess.CREATE_NO_WINDOW)
        except OSError as exc:
            messagebox.showerror('Could not start transcription', str(exc))
            return
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.status.set('Starting. Keep this window open during transcription.')
        def reader(process):
            for line in process.stdout:
                self.messages.put(line)
            process.stdout.close()
            self.messages.put(('exit', process.wait()))
        threading.Thread(target=reader, args=(self.process,), daemon=True).start()

    def stop(self):
        if self.process and self.process.poll() is None:
            self.stop_file.touch()
            self.stop_button.config(state='disabled')
            self.status.set('Stopping and saving the final audio chunk...')

    def poll(self):
        while not self.messages.empty():
            item = self.messages.get_nowait()
            if isinstance(item, tuple):
                self.status.set('Finished. Transcript saved if audio was received.' if item[1] == 0 else 'Stopped with an error. See the log below.')
                self.start_button.config(state='normal')
                self.stop_button.config(state='disabled')
                self.stop_file.unlink(missing_ok=True)
                self.process = None
            else:
                if item.startswith('Capturing audio;'):
                    self.status.set('Transcribing. Computer audio mode: now play your video. Stop and save when finished.'
                                    if self.mode.get() == 'audio' else 'Transcribing. Text appears below as audio is processed.')
                elif item.startswith('This event has not started'):
                    self.status.set('Waiting for the live event to start...')
                self.output.config(state='normal')
                self.output.insert('end', item)
                if int(self.output.index('end-1c').split('.')[0]) > 2000:
                    self.output.delete('1.0', '500.0')
                self.output.see('end')
                self.output.config(state='disabled')
        self.root.after(150, self.poll)

    def open_outputs(self):
        folder = ROOT / 'transcripts'
        folder.mkdir(exist_ok=True)
        os.startfile(folder)

    def close(self):
        if self.process and self.process.poll() is None:
            self.stop()
            self.root.after(300, self.close)
        else:
            self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
