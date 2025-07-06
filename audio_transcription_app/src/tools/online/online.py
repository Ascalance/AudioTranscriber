import openai
import os
import logging  # Logging is configured globally in main.py

class OnlineTranscriber:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("No OpenAI API key provided.")
        openai.api_key = self.api_key

    def transcribe_audio_from_file(self, file_path, language=None, model="whisper-1"):
        if not os.path.exists(file_path):
            logging.error("Audio file not found.")
            return None
        with open(file_path, "rb") as audio_file:
            try:
                transcript = openai.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    language=language if language else None
                )
                return transcript.text
            except Exception as e:
                logging.error(f"Error during online transcription: {e}")
                return None
