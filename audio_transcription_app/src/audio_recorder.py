import sounddevice as sd
import wave
import whisper
import os
import logging
import time
from datetime import datetime

try:
    from pydub import AudioSegment
except ImportError:
    print("Error: 'pydub' module is not installed. Please install it by running 'pip install pydub'.")
    exit()

log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'Logs')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(filename=os.path.join(log_dir, 'log.txt'), level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("\n--- Nouvelle session ---")

class AudioRecorder:
    def __init__(self):
        self.recording = False
        self.frames = []
        self.sample_rate = 44100
        self.channels = 2
        self.dtype = 'int16'

    def start_recording(self):
        logging.info("Starting recording...")
        self.recording = True
        self.frames = []
        self.recording_start_time = time.time()

        def callback(indata, frames, time, status):
            if status:
                logging.warning(f"Status: {status}")
            self.frames.append(indata.copy())

        self.stream = sd.InputStream(callback=callback, channels=self.channels, samplerate=self.sample_rate, dtype=self.dtype)
        self.stream.start()

    def stop_recording(self):
        self.recording = False
        self.stream.stop()
        self.stream.close()
        recording_end_time = time.time()
        logging.info(f"Recording completed in {recording_end_time - self.recording_start_time:.2f} seconds")

    def save_recording(self, file_path):
        with wave.open(file_path, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(self.frames))
        logging.info(f"Recording saved to {file_path}")

    def transcribe_audio(self, save_path, language, model, delete_after_transcription):
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        audio_file = os.path.join(temp_dir, "enregistrement.wav")
        self.save_recording(audio_file)
        self.transcribe_audio_from_file(audio_file, save_path, language, model, delete_after_transcription)

    def transcribe_audio_from_file(self, file_path, save_path, language, model, delete_after_transcription):
        if not os.path.exists(file_path):
            logging.error("Audio file not found.")
            return

        model = whisper.load_model(model)
        transcription_start_time = time.time()
        try:
            result = model.transcribe(file_path, language=language)
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