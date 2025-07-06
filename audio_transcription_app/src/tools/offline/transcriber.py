import whisper
import os
import logging  # Logging is configured globally in main.py
import time
import torch

class Transcriber:
    def __init__(self):
        # Detect device: CUDA (NVIDIA GPU) if available, else CPU
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logging.info(f"Whisper will run on: {self.device}")

    def transcribe_audio_from_file(self, file_path, save_path, language, model, delete_after_transcription):
        if not os.path.exists(file_path):
            logging.error("Audio file not found.")
            raise FileNotFoundError(f"Audio file not found: {file_path}")

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
            whisper_model = whisper.load_model(model_mapping.get(model, model), device=self.device)
            if language is None:
                result = whisper_model.transcribe(file_path)
            else:
                result = whisper_model.transcribe(file_path, language=language)
        except Exception as e:
            logging.error(f"Transcription error: {e}")
            raise RuntimeError(f"Transcription error: {e}")
        transcription_end_time = time.time()
        logging.info(f"Transcription completed in {transcription_end_time - transcription_start_time:.2f} seconds")

        if not result["text"].strip():
            logging.warning("No transcription generated.")
            raise ValueError("No transcription generated.")

        # Ensure the output directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(result["text"])
        logging.info(f"Transcription saved to {save_path}")

        # Robust temp file deletion: check for 'temp' folder in path (case-insensitive)
        norm_path = os.path.normcase(os.path.normpath(file_path))
        is_temp = os.path.sep + "temp" + os.path.sep in norm_path or norm_path.startswith("temp" + os.path.sep)
        if delete_after_transcription and is_temp:
            try:
                os.remove(file_path)
                logging.info("Temporary audio file deleted.")
            except Exception as e:
                logging.error(f"Failed to delete temporary audio file: {e}")
        else:
            logging.info("Audio file not deleted.")

    def get_unique_filepath(self, file_path):
        base, extension = os.path.splitext(file_path)
        counter = 1
        new_file_path = file_path
        while os.path.exists(new_file_path):
            new_file_path = f"{base}({counter}){extension}"
            counter += 1
        return new_file_path
