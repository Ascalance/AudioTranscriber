import whisper
import os
import logging
import time

class Transcriber:
    def __init__(self):
        pass

    def transcribe_audio_from_file(self, file_path, save_path, language, model, delete_after_transcription):
        if not os.path.exists(file_path):
            logging.error("Audio file not found.")
            return

        model_mapping = {
            "Turbo": "turbo",
            "Tiny": "tiny",
            "Base": "base",
            "Small": "small",
            "Medium": "medium",
            "Large": "large-v3-turbo"
        }

        transcription_start_time = time.time()
        try:
            result = whisper.load_model(model_mapping.get(model, model)).transcribe(file_path, language=language)
        except ValueError as e:
            logging.error(f"Transcription error: {e}")
            return
        transcription_end_time = time.time()
        logging.info(f"Transcription completed in {transcription_end_time - transcription_start_time:.2f} seconds")

        if not result["text"].strip():
            logging.warning("No transcription generated.")
            return

        transcription_folder = os.path.join("Records", "Transcription")
        os.makedirs(transcription_folder, exist_ok=True)
        save_path = self.get_unique_filepath(os.path.join(transcription_folder, "transcription.txt"))

        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(result["text"])
        logging.info(f"Transcription saved to {save_path}")

        if delete_after_transcription and file_path.startswith("temp"):
            os.remove(file_path)
            logging.info("Temporary audio file deleted.")
        elif not file_path.startswith("temp"):
            logging.info("Imported audio file not deleted.")

    def get_unique_filepath(self, file_path):
        base, extension = os.path.splitext(file_path)
        counter = 1
        new_file_path = file_path
        while os.path.exists(new_file_path):
            new_file_path = f"{base}({counter}){extension}"
            counter += 1
        return new_file_path
