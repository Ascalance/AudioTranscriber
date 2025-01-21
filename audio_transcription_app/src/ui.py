from tkinter import Tk, Button, Label, StringVar, Entry, OptionMenu, filedialog, Checkbutton, BooleanVar, Menu
from audio_recorder import AudioRecorder
import os
import logging
import time

# Configurer le logging
log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'Logs')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(filename=os.path.join(log_dir, 'log.txt'), level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Ajouter un retour à la ligne pour chaque nouvelle session
logging.info("\n\n--- Nouvelle session ---")

class AppUI:
    def __init__(self, master):
        start_time = time.time()
        self.master = master
        self.master.title("Audio Transcription Application")
        self.master.geometry("400x420")
        self.master.configure(bg="#2e2e2e")

        self.language_var = StringVar(master)
        self.language_var.set("fr")  # valeur par défaut

        self.create_widgets()
        self.recorder = AudioRecorder()
        self.create_menu()

        end_time = time.time()
        logging.info(f"Tkinter interface created in {end_time - start_time:.2f} seconds")

    def create_widgets(self):
        self.label = Label(self.master, text="Select Language:", bg="#2e2e2e", fg="#ffffff")
        self.label.pack(pady=10)

        self.language_menu = OptionMenu(self.master, self.language_var, "fr", "en", command=self.change_language)
        self.language_menu.pack(pady=10)

        self.save_path_label = Label(self.master, text="Save Path:", bg="#2e2e2e", fg="#ffffff")
        self.save_path_label.pack(pady=10)

        self.save_path_entry = Entry(self.master)
        self.save_path_entry.pack(pady=10)

        self.delete_after_transcription_var = BooleanVar(value=True)
        self.delete_after_transcription_check = Checkbutton(self.master, text="Delete recording after transcription", variable=self.delete_after_transcription_var, bg="#2e2e2e", fg="#ffffff", selectcolor="#2e2e2e")
        self.delete_after_transcription_check.pack(pady=10)

        self.start_button = Button(self.master, text="Start Recording", command=self.start_recording, bg="#4CAF50", fg="#ffffff")
        self.start_button.pack(pady=10)

        self.stop_button = Button(self.master, text="Stop Recording", command=self.stop_recording, bg="#f44336", fg="#ffffff")
        self.stop_button.pack(pady=10)

        self.import_button = Button(self.master, text="Import Audio File", command=self.import_audio, bg="#2196F3", fg="#ffffff")
        self.import_button.pack(pady=10)

        self.status_label = Label(self.master, text="Status: Ready", bg="#2e2e2e", fg="#ffffff", font=("Helvetica", 12, "bold"))
        self.status_label.pack(pady=20, fill='x')

    def create_menu(self):
        menu_bar = Menu(self.master)
        self.master.config(menu=menu_bar)

        language_menu = Menu(menu_bar, tearoff=0)
        language_menu.add_command(label="Français", command=lambda: self.change_language("fr"))
        language_menu.add_command(label="English", command=lambda: self.change_language("en"))
        menu_bar.add_cascade(label="Language", menu=language_menu)

        theme_menu = Menu(menu_bar, tearoff=0)
        theme_menu.add_command(label="Light", command=self.light_mode)
        theme_menu.add_command(label="Dark", command=self.dark_mode)
        menu_bar.add_cascade(label="Theme", menu=theme_menu)

    def change_language(self, lang):
        if lang == "fr":
            self.master.title("Application de Transcription Audio")
            self.label.config(text="Sélectionnez la langue:")
            self.save_path_label.config(text="Chemin de sauvegarde:")
            self.delete_after_transcription_check.config(text="Supprimer l'enregistrement après la transcription")
            self.start_button.config(text="Démarrer l'enregistrement")
            self.stop_button.config(text="Arrêter l'enregistrement")
            self.import_button.config(text="Importer un fichier audio")
            self.status_label.config(text="Statut : Prêt")
        elif lang == "en":
            self.master.title("Audio Transcription Application")
            self.label.config(text="Select Language:")
            self.save_path_label.config(text="Save Path:")
            self.delete_after_transcription_check.config(text="Delete recording after transcription")
            self.start_button.config(text="Start Recording")
            self.stop_button.config(text="Stop Recording")
            self.import_button.config(text="Import Audio File")
            self.status_label.config(text="Status: Ready")

    def light_mode(self):
        self.master.configure(bg="#ffffff")
        self.label.config(bg="#ffffff", fg="#000000")
        self.save_path_label.config(bg="#ffffff", fg="#000000")
        self.delete_after_transcription_check.config(bg="#ffffff", fg="#000000", selectcolor="#ffffff")
        self.status_label.config(bg="#ffffff", fg="#000000")

    def dark_mode(self):
        self.master.configure(bg="#2e2e2e")
        self.label.config(bg="#2e2e2e", fg="#ffffff")
        self.save_path_label.config(bg="#2e2e2e", fg="#ffffff")
        self.delete_after_transcription_check.config(bg="#2e2e2e", fg="#ffffff", selectcolor="#2e2e2e")
        self.status_label.config(bg="#2e2e2e", fg="#ffffff")

    def start_recording(self):
        logging.info("Starting recording...")
        self.recorder.start_recording()
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_label.config(text="Status: Recording...")
        self.recording_start_time = time.time()

    def stop_recording(self):
        logging.info("Stopping recording...")
        self.recorder.stop_recording()
        recording_end_time = time.time()
        logging.info(f"Recording completed in {recording_end_time - self.recording_start_time:.2f} seconds")
        self.status_label.config(text="Status: Recording completed")
        save_path = self.save_path_entry.get()
        language = self.language_var.get()
        delete_after_transcription = self.delete_after_transcription_var.get()
        logging.info(f"Save Path: {save_path}")
        logging.info(f"Selected Language: {language}")
        logging.info(f"Delete after transcription: {delete_after_transcription}")
        if not save_path:
            save_path = os.path.join("records", "transcription.txt")
            logging.info(f"No save path provided. Using default path: {save_path}")
        if not language:
            logging.error("Error: No language selected.")
            self.status_label.config(text="Error: No language selected.")
            return
        self.status_label.config(text="Status: Transcribing...")
        transcription_start_time = time.time()
        self.recorder.transcribe_audio(save_path, language, delete_after_transcription)
        transcription_end_time = time.time()
        logging.info(f"Transcription completed in {transcription_end_time - transcription_start_time:.2f} seconds")
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_label.config(text="Status: Transcription completed")

    def import_audio(self):
        file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav *.mp3 *.flac *.aac *.ogg *.m4a")])
        if file_path:
            logging.info(f"Imported audio file: {file_path}")
            save_path = self.save_path_entry.get()
            language = self.language_var.get()
            delete_after_transcription = self.delete_after_transcription_var.get()
            logging.info(f"Save Path: {save_path}")
            logging.info(f"Selected Language: {language}")
            logging.info(f"Delete after transcription: {delete_after_transcription}")
            if not save_path:
                save_path = os.path.join("records", "transcription.txt")
                logging.info(f"No save path provided. Using default path: {save_path}")
            if not language:
                logging.error("Error: No language selected.")
                self.status_label.config(text="Error: No language selected.")
                return
            self.status_label.config(text="Status: Transcribing...")
            transcription_start_time = time.time()
            self.recorder.transcribe_audio_from_file(file_path, save_path, language, delete_after_transcription)
            transcription_end_time = time.time()
            logging.info(f"Transcription completed in {transcription_end_time - transcription_start_time:.2f} seconds")
            self.status_label.config(text="Status: Transcription completed")

def main():
    root = Tk()
    app = AppUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()