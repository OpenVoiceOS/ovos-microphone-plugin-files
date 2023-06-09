# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
from dataclasses import dataclass, field
from queue import Queue
from typing import Optional
from os.path import expanduser
import speech_recognition as sr
from ovos_plugin_manager.templates.microphone import Microphone
from ovos_utils.file_utils import FileWatcher
from ovos_utils.log import LOG


@dataclass
class FilesMicrophone(Microphone):
    files_folder: str = expanduser("~/file_microphone")
    current_file: str = ""
    autodelete: bool = True
    timeout: float = 5.0

    _watcher: Optional[FileWatcher] = None
    _queue: "Queue[Optional[bytes]]" = field(default_factory=Queue)
    _is_running: bool = False

    @staticmethod
    def read_wave_file(wave_file_path):
        '''
        reads the wave file at provided path and return the expected
        Audio format
        '''
        # use the audio file as the audio source
        r = sr.Recognizer()
        with sr.AudioFile(wave_file_path) as source:
            audio = r.record(source)
        return audio

    def on_new_file(self, path):
        self.current_file = path

        try:
            audio = self.read_wave_file(path)
            full_chunk = audio.frame_data
            while len(full_chunk) >= self.chunk_size:
                self._queue.put_nowait(full_chunk[: self.chunk_size])
                full_chunk = full_chunk[self.chunk_size:]
            if self.autodelete:
                os.remove(path)
        except:
            LOG.exception(f"failed to process file: {path}")
        self.current_file = ""

    def start(self):
        assert self._watcher is None, "Already started"
        self._watcher = FileWatcher(self.files_folder,
                                    callback=self.on_new_file)
        self._is_running = True

    def read_chunk(self) -> Optional[bytes]:
        assert self._is_running, "Not running"
        if self.current_file:
            return self._queue.get(timeout=self.timeout)
        return b"0" * self.chunk_size  # silence

    def stop(self):
        assert self._watcher is not None, "Not started"
        self._is_running = False
        while not self._queue.empty():
            self._queue.get()
        self._queue.put_nowait(None)
        self._watcher.shutdown()
