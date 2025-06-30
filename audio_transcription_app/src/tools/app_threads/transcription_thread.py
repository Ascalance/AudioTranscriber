# moved from tools/threads/transcription_thread.py
from ..offline.transcriber import Transcriber
from PyQt5 import QtCore
import os
import datetime

class TranscriptionThread(QtCore.QThread):
    transcription_completed = QtCore.pyqtSignal(str, str)
    def __init__(self, transcriber, file_path, save_path, language, model, delete_after_transcription):
        super().__init__()
        self.transcriber = transcriber
        self.file_path = file_path
        self.save_path = save_path
        self.language = language
        self.model = model
        self.delete_after_transcription = delete_after_transcription
    def run(self):
        try:
            self.transcriber.transcribe_audio_from_file(self.file_path, self.save_path, self.language, self.model, self.delete_after_transcription)
            self.transcription_completed.emit("Status: Transcription completed", "green")
        except Exception as e:
            self.transcription_completed.emit(f"Status: {e}", "red")
