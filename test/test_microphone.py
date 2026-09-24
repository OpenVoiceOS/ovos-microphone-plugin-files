import os
import struct
import tempfile
import unittest
import wave

from ovos_microphone_plugin_files import FilesMicrophone


def _write_silence_wav(path, sample_rate=16000, sample_width=2,
                       channels=1, frames=8000):
    """Write a tiny valid mono PCM wav of silence to ``path``."""
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack("<" + "h" * frames, *([0] * frames)))


class TestFilesMicrophone(unittest.TestCase):
    def test_is_microphone(self):
        from ovos_plugin_manager.templates.microphone import Microphone
        self.assertTrue(issubclass(FilesMicrophone, Microphone))

    def test_instantiation_defaults(self):
        mic = FilesMicrophone()
        self.assertEqual(mic.sample_rate, 16000)
        self.assertEqual(mic.sample_width, 2)
        self.assertEqual(mic.sample_channels, 1)
        self.assertTrue(mic.autodelete)
        self.assertFalse(mic._is_running)
        self.assertIsNone(mic._watcher)
        # inherited derived properties
        self.assertEqual(mic.frames_per_chunk,
                         mic.chunk_size // (mic.sample_width *
                                            mic.sample_channels))
        self.assertGreater(mic.seconds_per_chunk, 0)

    def test_interface_methods_exist(self):
        for method in ("start", "read_chunk", "stop", "on_new_file",
                       "read_wave_file"):
            self.assertTrue(callable(getattr(FilesMicrophone, method)))

    def test_read_wave_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sample.wav")
            _write_silence_wav(path)
            audio = FilesMicrophone.read_wave_file(path)
            self.assertTrue(len(audio.frame_data) > 0)

    def test_on_new_file_queues_chunks_and_autodeletes(self):
        with tempfile.TemporaryDirectory() as tmp:
            mic = FilesMicrophone(files_folder=tmp, autodelete=True)
            path = os.path.join(tmp, "sample.wav")
            _write_silence_wav(path, frames=16000)

            mic.on_new_file(path)

            # chunks were enqueued from the file
            self.assertFalse(mic._queue.empty())
            chunk = mic._queue.get_nowait()
            self.assertEqual(len(chunk), mic.chunk_size)
            # current_file reset and file removed when autodelete is on
            self.assertEqual(mic.current_file, "")
            self.assertFalse(os.path.exists(path))

    def test_read_wave_file_handles_either_audiofile(self):
        """The source class is whichever ovos-plugin-manager installed.

        OPM replaces ``speech_recognition.AudioFile`` with its own class,
        which does not subclass ``speech_recognition.AudioSource``. The
        upstream class does, and is read through ``Recognizer.record()``;
        the replacement reads itself through ``read()``. Both are inside
        the declared ``ovos-plugin-manager>=2.1.0,<3.0.0`` range, so both
        doors are driven here.
        """
        import speech_recognition as sr
        from ovos_microphone_plugin_files import FilesMicrophone as M

        class _Data:
            frame_data = b"\x00\x01"

        class _OPMSource:
            """Not an AudioSource. Reads itself, as OPM's class does."""

            def __init__(self, path):
                self.path = path

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return _Data()

        class _UpstreamSource(sr.AudioSource):
            """An AudioSource with no read(), as the upstream class is."""

            def __init__(self, path):
                self.path = path

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        recorded = []

        class _Recognizer:
            def record(self, source):
                recorded.append(source)
                return _Data()

        original_file, original_rec = sr.AudioFile, sr.Recognizer
        try:
            sr.AudioFile, sr.Recognizer = _OPMSource, _Recognizer
            audio = M.read_wave_file("ignored.wav")
            self.assertEqual(audio.frame_data, b"\x00\x01")
            self.assertEqual(recorded, [], "record() must not be used on a "
                                           "source it would refuse")

            sr.AudioFile = _UpstreamSource
            audio = M.read_wave_file("ignored.wav")
            self.assertEqual(audio.frame_data, b"\x00\x01")
            self.assertEqual(len(recorded), 1,
                             "an AudioSource is read through record()")
        finally:
            sr.AudioFile, sr.Recognizer = original_file, original_rec

    def test_read_chunk_requires_running(self):
        mic = FilesMicrophone()
        with self.assertRaises(AssertionError):
            mic.read_chunk()


if __name__ == "__main__":
    unittest.main()
