import sounddevice as sd
import numpy as np
import wave
import whisper
import os
import logging
import time
import torch

try:
    from pydub import AudioSegment
except ImportError:
    print("Error: 'pydub' module is not installed. Please install it by running 'pip install pydub'.")
    exit()

# Configure logging
log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'Logs')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(filename=os.path.join(log_dir, 'log.txt'), level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Ajouter un retour à la ligne pour chaque nouvelle session
logging.info("\n--- Nouvelle session ---")

class AudioRecorder:
    def __init__(self):
        self.recording = False
        self.frames = []
        self.sample_rate = 44100
        self.channels = 2  # Use two channels for stereo recording
        self.dtype = 'int16'  # Use 16-bit data type to reduce artifacts

    def start_recording(self):
        logging.info("Starting recording...")
        self.recording = True
        self.frames = []
        self.recording_start_time = time.time()

        def callback(indata, frames, time, status):
            if status:
                logging.warning(f"Status: {status}")
            logging.debug(f"Callback - frames: {frames}, time: {time}, status: {status}")
            self.frames.append(indata.copy())
            logging.debug(f"Data captured: {indata}")

        self.stream = sd.InputStream(callback=callback, channels=self.channels, samplerate=self.sample_rate, dtype=self.dtype)
        self.stream.start()
        logging.info("Recording started.")

    def stop_recording(self):
        logging.info("Stopping recording...")
        self.recording = False
        self.stream.stop()
        self.stream.close()
        recording_end_time = time.time()
        logging.info(f"Recording completed in {recording_end_time - self.recording_start_time:.2f} seconds")
        logging.info("Recording stopped.")

    def save_recording(self, file_path):
        logging.info(f"Saving recording to {file_path}...")
        with wave.open(file_path, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16 bits
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(self.frames))
        logging.info("Recording saved.")
        # Verify the validity of the audio file
        with wave.open(file_path, 'rb') as wf:
            logging.info(f"Audio file saved - channels: {wf.getnchannels()}, sample width: {wf.getsampwidth()}, sample rate: {wf.getframerate()}, number of frames: {wf.getnframes()}")

    def transcribe_audio(self, save_path, language, delete_after_transcription):
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        audio_file = os.path.join(temp_dir, "enregistrement.wav")
        self.save_recording(audio_file)
        self.transcribe_audio_from_file(audio_file, save_path, language, delete_after_transcription)

    def transcribe_audio_from_file(self, file_path, save_path, language, delete_after_transcription):
        # Check if the audio file was imported correctly
        if not os.path.exists(file_path):
            logging.error("Error: The audio file was not imported correctly.")
            return

        # Load the Whisper model
        logging.info("Loading Whisper model 'turbo'...")
        model = whisper.load_model("turbo")

        # Transcribe the audio
        logging.info(f"Transcribing audio in {language}...")
        transcription_start_time = time.time()
        try:
            result = model.transcribe(file_path, language=language)
        except ValueError as e:
            logging.error(f"Error during transcription: {e}")
            return
        transcription_end_time = time.time()
        logging.info(f"Transcription completed in {transcription_end_time - transcription_start_time:.2f} seconds")

        # Display the transcribed text
        logging.info("Transcribed text:")
        logging.info(result["text"])

        # Check if the text is empty
        if not result["text"].strip():
            logging.warning("No transcription was generated.")
            logging.debug(f"Debug info: {result}")
            return

        # Check the segments
        if not result["segments"]:
            logging.warning("No segments were detected.")
            logging.debug(f"Debug info: {result}")
            return

        # Display the segments for debugging
        for segment in result["segments"]:
            logging.debug(f"Segment: {segment}")

        # Determine the save path
        if not save_path:
            save_path = os.path.join("records", "transcription.txt")
        else:
            # Create the save directory if it does not exist
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            save_path = self.get_unique_filepath(save_path)

        # Save the text to the specified path
        logging.info(f"Saving transcription to {save_path}...")
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(result["text"])
        logging.info(f"Text saved to: {save_path}")

        # Delete the temporary audio file after transcription if the option is enabled
        if delete_after_transcription and file_path == os.path.join("temp", "enregistrement.wav"):
            os.remove(file_path)
            logging.info("Temporary audio file deleted.")

    def get_unique_filepath(self, file_path):
        base, extension = os.path.splitext(file_path)
        counter = 1
        new_file_path = file_path
        while os.path.exists(new_file_path):
            new_file_path = f"{base}_({counter}){extension}"
            counter += 1
        return new_file_path