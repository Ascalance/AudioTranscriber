import sounddevice as sd
import numpy as np
import wave
import os
import logging

# Configurer le logging
log_dir = "Logs"
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(filename=os.path.join(log_dir, 'log.txt'), level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AudioRecorderV2:
    def __init__(self):
        self.recording = False
        self.frames = []
        self.sample_rate = 44100
        self.channels = 2  # Utiliser deux canaux pour un enregistrement stéréo
        self.dtype = 'int16'  # Utiliser un type de données 16 bits pour réduire les artefacts

    def start_recording(self):
        logging.info("Initialisation de l'enregistrement...")
        self.recording = True
        self.frames = []

        def callback(indata, frames, time, status):
            if status:
                logging.warning(f"Status: {status}")
            logging.debug(f"Callback - frames: {frames}, time: {time}, status: {status}")
            self.frames.append(indata.copy())
            logging.debug(f"Data captured: {indata}")

        self.stream = sd.InputStream(callback=callback, channels=self.channels, samplerate=self.sample_rate, dtype=self.dtype)
        self.stream.start()
        logging.info("Enregistrement démarré.")

    def stop_recording(self):
        logging.info("Arrêt de l'enregistrement...")
        self.recording = False
        self.stream.stop()
        self.stream.close()
        logging.info("Enregistrement arrêté.")

    def save_recording(self, file_path):
        logging.info(f"Sauvegarde de l'enregistrement dans {file_path}...")
        with wave.open(file_path, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16 bits
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(self.frames))
        logging.info("Enregistrement sauvegardé.")
        # Vérification de la validité du fichier audio
        with wave.open(file_path, 'rb') as wf:
            logging.info(f"Fichier audio sauvegardé - nombre de canaux: {wf.getnchannels()}, largeur d'échantillon: {wf.getsampwidth()}, fréquence d'échantillonnage: {wf.getframerate()}, nombre de frames: {wf.getnframes()}")

def main():
    recorder = AudioRecorderV2()
    print("Appuyez sur Entrée pour démarrer l'enregistrement...")
    input()
    recorder.start_recording()
    print("Appuyez sur Entrée pour arrêter l'enregistrement...")
    input()
    recorder.stop_recording()
    recorder.save_recording("test_enregistrement.wav")
    print("Enregistrement terminé et sauvegardé dans 'test_enregistrement.wav'.")

if __name__ == "__main__":
    main()
