"""Capture the default Windows playback device through WASAPI loopback."""
import argparse
import audioop
import queue
from pathlib import Path
import sys
import threading
import wave


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--chunk-seconds', type=int, default=30)
    parser.add_argument('--seconds', type=int)
    args = parser.parse_args()
    import numpy as np
    import pyaudiowpatch as pa
    stop = threading.Event()

    def commands():
        for line in sys.stdin:
            if line.strip() == 'q':
                stop.set()
                return
        stop.set()
    threading.Thread(target=commands, daemon=True).start()
    folder = Path(args.output)
    folder.mkdir(parents=True, exist_ok=True)
    writer = None
    total = 0
    index = 0
    segment_samples = 0
    state = None
    with pa.PyAudio() as audio:
        device = audio.get_default_wasapi_loopback()
        channels = int(device['maxInputChannels'])
        rate = int(device['defaultSampleRate'])
        if channels < 1:
            raise RuntimeError('Default playback device has no loopback channels.')
        print(f"Capturing playback device: {device['name']}", file=sys.stderr, flush=True)
        buffers = queue.Queue(maxsize=100)
        overflow = threading.Event()

        def receive(data, frame_count, time_info, status):
            try:
                buffers.put_nowait(data)
            except queue.Full:
                overflow.set()
                return (None, pa.paComplete)
            return (None, pa.paContinue)

        stream = audio.open(format=pa.paInt16, channels=channels, rate=rate,
                            input=True, input_device_index=device['index'], frames_per_buffer=1024,
                            stream_callback=receive)
        try:
            while not stop.is_set():
                if overflow.is_set():
                    raise RuntimeError('Audio capture fell behind; restart with fewer apps running.')
                try:
                    data = buffers.get(timeout=0.1)
                except queue.Empty:
                    # WASAPI may stop producing buffers while all playback is silent.
                    # Keep the capture timeline advancing and the stop command responsive.
                    data = bytes((rate // 10) * channels * 2)
                frames = np.frombuffer(data, dtype='<i2').reshape(-1, channels)
                mono = np.rint(frames.astype(np.float32).mean(axis=1)).astype('<i2').tobytes()
                converted, state = audioop.ratecv(mono, 2, 1, rate, 16000, state)
                if args.seconds:
                    converted = converted[:max(0, args.seconds * 16000 - total) * 2]
                while converted:
                    if writer is None:
                        writer = wave.open(str(folder / f'{index:08d}.wav'), 'wb')
                        writer.setnchannels(1)
                        writer.setsampwidth(2)
                        writer.setframerate(16000)
                    remaining = args.chunk_seconds * 16000 - segment_samples
                    part, converted = converted[:remaining * 2], converted[remaining * 2:]
                    writer.writeframesraw(part)
                    samples = len(part) // 2
                    segment_samples += samples
                    total += samples
                    if segment_samples == args.chunk_seconds * 16000:
                        writer.close()
                        writer = None
                        segment_samples = 0
                        index += 1
                if args.seconds and total >= args.seconds * 16000:
                    break
        finally:
            stream.stop_stream()
            stream.close()
            if writer:
                writer.close()
    print(f'Captured {total / 16000:.1f}s of computer audio.', file=sys.stderr, flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Computer audio capture failed: {exc}. Check the Windows default playback device.', file=sys.stderr)
        sys.exit(1)
