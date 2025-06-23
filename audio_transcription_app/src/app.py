from PyQt5 import QtWidgets, QtGui, QtCore
import os, json, logging, shutil, datetime
from audio_recorder import AudioRecorder
from transcriber import Transcriber

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SETTINGS_USER_DIR = os.path.join(BASE_DIR, "Settings", "user")
SETTINGS_APP_DIR = os.path.join(BASE_DIR, "Settings", "app")
SETTINGS_FILE = os.path.join(SETTINGS_USER_DIR, "settings.json")
LICENSE_PATHS = [
    os.path.join(SETTINGS_USER_DIR, "LICENSE"),
    os.path.join(os.path.dirname(__file__), "LICENSE"),
]

# Ensure folders exist
for folder in ["Logs", "Records/Audio", "Records/Transcription", "Temp"]:
    os.makedirs(folder, exist_ok=True)

logging.basicConfig(filename=os.path.join("Logs", 'log.txt'), level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                pass
    return {
        "ui": {
            "theme": "light",
            "whisper_mode": "whisper offline",
            "choose_language": "Detect Language Automatically",
            "whisper_model": "Turbo",
            "temp_audio": True,
            "online_model": "whisper-1",
            "online_temp_audio": True
        },
        "first_run": True
    }

def save_settings(settings):
    os.makedirs(SETTINGS_USER_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

class TranscriptionThread(QtCore.QThread):
    transcription_completed = QtCore.pyqtSignal(str, str)
    def __init__(self, transcriber, file_path, save_path, language, model, delete_after_transcription):
        super().__init__()
        self.transcriber = transcriber
        self.file_path = file_path
        self.save_path = save_path
        self.language = language
        self.model = model
        self.delete_after_transcription = delete_after_transcription
    def run(self):
        self.transcriber.transcribe_audio_from_file(self.file_path, self.save_path, self.language, self.model, self.delete_after_transcription)
        self.transcription_completed.emit("Status: Transcription completed", "green")

class AppUI(QtWidgets.QMainWindow):
    def __init__(self):
        self.settings = load_settings()
        super().__init__()
        if self.settings.get("first_run", True):
            self.show_first_run_popup()
            self.settings["first_run"] = False
            save_settings(self.settings)
        self.initUI()
        self.set_theme(self.settings["ui"].get("theme", "light"))
        self._set_ui_defaults()
        self.imported_file_path = self.temp_audio_file_path = self.last_recorded_file_path = None
        self.is_recording = self.is_transcribing = False
        self.transcriber = Transcriber()

    def show_first_run_popup(self):
        message_path = os.path.join(SETTINGS_APP_DIR, "first_run_message.txt")
        msg = "Welcome!\n\nFirst run message file not found."
        if os.path.exists(message_path):
            with open(message_path, "r", encoding="utf-8") as f:
                msg = f.read()
        QtWidgets.QMessageBox.information(self, "First Launch", msg)

    def initUI(self):
        self.setWindowTitle("AudioTranscriber")
        self.setFixedSize(520, 673)
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QtWidgets.QVBoxLayout(central_widget)
        self.recorder = AudioRecorder()
        self.record_button = self.create_button("Start Recording", self.start_recording)
        self.stop_button = self.create_button("Stop Recording", self.stop_recording, enabled=False)
        self.import_button = self.create_button("Import Audio", self.import_audio)
        self.clear_temp_button = self.create_button("Clear Temp Folder", self.clear_temp_folder)
        self.whisper_mode_combo = self.create_combo_box(["Whisper Online", "Whisper Offline"], default=self._get_mode_combo_default())
        self.whisper_mode_combo.currentTextChanged.connect(self.switch_whisper_mode)
        # Offline widgets
        self.language_label = self.create_label("Choose Language:")
        self.language_combo = self.create_combo_box(["Detect Language Automatically", "French", "English", "Spanish", "German", "Chinese", "Japanese", "Russian", "Portuguese", "Italian", "Korean"])
        self.model_label = self.create_label("Choose Whisper Model:")
        self.model_combo = self.create_combo_box(["Turbo", "Tiny", "Base", "Small", "Medium", "Large"], default="Turbo")
        self.file_choice_label = self.create_label("Choose File to Transcribe:")
        self.file_choice_combo = self.create_combo_box(["Last Recorded", "Imported"])
        self.delete_temp_audio_checkbox = self.create_check_box("Temporary audio (will be deleted after transcription)", checked=True)
        self.transcription_button = self.create_button("Start Transcription", self.start_offline_transcription)
        # Online widgets
        self.api_key_label = self.create_label("OpenAI API Key:")
        self.api_key_input = QtWidgets.QLineEdit()
        self.api_key_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.layout.addWidget(self.api_key_input)
        self.online_model_label = self.create_label("Choose Online Model:")
        self.online_model_combo = self.create_combo_box(["whisper-1", "whisper-2"], default="whisper-1")
        self.online_temp_audio_checkbox = self.create_check_box("Temporary audio (will be deleted after online transcription)", checked=True)
        self.online_transcription_button = self.create_button("Start Transcription", self.start_online_transcription)
        self.status_label = self.create_label("Status: Ready", font_size=16, bold=True, alignment=QtCore.Qt.AlignCenter)
        self.size_label = self.create_label(f"Window Size: {self.width()} x {self.height()}", alignment=QtCore.Qt.AlignCenter)
        self.create_menu()
        self.update_status("Status: Ready", "blue")
        self.transcription_button.installEventFilter(self)
        self.online_transcription_button.installEventFilter(self)
        self.switch_whisper_mode(self.whisper_mode_combo.currentText())

    def _set_ui_defaults(self):
        mode = self.settings["ui"].get("whisper_mode", "whisper offline").strip().lower()
        self.whisper_mode_combo.setCurrentText("Whisper Online" if mode == "whisper online" else "Whisper Offline")
        self.language_combo.setCurrentText(self.settings["ui"].get("choose_language", "Detect Language Automatically"))
        self.model_combo.setCurrentText(self.settings["ui"].get("whisper_model", "Turbo"))
        self.delete_temp_audio_checkbox.setChecked(self.settings["ui"].get("temp_audio", True))
        self.online_model_combo.setCurrentText(self.settings["ui"].get("online_model", "whisper-1"))
        self.online_temp_audio_checkbox.setChecked(self.settings["ui"].get("online_temp_audio", True))

    def _get_mode_combo_default(self):
        return "Whisper Online" if self.settings["ui"].get("whisper_mode", "whisper offline").strip().lower() == "whisper online" else "Whisper Offline"

    def create_button(self, text, callback, enabled=True):
        button = QtWidgets.QPushButton(text)
        button.setFont(QtGui.QFont("Arial", 12))
        button.clicked.connect(callback)
        button.setEnabled(enabled)
        self.layout.addWidget(button)
        return button

    def create_label(self, text, font_size=12, bold=False, alignment=None):
        label = QtWidgets.QLabel(text)
        font = QtGui.QFont("Arial", font_size)
        if bold:
            font.setBold(True)
        label.setFont(font)
        if alignment:
            label.setAlignment(alignment)
        self.layout.addWidget(label)
        return label

    def create_combo_box(self, items, default=None):
        combo_box = QtWidgets.QComboBox()
        combo_box.setFont(QtGui.QFont("Arial", 12))
        combo_box.addItems(items)
        if default:
            combo_box.setCurrentText(default)
        self.layout.addWidget(combo_box)
        return combo_box

    def create_check_box(self, text, checked=False):
        check_box = QtWidgets.QCheckBox(text)
        check_box.setChecked(checked)
        self.layout.addWidget(check_box)
        return check_box

    def create_menu(self):
        menubar = self.menuBar()
        settings_menu = menubar.addMenu('Settings')
        theme_menu = settings_menu.addMenu('Theme')
        self.light_theme_action = QtWidgets.QAction('Light Mode', self)
        self.light_theme_action.setCheckable(True)
        self.dark_theme_action = QtWidgets.QAction('Dark Mode', self)
        self.dark_theme_action.setCheckable(True)
        theme_group = QtWidgets.QActionGroup(self)
        theme_group.addAction(self.light_theme_action)
        theme_group.addAction(self.dark_theme_action)
        theme_menu.addAction(self.light_theme_action)
        theme_menu.addAction(self.dark_theme_action)
        self.light_theme_action.triggered.connect(lambda: self.set_theme('light'))
        self.dark_theme_action.triggered.connect(lambda: self.set_theme('dark'))
        if self.settings.get("theme", "light") == "dark":
            self.dark_theme_action.setChecked(True)
        else:
            self.light_theme_action.setChecked(True)
        credits_menu = menubar.addMenu('Credits')
        author_action = QtWidgets.QAction('Author', self)
        author_action.triggered.connect(self.show_author_info)
        credits_menu.addAction(author_action)
        license_action = QtWidgets.QAction('License', self)
        license_action.triggered.connect(self.show_license_info)
        credits_menu.addAction(license_action)

    def set_theme(self, mode):
        if hasattr(self, '_current_theme') and self._current_theme == mode:
            return
        self._current_theme = mode
        self.settings["ui"]["theme"] = mode
        save_settings(self.settings)
        if mode == 'dark':
            qss_path = os.path.join(SETTINGS_APP_DIR, "dark_stylesheet.qss")
            if os.path.exists(qss_path):
                with open(qss_path, "r", encoding="utf-8") as f:
                    dark_stylesheet = f.read()
                self.setStyleSheet(dark_stylesheet)
            else:
                self.setStyleSheet("")
            self.dark_theme_action.setChecked(True)
        else:
            self.setStyleSheet('')
            self.light_theme_action.setChecked(True)

    def show_author_info(self):
        QtWidgets.QMessageBox.information(self, "Author", "Baptiste Lusseau 2025\nGitHub: Ascalance")

    def show_license_info(self):
        for path in LICENSE_PATHS:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    license_text = f.read()
                QtWidgets.QMessageBox.information(self, "License", license_text)
                return
        QtWidgets.QMessageBox.warning(self, "License", "LICENSE file not found.")

    def update_status(self, text, color):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")

    def reset_status(self):
        self.update_status("Status: Ready", "blue")
        self.record_button.setEnabled(True)

    def toggle_recording_buttons(self, recording):
        self.record_button.setEnabled(not recording)
        self.stop_button.setEnabled(recording)
        self.transcription_button.setEnabled(not recording)

    def resizeEvent(self, event):
        self.size_label.setText(f"Window Size: {self.width()} x {self.height()}")
        super().resizeEvent(event)

    def closeEvent(self, event):
        os.makedirs("Temp", exist_ok=True)
        super().closeEvent(event)

    def get_unique_temp_filepath(self, base_path):
        base, extension = os.path.splitext(base_path)
        counter = 1
        new_file_path = base_path
        while os.path.exists(new_file_path):
            new_file_path = f"{base}{counter}{extension}"
            counter += 1
        return new_file_path

    def switch_whisper_mode(self, mode):
        offline_widgets = [
            self.language_label, self.language_combo, self.model_label, self.model_combo,
            self.file_choice_label, self.file_choice_combo, self.delete_temp_audio_checkbox, self.transcription_button
        ]
        online_widgets = [self.api_key_label, self.api_key_input, self.online_model_label, self.online_model_combo, self.online_temp_audio_checkbox, self.online_transcription_button]
        if mode == "Whisper Online":
            for w in offline_widgets:
                w.hide()
            self.file_choice_label.show()
            self.file_choice_combo.show()
            for w in online_widgets:
                w.show()
        else:
            for w in offline_widgets:
                w.show()
            for w in online_widgets:
                w.hide()
        self.settings["ui"]["whisper_mode"] = mode.lower()
        save_settings(self.settings)

    def start_recording(self):
        logging.info("Starting recording...")
        self.recorder.start_recording()
        self.toggle_recording_buttons(recording=True)
        self.update_status("Status: Recording...", "red")

    def stop_recording(self):
        self.recorder.stop_recording()
        self.temp_audio_file_path = self.get_unique_temp_filepath("Temp/record.wav")
        self.recorder.save_recording(self.temp_audio_file_path)
        self.update_status("Status: Recording completed", "orange")
        self.toggle_recording_buttons(recording=False)
        if not self.delete_temp_audio_checkbox.isChecked():
            audio_save_path = os.path.join("Records", "Audio", datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".wav")
            shutil.move(self.temp_audio_file_path, audio_save_path)
            self.temp_audio_file_path = audio_save_path
        self.last_recorded_file_path = self.temp_audio_file_path

    def import_audio(self):
        options = QtWidgets.QFileDialog.Options()
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import Audio File", "", "Audio Files (*.wav *.mp3 *.flac *.m4a *.aac *.ogg *.wma);;All Files (*)", options=options)
        if file_path:
            self.imported_file_path = file_path
            self.last_recorded_file_path = file_path
            self.update_status("Status: Audio imported", "orange")

    def clear_temp_folder(self):
        reply = QtWidgets.QMessageBox.question(self, 'Clear Temp Folder', 'Are you sure you want to clear the Temp folder?', QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            for filename in os.listdir("Temp"):
                file_path = os.path.join("Temp", filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    logging.error(f"Failed to delete {file_path}. Reason: {e}")
            self.update_status("Status: Temp folder cleared", "green")
            QtCore.QTimer.singleShot(2000, self.reset_status)
        else:
            self.update_status("Status: Temp folder clear cancelled", "orange")
            QtCore.QTimer.singleShot(2000, self.reset_status)

    def start_offline_transcription(self):
        if self.is_recording:
            self.update_status("Status: Cannot transcribe while recording", "red")
            return
        if self.is_transcribing:
            self.update_status("Status: Transcription already in progress", "red")
            return
        self.is_transcribing = True
        self.transcription_button.setEnabled(False)
        self.update_status("Status: Transcribing...", "purple")
        save_path = os.path.join("Records", "Transcription", datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".txt")
        language = self.language_combo.currentText()
        if language == "Detect Language Automatically":
            language = None
        model = self.model_combo.currentText()
        delete_temp_audio = self.delete_temp_audio_checkbox.isChecked()
        file_choice = self.file_choice_combo.currentText()
        if file_choice == "Imported" and self.imported_file_path:
            file_path = self.imported_file_path
            delete_after_transcription = file_path.startswith("Temp")
        elif file_choice == "Last Recorded" and self.last_recorded_file_path:
            file_path = self.last_recorded_file_path
            delete_after_transcription = delete_temp_audio and file_path.startswith("Temp")
        else:
            self.update_status("Status: No file selected for transcription", "red")
            self.is_transcribing = False
            self.transcription_button.setEnabled(True)
            return
        self.transcription_thread = TranscriptionThread(self.transcriber, file_path, save_path, language, model, delete_after_transcription)
        self.transcription_thread.transcription_completed.connect(self.on_transcription_completed)
        self.transcription_thread.start()

    def on_transcription_completed(self, status, color):
        self.update_status(status, color)
        self.is_transcribing = False
        self.transcription_button.setEnabled(True)
        QtCore.QTimer.singleShot(2000, lambda: self.update_status("Status: Ready", "blue"))

    def start_online_transcription(self):
        from online import OnlineTranscriber
        api_key = self.api_key_input.text().strip()
        if not api_key:
            self.update_status("Status: Please enter your OpenAI API key", "red")
            return
        file_path = self.imported_file_path or self.last_recorded_file_path
        if not file_path:
            self.update_status("Status: No audio file selected", "red")
            return
        model = self.online_model_combo.currentText()
        delete_temp = self.online_temp_audio_checkbox.isChecked()
        self.update_status("Status: Online transcription in progress...", "purple")
        try:
            transcriber = OnlineTranscriber(api_key=api_key)
            text = transcriber.transcribe_audio_from_file(file_path, model=model)
            if text:
                save_path = os.path.join("Records", "Transcription", datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_online.txt")
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                if delete_temp and file_path.startswith("Temp"):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
                self.update_status("Status: Online transcription completed", "green")
            else:
                self.update_status("Status: Error during online transcription", "red")
        except Exception as e:
            self.update_status(f"Status: {e}", "red")

    def on_language_changed(self, language):
        self.settings["ui"]["choose_language"] = language
        save_settings(self.settings)
    def on_model_changed(self, model):
        self.settings["ui"]["whisper_model"] = model
        save_settings(self.settings)
    def on_temp_audio_changed(self, checked):
        self.settings["ui"]["temp_audio"] = checked
        save_settings(self.settings)
    def on_online_model_changed(self, model):
        self.settings["ui"]["online_model"] = model
        save_settings(self.settings)
    def on_online_temp_audio_changed(self, checked):
        self.settings["ui"]["online_temp_audio"] = checked
        save_settings(self.settings)
