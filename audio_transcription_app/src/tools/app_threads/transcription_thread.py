# moved from tools/threads/transcription_thread.py
from ..offline.transcriber import Transcriber
from PyQt5 import QtCore
import os
import datetime

class TranscriptionThread(QtCore.QThread):
    transcription_completed = QtCore.pyqtSignal(str, str)
    def __init__(self, transcriber, file_path, save_path, language, model, delete_after_transcription, export_format="PDF"):
        super().__init__()
        self.transcriber = transcriber
        self.file_path = file_path
        self.save_path = save_path
        self.language = language
        self.model = model
        self.delete_after_transcription = delete_after_transcription
        self.export_format = export_format
    def run(self):
        try:
            # Always transcribe to text first
            txt_save_path = self.save_path
            if self.export_format != "TXT":
                txt_save_path = self.save_path.replace(os.path.splitext(self.save_path)[1], ".txt")
            self.transcriber.transcribe_audio_from_file(self.file_path, txt_save_path, self.language, self.model, self.delete_after_transcription)
            # Read transcription
            with open(txt_save_path, 'r', encoding='utf-8') as f:
                transcription = f.read()
            # Export to chosen format
            if self.export_format == "PDF":
                from ..utils.export_pdf import export_pdf
                export_pdf(transcription, self.save_path)
            elif self.export_format == "DOCX":
                from ..utils.export_docx import export_docx
                export_docx(transcription, self.save_path)
            elif self.export_format == "SRT":
                from ..utils.export_srt import export_srt
                export_srt(transcription, self.save_path)
            elif self.export_format == "ODT":
                from ..utils.export_odt import export_odt
                export_odt(transcription, self.save_path)
            self.transcription_completed.emit("Status: Transcription completed", "green")
        except Exception as e:
            import logging  # Logging is configured globally in main.py
            logging.error(f"Transcription error: {e}")
            self.transcription_completed.emit(f"Erreur : {e}", "red")
