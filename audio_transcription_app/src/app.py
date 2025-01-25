from PyQt5 import QtWidgets, QtGui, QtCore
from audio_recorder import AudioRecorder
from transcriber import Transcriber
import logging
import os
import shutil
import datetime

os.makedirs("Logs", exist_ok=True)
os.makedirs("Records/Audio", exist_ok=True)
os.makedirs("Records/Transcription", exist_ok=True)
os.makedirs("Temp", exist_ok=True)

shutil.rmtree("Temp")
os.makedirs("Temp", exist_ok=True)

logging.basicConfig(filename=os.path.join("Logs", 'log.txt'), level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AppUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.imported_file_path = None
        self.temp_audio_file_path = None
        self.last_recorded_file_path = None
        self.is_recording = False
        self.transcriber = Transcriber()

    def initUI(self):
        self.setWindowTitle("AudioTranscriber")
        self.setGeometry(100, 100, 500, 400)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        self.recorder = AudioRecorder()

        self.record_button = self.create_button("Start Recording", self.start_recording, layout)
        self.stop_button = self.create_button("Stop Recording", self.stop_recording, layout, enabled=False)
        self.import_button = self.create_button("Import Audio", self.import_audio, layout)

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
        label.setStyleSheet(f"color: {color};")
        if alignment:
            label.setAlignment(alignment)
        layout.addWidget(label)
        return label

    def create_combo_box(self, items, layout, default=None):
        combo_box = QtWidgets.QComboBox()
        combo_box.setFont(QtGui.QFont("Arial", 12))
        for item in items:
            combo_box.addItem(item)
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
        credits_menu = menubar.addMenu('Credits')

        author_action = QtWidgets.QAction('Author', self)
        author_action.triggered.connect(self.show_author_info)
        credits_menu.addAction(author_action)

        license_action = QtWidgets.QAction('License', self)
        license_action.triggered.connect(self.show_license_info)
        credits_menu.addAction(license_action)

    def show_author_info(self):
        QtWidgets.QMessageBox.information(self, "Author", "Baptiste Lusseau 2025\nGitHub: Ascalance")

    def show_license_info(self):
        QtWidgets.QMessageBox.information(self, "License", "This software is licensed under the MIT License.")

    def start_recording(self):
        logging.info("Starting recording...")
        self.recorder.start_recording()
        self.record_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.transcription_button.setEnabled(False)
        self.is_recording = True
        self.update_status("Status: Recording...", "red")

    def stop_recording(self):
        self.recorder.stop_recording()
        self.temp_audio_file_path = os.path.join("temp", "record.wav")
        self.recorder.save_recording(self.temp_audio_file_path)
        self.update_status("Status: Recording completed", "orange")
        self.stop_button.setEnabled(False)
        self.record_button.setEnabled(True)
        self.transcription_button.setEnabled(True)
        self.is_recording = False
        if not self.delete_temp_audio_checkbox.isChecked():
            audio_save_path = os.path.join("Records", "Audio", datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".wav")
            shutil.move(self.temp_audio_file_path, audio_save_path)
            self.temp_audio_file_path = audio_save_path
        self.last_recorded_file_path = self.temp_audio_file_path

    def start_transcription(self):
        if self.is_recording:
            self.update_status("Status: Cannot transcribe while recording", "red")
            return
        save_path = os.path.join("Records", "Transcription", datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".txt")
        language = self.language_combo.currentText()
        if language == "Detect Language Automatically":
            language = None
        model = self.model_combo.currentText()
        logging.info(f"Using model: {model}")
        delete_temp_audio = self.delete_temp_audio_checkbox.isChecked()
        self.update_status("Status: Transcribing...", "purple")
        file_choice = self.file_choice_combo.currentText()
        if file_choice == "Imported" and self.imported_file_path:
            self.transcriber.transcribe_audio_from_file(self.imported_file_path, save_path, language, model, delete_after_transcription=False)
            self.imported_file_path = None
            self.update_status("Status: Transcription completed", "green")
        elif file_choice == "Last Recorded" and self.last_recorded_file_path:
            self.transcriber.transcribe_audio_from_file(self.last_recorded_file_path, save_path, language, model, delete_after_transcription=delete_temp_audio)
            if delete_temp_audio and os.path.exists(self.last_recorded_file_path):
                os.remove(self.last_recorded_file_path)
            self.last_recorded_file_path = None
            self.update_status("Status: Transcription completed", "green")
        else:
            self.update_status("Status: No file selected for transcription", "red")
            return
        QtCore.QTimer.singleShot(2000, self.reset_status)

    def update_status(self, text, color):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")

    def reset_status(self):
        self.update_status("Status: Ready", "blue")
        self.record_button.setEnabled(True)

    def import_audio(self):
        options = QtWidgets.QFileDialog.Options()
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import Audio File", "", "Audio Files (*.wav *.mp3 *.flac *.m4a *.aac *.ogg *.wma);;All Files (*)", options=options)
        if file_path:
            self.imported_file_path = file_path
            self.last_recorded_file_path = file_path
            self.update_status("Status: Audio imported", "orange")

    def resizeEvent(self, event):
        self.size_label.setText(f"Window Size: {self.width()} x {self.height()}")
        super().resizeEvent(event)

    def closeEvent(self, event):
        shutil.rmtree("Temp")
        os.makedirs("Temp", exist_ok=True)
        super().closeEvent(event)
