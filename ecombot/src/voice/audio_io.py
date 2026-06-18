import io
import logging
import struct
import tempfile
import threading
import time
import wave
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit
FRAME_DURATION_MS = 30  # VAD frame size
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)

SILENCE_TIMEOUT_S = 1.5  # seconds of silence to end utterance
MIN_SPEECH_FRAMES = 5  # minimum speech frames to consider valid


class AudioIO:

    def __init__(self, enable_barge_in: bool = True):
        self._enable_barge_in = enable_barge_in
        self._interrupted = False
        self._listening = False
        self._interrupt_audio: Optional[bytes] = None

    @property
    def was_interrupted(self) -> bool:
        return self._interrupted

    @property
    def interrupt_audio(self) -> Optional[bytes]:
        return self._interrupt_audio

    def listen_utterance(self, max_duration_s: float = 15.0) -> bytes:
        try:
            import sounddevice as sd
            import webrtcvad
        except ImportError as e:
            log.error("Audio dependencies not installed: %s", e)
            return b""

        vad = webrtcvad.Vad(2)  # aggressiveness: 0-3
        frames: list[bytes] = []
        speech_frames = 0
        silence_frames = 0
        max_silence_frames = int(SILENCE_TIMEOUT_S * 1000 / FRAME_DURATION_MS)
        max_frames = int(max_duration_s * 1000 / FRAME_DURATION_MS)
        started = False

        self._listening = True
        log.info("🎤 Listening... (speak now)")

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=FRAME_SIZE,
            ) as stream:
                for _ in range(max_frames):
                    if not self._listening:
                        break

                    data, _ = stream.read(FRAME_SIZE)
                    frame_bytes = data.tobytes()

                    is_speech = vad.is_speech(frame_bytes, SAMPLE_RATE)

                    if is_speech:
                        speech_frames += 1
                        silence_frames = 0
                        started = True
                        frames.append(frame_bytes)
                    elif started:
                        silence_frames += 1
                        frames.append(frame_bytes)
                        if silence_frames >= max_silence_frames:
                            break

        except Exception as exc:
            log.error("Microphone error: %s", exc)
            return b""
        finally:
            self._listening = False

        if speech_frames < MIN_SPEECH_FRAMES:
            log.info("No meaningful speech detected")
            return b""

        log.info("Captured %d frames (%d speech)", len(frames), speech_frames)
        return self._frames_to_wav(frames)

    def speak(self, audio_bytes: bytes, format: str = "mp3") -> None:
        self._interrupted = False
        self._interrupt_audio = None

        if not audio_bytes:
            return

        try:
            import sounddevice as sd
        except ImportError:
            log.error("sounddevice not installed")
            return

        try:
            audio_array, sr = self._decode_audio(audio_bytes, format)
        except Exception as exc:
            log.error("Audio decode error: %s", exc)
            return

        if audio_array is None:
            return

        barge_in_thread = None
        if self._enable_barge_in:
            self._listening = False
            barge_in_thread = threading.Thread(
                target=self._monitor_barge_in, daemon=True
            )

        try:
            log.info("🔊 Speaking...")
            if barge_in_thread:
                barge_in_thread.start()

            sd.play(audio_array, sr)

            while sd.get_stream().active:
                if self._interrupted:
                    sd.stop()
                    log.info("⚡ Barge-in detected! Stopping playback.")
                    break
                time.sleep(0.05)

            sd.wait()
        except Exception as exc:
            log.error("Playback error: %s", exc)

    def _monitor_barge_in(self) -> None:
        try:
            import sounddevice as sd
            import webrtcvad
        except ImportError:
            return

        vad = webrtcvad.Vad(2)
        consecutive_speech = 0
        required_speech_frames = 3  # Require sustained speech to trigger

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=FRAME_SIZE,
            ) as stream:
                while not self._interrupted:
                    try:
                        data, _ = stream.read(FRAME_SIZE)
                        frame_bytes = data.tobytes()

                        if vad.is_speech(frame_bytes, SAMPLE_RATE):
                            consecutive_speech += 1
                            if consecutive_speech >= required_speech_frames:
                                self._interrupted = True
                                self._interrupt_audio = self.listen_utterance(max_duration_s=10)
                                return
                        else:
                            consecutive_speech = 0
                    except Exception:
                        break
        except Exception as exc:
            log.debug("Barge-in monitor error: %s", exc)

    def _frames_to_wav(self, frames: list[bytes]) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(SAMPLE_WIDTH)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b"".join(frames))
        return buf.getvalue()

    def _decode_audio(self, audio_bytes: bytes, format: str):
        import sounddevice as sd

        if format == "wav":
            buf = io.BytesIO(audio_bytes)
            with wave.open(buf, "rb") as wf:
                sr = wf.getframerate()
                n_frames = wf.getnframes()
                data = wf.readframes(n_frames)
                array = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                return array, sr

        elif format == "mp3":
            try:
                import subprocess
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    f.write(audio_bytes)
                    tmp_path = f.name

                result = subprocess.run(
                    ["ffmpeg", "-i", tmp_path, "-f", "s16le", "-ar", "24000",
                     "-ac", "1", "-loglevel", "quiet", "-"],
                    capture_output=True,
                    timeout=10,
                )
                import os
                os.unlink(tmp_path)

                if result.returncode == 0 and result.stdout:
                    array = np.frombuffer(result.stdout, dtype=np.int16).astype(np.float32) / 32768.0
                    return array, 24000
                else:
                    log.warning("ffmpeg conversion failed, trying direct playback")
                    return None, None
            except FileNotFoundError:
                log.warning("ffmpeg not found — install ffmpeg for MP3 playback")
                return None, None
            except Exception as exc:
                log.error("MP3 decode error: %s", exc)
                return None, None
        else:
            log.error("Unsupported audio format: %s", format)
            return None, None
