# moved from tools/threads/online_transcription_thread.py
from ..online.online import OnlineTranscriber
from PyQt5 import QtCore
import os

class OnlineTranscriptionThread(QtCore.QThread):
    transcription_completed = QtCore.pyqtSignal(str, str)
    def __init__(self, api_key, file_path, model, delete_temp, save_path):
        super().__init__()
        self.api_key = api_key
        self.file_path = file_path
        self.model = model
        self.delete_temp = delete_temp
        self.save_path = save_path
    def run(self):
        try:
            transcriber = OnlineTranscriber(api_key=self.api_key)
            text = transcriber.transcribe_audio_from_file(self.file_path, model=self.model)
            if text:
                with open(self.save_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                if self.delete_temp and self.file_path.startswith("Temp"):
                    try:
                        os.remove(self.file_path)
                    except Exception:
                        pass
                self.transcription_completed.emit("Status: Online transcription completed", "green")
            else:
                self.transcription_completed.emit("Status: Error during online transcription", "red")
        except Exception as e:
            self.transcription_completed.emit(f"Status: {e}", "red")
