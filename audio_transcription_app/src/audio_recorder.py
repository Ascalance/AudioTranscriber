import sounddevice as sd
import wave
import os
import logging
import time

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