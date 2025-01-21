class Transcriber:
    def __init__(self, whisper_model):
        self.whisper_model = whisper_model

    def transcribe(self, audio_file_path, language):
        # Transcription de l'audio en texte
        result = self.whisper_model.transcribe(audio_file_path, language=language)
        return result['text']