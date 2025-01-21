import tkinter as tk
from audio_recorder import AudioRecorder
import logging
import os

# Configurer le logging
log_dir = "Logs"
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(filename=os.path.join(log_dir, 'log.txt'), level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AppUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Enregistreur Audio")

        self.recorder = AudioRecorder()

        self.record_button = tk.Button(master, text="Démarrer l'enregistrement", command=self.start_recording)
        self.record_button.pack(pady=20)

        self.stop_button = tk.Button(master, text="Arrêter l'enregistrement", command=self.stop_recording, state=tk.DISABLED)
        self.stop_button.pack(pady=20)

        self.language_label = tk.Label(master, text="Choisissez la langue :")
        self.language_label.pack(pady=10)

        self.language_var = tk.StringVar(value="fr")
        self.language_menu = tk.OptionMenu(master, self.language_var, "fr", "en")
        self.language_menu.pack(pady=10)

        self.save_path_label = tk.Label(master, text="Chemin de sauvegarde :")
        self.save_path_label.pack(pady=10)

        self.save_path_entry = tk.Entry(master, width=50)
        self.save_path_entry.pack(pady=10)

        self.status_label = tk.Label(master, text="Statut : Prêt")
        self.status_label.pack(pady=20)

    def start_recording(self):
        logging.info("Démarrage de l'enregistrement...")
        self.recorder.start_recording()
        self.record_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="Statut : Enregistrement...")

    def stop_recording(self):
        logging.info("Arrêt de l'enregistrement...")
        self.recorder.stop_recording()
        save_path = self.save_path_entry.get()
        language = self.language_var.get()
        logging.info(f"Chemin de sauvegarde : {save_path}")
        logging.info(f"Langue sélectionnée : {language}")
        self.recorder.transcribe_audio(save_path, language)
        logging.info("Transcription terminée.")
        self.status_label.config(text="Statut : Enregistrement terminé")
        self.record_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = AppUI(root)
    root.mainloop()