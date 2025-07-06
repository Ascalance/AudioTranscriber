# moved from tools/threads/online_transcription_thread.py
from ..online.online import OnlineTranscriber
from PyQt5 import QtCore
import os

class OnlineTranscriptionThread(QtCore.QThread):
    transcription_completed = QtCore.pyqtSignal(str, str)
    def __init__(self, api_key, file_path, model, delete_temp, save_path, language=None, export_format="PDF"):
        super().__init__()
        self.api_key = api_key
        self.file_path = file_path
        self.model = model
        self.delete_temp = delete_temp
        self.save_path = save_path
        self.language = language
        self.export_format = export_format
    def run(self):
        try:
            transcriber = OnlineTranscriber(api_key=self.api_key)
            text = transcriber.transcribe_audio_from_file(self.file_path, language=self.language, model=self.model)
            if text:
                # Always save as txt first
                txt_save_path = self.save_path
                if self.export_format != "TXT":
                    txt_save_path = self.save_path.replace(os.path.splitext(self.save_path)[1], ".txt")
                with open(txt_save_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                # Export to chosen format
                if self.export_format == "PDF":
                    from ..utils.export_pdf import export_pdf
                    export_pdf(text, self.save_path)
                elif self.export_format == "DOCX":
                    from ..utils.export_docx import export_docx
                    export_docx(text, self.save_path)
                elif self.export_format == "SRT":
                    from ..utils.export_srt import export_srt
                    export_srt(text, self.save_path)
                elif self.export_format == "ODT":
                    from ..utils.export_odt import export_odt
                    export_odt(text, self.save_path)
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
