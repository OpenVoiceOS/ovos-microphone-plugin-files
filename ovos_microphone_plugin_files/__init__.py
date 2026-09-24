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
        # ovos-plugin-manager replaces speech_recognition.AudioFile with
        # its own class (ovos_plugin_manager.utils.audio) from 2.2 on. That
        # class does not subclass speech_recognition.AudioSource, which is
        # what Recognizer.record() asserts, so record() refuses the source
        # it is handed. The replacement reads the stream itself instead.
        # This plugin declares ovos-plugin-manager>=2.1.0, and 2.1.0 ships
        # no replacement, so both sources are in range and the test is for
        # the property record() checks, not for a version.
        with sr.AudioFile(wave_file_path) as source:
            if isinstance(source, sr.AudioSource):
                return sr.Recognizer().record(source)
            return source.read()

    def on_new_file(self, path):
        self.current_file = path

        try:
            LOG.debug(f"processing file: {path}")
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
        self._watcher = FileWatcher([self.files_folder],
                                    callback=self.on_new_file)
        self._is_running = True

    def read_chunk(self) -> Optional[bytes]:
        assert self._is_running, "Not running"
        if not self.current_file and self._queue.empty():
            return None

        LOG.debug("reading chunk")
        return self._queue.get(timeout=self.timeout)

    def stop(self):
        assert self._watcher is not None, "Not started"
        self._is_running = False
        while not self._queue.empty():
            self._queue.get()
        self._queue.put_nowait(None)
        self._watcher.shutdown()
