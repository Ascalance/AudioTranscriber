from PyQt5 import QtWidgets, QtGui, QtCore
from audio_recorder import AudioRecorder
from transcriber import Transcriber
import logging
import os
import shutil
import datetime
import threading

os.makedirs("Logs", exist_ok=True)
os.makedirs("Records/Audio", exist_ok=True)
os.makedirs("Records/Transcription", exist_ok=True)
os.makedirs("Temp", exist_ok=True)

logging.basicConfig(filename=os.path.join("Logs", 'log.txt'), level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        super().__init__()
        self.initUI()
        self.imported_file_path = None
        self.temp_audio_file_path = None
        self.last_recorded_file_path = None
        self.is_recording = False
        self.is_transcribing = False
        self.transcriber = Transcriber()

    def initUI(self):
        self.setWindowTitle("AudioTranscriber")
        self.setGeometry(100, 100, 500, 673)
        self.setFixedWidth(520)
        self.setFixedHeight(673)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QtWidgets.QVBoxLayout(central_widget)

        self.recorder = AudioRecorder()

        self.record_button = self.create_button("Start Recording", self.start_recording, self.layout)
        self.stop_button = self.create_button("Stop Recording", self.stop_recording, self.layout, enabled=False)
        self.import_button = self.create_button("Import Audio", self.import_audio, self.layout)
        self.clear_temp_button = self.create_button("Clear Temp Folder", self.clear_temp_folder, self.layout)

        self.whisper_mode_combo = self.create_combo_box(["Whisper Online", "Whisper Offline"], self.layout, default="Whisper Offline")
        self.whisper_mode_combo.currentTextChanged.connect(self.switch_whisper_mode)

        # Offline widgets
        self.language_label = self.create_label("Choose Language:", self.layout)
        self.language_combo = self.create_combo_box(["Detect Language Automatically", "French", "English", "Spanish", "German", "Chinese", "Japanese", "Russian", "Portuguese", "Italian", "Korean"], self.layout)
        self.model_label = self.create_label("Choose Whisper Model:", self.layout)
        self.model_combo = self.create_combo_box(["Turbo", "Tiny", "Base", "Small", "Medium", "Large"], self.layout, default="Turbo")
        self.file_choice_label = self.create_label("Choose File to Transcribe:", self.layout)
        self.file_choice_combo = self.create_combo_box(["Last Recorded", "Imported"], self.layout)
        self.delete_temp_audio_checkbox = self.create_check_box("Temporary audio (will be deleted after transcription)", self.layout, checked=True)
        self.transcription_button = self.create_button("Start Transcription", self.start_offline_transcription, self.layout)

        # Online widgets
        self.api_key_label = self.create_label("OpenAI API Key:", self.layout)
        self.api_key_input = QtWidgets.QLineEdit()
        self.api_key_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.layout.addWidget(self.api_key_input)
        self.online_transcription_button = self.create_button("Start Transcription", self.start_online_transcription, self.layout)

        self.status_label = self.create_label("Status: Ready", self.layout, font_size=16, bold=True, alignment=QtCore.Qt.AlignCenter, color="blue")
        self.size_label = self.create_label(f"Window Size: {self.width()} x {self.height()}", self.layout, alignment=QtCore.Qt.AlignCenter)
        self.create_menu()

        self.transcription_button.installEventFilter(self)
        self.online_transcription_button.installEventFilter(self)

        self.switch_whisper_mode(self.whisper_mode_combo.currentText())

        self.setGeometry(100, 100, 500, 400)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        self.recorder = AudioRecorder()

        self.record_button = self.create_button("Start Recording", self.start_recording, layout)
        self.stop_button = self.create_button("Stop Recording", self.stop_recording, layout, enabled=False)
        self.import_button = self.create_button("Import Audio", self.import_audio, layout)
        
        self.clear_temp_button = self.create_button("Clear Temp Folder", self.clear_temp_folder, layout)

        self.language_label = self.create_label("Choose Language:", layout)
        self.language_combo = self.create_combo_box(["Detect Language Automatically", "French", "English", "Spanish", "German", "Chinese", "Japanese", "Russian", "Portuguese", "Italian", "Korean"], layout)

        self.model_label = self.create_label("Choose Whisper Model:", layout)
        self.model_combo = self.create_combo_box(["Turbo", "Tiny", "Base", "Small", "Medium", "Large"], layout, default="Turbo")

        self.file_choice_label = self.create_label("Choose File to Transcribe:", layout)
        self.file_choice_combo = self.create_combo_box(["Last Recorded", "Imported"], layout)

        self.delete_temp_audio_checkbox = self.create_check_box("Temporary audio (will be deleted after transcription)", layout, checked=True)

        self.transcription_button = self.create_button("Start Transcription", self.start_transcription, layout)

        self.status_label = self.create_label("Status: Ready", layout, font_size=16, bold=True, color="blue", alignment=QtCore.Qt.AlignCenter)

        self.size_label = self.create_label(f"Window Size: {self.width()} x {self.height()}", layout, alignment=QtCore.Qt.AlignCenter)

        self.create_menu()

    def create_button(self, text, callback, layout, enabled=True):
        button = QtWidgets.QPushButton(text)
        button.setFont(QtGui.QFont("Arial", 12))
        button.clicked.connect(callback)
        button.setEnabled(enabled)
        layout.addWidget(button)
        return button

    def create_label(self, text, layout, font_size=12, bold=False, color="black", alignment=None):
        label = QtWidgets.QLabel(text)
        font = QtGui.QFont("Arial", font_size)
        if bold:
            font.setBold(True)
        label.setFont(font)
        # Remove color argument, let stylesheet handle it globally
        label.setStyleSheet(f"color: {color};")
        if alignment:
            label.setAlignment(alignment)
        layout.addWidget(label)
        return label

    def create_combo_box(self, items, layout, default=None):
        combo_box = QtWidgets.QComboBox()
        combo_box.setFont(QtGui.QFont("Arial", 12))
        combo_box.addItems(items)
        if default:
            combo_box.setCurrentText(default)
        layout.addWidget(combo_box)
        return combo_box

    def create_check_box(self, text, layout, checked=False):
        check_box = QtWidgets.QCheckBox(text)
        check_box.setChecked(checked)
        layout.addWidget(check_box)
        return check_box

    def create_menu(self):
        menubar = self.menuBar()

        # Add theme menu before credits
        theme_menu = menubar.addMenu('Theme')
        self.theme_action = QtWidgets.QAction('Toggle Dark/Light Mode', self)
        self.theme_action.setCheckable(True)
        self.theme_action.triggered.connect(self.toggle_theme)
        theme_menu.addAction(self.theme_action)
        credits_menu = menubar.addMenu('Credits')
        author_action = QtWidgets.QAction('Author', self)
        author_action.triggered.connect(self.show_author_info)
        credits_menu.addAction(author_action)

        license_action = QtWidgets.QAction('License', self)
        license_action.triggered.connect(self.show_license_info)
        credits_menu.addAction(license_action)

    def toggle_theme(self):
        # VSCode dark theme colors
        dark_stylesheet = '''
            QWidget { background-color: #1e1e1e; color: #d4d4d4; }
            QLineEdit, QComboBox, QTextEdit, QPlainTextEdit { background-color: #252526; color: #d4d4d4; border: 1px solid #3c3c3c; }
            QPushButton { background-color: #2d2d2d; color: #d4d4d4; border: 1px solid #3c3c3c; }
            QPushButton:pressed { background-color: #373737; }
            QMenuBar { background-color: #2d2d2d; color: #d4d4d4; }
            QMenuBar::item:selected { background: #373737; }
            QMenu { background-color: #2d2d2d; color: #d4d4d4; }
            QMenu::item:selected { background-color: #373737; }
            QCheckBox { background-color: transparent; color: #d4d4d4; }
            QLabel { color: #d4d4d4; }
            QScrollBar:vertical, QScrollBar:horizontal { background: #2d2d2d; }
        '''
        light_stylesheet = ''  # Default Qt style (no override)
        if self.theme_action.isChecked():
            self.setStyleSheet(dark_stylesheet)
        else:
            self.setStyleSheet(light_stylesheet)

    def show_author_info(self):
        QtWidgets.QMessageBox.information(self, "Author", "Baptiste Lusseau 2025\nGitHub: Ascalance")

    def show_license_info(self):
        QtWidgets.QMessageBox.information(self, "License", "This software is licensed under the MIT License.")

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
            temp_folder = "Temp"
            for filename in os.listdir(temp_folder):
                file_path = os.path.join(temp_folder, filename)
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

    def toggle_recording_buttons(self, recording):
        self.record_button.setEnabled(not recording)
        self.stop_button.setEnabled(recording)
        self.transcription_button.setEnabled(not recording)

    def update_status(self, text, color):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")

    def reset_status(self):
        self.update_status("Status: Ready", "blue")
        self.record_button.setEnabled(True)

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
        online_widgets = [self.api_key_label, self.api_key_input, self.online_transcription_button]
        # Always show file_choice_label and file_choice_combo in online mode as well
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
        # ...existing code...

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
        self.update_status("Status: Online transcription in progress...", "purple")
        try:
            transcriber = OnlineTranscriber(api_key=api_key)
            text = transcriber.transcribe_audio_from_file(file_path)
            if text:
                save_path = os.path.join("Records", "Transcription", datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_online.txt")
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                self.update_status("Status: Online transcription completed", "green")
            else:
                self.update_status("Status: Error during online transcription", "red")
        except Exception as e:
            self.update_status(f"Status: {e}", "red")
