from PyQt5 import QtWidgets, QtGui, QtCore
from audio_recorder import AudioRecorder
import logging
import os
import shutil
import datetime

# Create necessary directories if they don't exist
os.makedirs("Logs", exist_ok=True)
os.makedirs("Records/Audio", exist_ok=True)
os.makedirs("Records/Transcription", exist_ok=True)
os.makedirs("Temp", exist_ok=True)

# Clear the Temp directory at startup
shutil.rmtree("Temp")
os.makedirs("Temp", exist_ok=True)

log_dir = "Logs"
logging.basicConfig(filename=os.path.join(log_dir, 'log.txt'), level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AppUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.imported_file_path = None
        self.temp_audio_file_path = None
        self.last_recorded_file_path = None
        self.is_recording = False

    def initUI(self):
        self.setWindowTitle("AudioTranscriber")
        self.setGeometry(100, 100, 500, 400)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        self.recorder = AudioRecorder()

        self.record_button = QtWidgets.QPushButton("Start Recording")
        self.record_button.setFont(QtGui.QFont("Arial", 12))
        self.record_button.clicked.connect(self.start_recording)
        layout.addWidget(self.record_button)

        self.stop_button = QtWidgets.QPushButton("Stop Recording")
        self.stop_button.setFont(QtGui.QFont("Arial", 12))
        self.stop_button.clicked.connect(self.stop_recording)
        self.stop_button.setEnabled(False)
        layout.addWidget(self.stop_button)

        self.import_button = QtWidgets.QPushButton("Import Audio")
        self.import_button.setFont(QtGui.QFont("Arial", 12))
        self.import_button.clicked.connect(self.import_audio)
        layout.addWidget(self.import_button)

        self.language_label = QtWidgets.QLabel("Choose Language:")
        self.language_label.setFont(QtGui.QFont("Arial", 12))
        layout.addWidget(self.language_label)

        self.language_combo = QtWidgets.QComboBox()
        self.language_combo.setFont(QtGui.QFont("Arial", 12))
        self.language_combo.addItem("Detect Language Automatically", None)
        self.language_combo.addItem("French", "fr")
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("Spanish", "es")
        self.language_combo.addItem("German", "de")
        self.language_combo.addItem("Chinese", "zh")
        self.language_combo.addItem("Japanese", "ja")
        self.language_combo.addItem("Russian", "ru")
        self.language_combo.addItem("Portuguese", "pt")
        self.language_combo.addItem("Italian", "it")
        self.language_combo.addItem("Korean", "ko")
        layout.addWidget(self.language_combo)

        self.model_label = QtWidgets.QLabel("Choose Whisper Model:")
        self.model_label.setFont(QtGui.QFont("Arial", 12))
        layout.addWidget(self.model_label)

        self.model_combo = QtWidgets.QComboBox()
        self.model_combo.setFont(QtGui.QFont("Arial", 12))
        self.model_combo.addItem("Turbo", "turbo")
        self.model_combo.addItem("Tiny", "tiny")
        self.model_combo.addItem("Base", "base")
        self.model_combo.addItem("Small", "small")
        self.model_combo.addItem("Medium", "medium")
        self.model_combo.addItem("Large", "large")
        self.model_combo.setCurrentText("Turbo")
        layout.addWidget(self.model_combo)

        self.save_path_label = QtWidgets.QLabel("Transcription Save Path:")
        self.save_path_label.setFont(QtGui.QFont("Arial", 12))
        layout.addWidget(self.save_path_label)

        self.save_path_entry = QtWidgets.QLineEdit()
        self.save_path_entry.setFont(QtGui.QFont("Arial", 12))
        layout.addWidget(self.save_path_entry)

        self.delete_temp_audio_checkbox = QtWidgets.QCheckBox("Delete temporary audio after transcription")
        self.delete_temp_audio_checkbox.setChecked(True)
        layout.addWidget(self.delete_temp_audio_checkbox)

        self.transcription_button = QtWidgets.QPushButton("Start Transcription")
        self.transcription_button.setFont(QtGui.QFont("Arial", 12))
        self.transcription_button.clicked.connect(self.start_transcription)
        layout.addWidget(self.transcription_button)

        self.file_choice_label = QtWidgets.QLabel("Choose File to Transcribe:")
        self.file_choice_label.setFont(QtGui.QFont("Arial", 12))
        layout.addWidget(self.file_choice_label)

        self.file_choice_combo = QtWidgets.QComboBox()
        self.file_choice_combo.setFont(QtGui.QFont("Arial", 12))
        self.file_choice_combo.addItem("Last Recorded", "last_recorded")
        self.file_choice_combo.addItem("Imported", "imported")
        layout.addWidget(self.file_choice_combo)

        self.status_label = QtWidgets.QLabel("Status: Ready")
        self.status_label.setFont(QtGui.QFont("Arial", 16, QtGui.QFont.Bold))
        self.status_label.setStyleSheet("color: blue;")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.size_label = QtWidgets.QLabel(f"Window Size: {self.width()} x {self.height()}")
        self.size_label.setFont(QtGui.QFont("Arial", 12))
        self.size_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.size_label)

        self.create_menu()

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
        self.status_label.setText("Status: Recording...")
        self.status_label.setStyleSheet("color: red;")

    def stop_recording(self):
        self.recorder.stop_recording()
        self.temp_audio_file_path = os.path.join("temp", "record.wav")
        self.recorder.save_recording(self.temp_audio_file_path)
        self.status_label.setText("Status: Recording completed")
        self.status_label.setStyleSheet("color: orange;")
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
            self.status_label.setText("Status: Cannot transcribe while recording")
            self.status_label.setStyleSheet("color: red;")
            return
        save_path = self.save_path_entry.text()
        if save_path:
            if not os.path.isabs(save_path):
                save_path = os.path.join("Records", "Transcription", save_path)
            if not save_path.endswith(".txt"):
                save_path += ".txt"
        else:
            save_path = os.path.join("Records", "Transcription", datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".txt")
        language = self.language_combo.currentData()
        model = self.model_combo.currentData()
        delete_temp_audio = self.delete_temp_audio_checkbox.isChecked()
        self.status_label.setText("Status: Transcribing...")
        self.status_label.setStyleSheet("color: purple;")
        file_choice = self.file_choice_combo.currentData()
        if file_choice == "imported" and self.imported_file_path:
            self.recorder.transcribe_audio_from_file(self.imported_file_path, save_path, language, model, delete_after_transcription=False)
            self.imported_file_path = None
        elif file_choice == "last_recorded" and self.last_recorded_file_path:
            self.recorder.transcribe_audio_from_file(self.last_recorded_file_path, save_path, language, model, delete_after_transcription=delete_temp_audio)
            if delete_temp_audio:
                os.remove(self.last_recorded_file_path)
            self.last_recorded_file_path = None
        else:
            self.status_label.setText("Status: No file selected for transcription")
            self.status_label.setStyleSheet("color: red;")
            return
        self.status_label.setText("Status: Transcription completed")
        self.status_label.setStyleSheet("color: green;")
        QtCore.QTimer.singleShot(2000, self.reset_status)

    def reset_status(self):
        self.status_label.setText("Status: Ready")
        self.status_label.setStyleSheet("color: blue;")
        self.record_button.setEnabled(True)

    def import_audio(self):
        options = QtWidgets.QFileDialog.Options()
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import Audio File", "", "Audio Files (*.wav *.mp3 *.flac *.m4a *.aac *.ogg *.wma);;All Files (*)", options=options)
        if file_path:
            self.imported_file_path = file_path
            self.status_label.setText("Status: Audio imported")
            self.status_label.setStyleSheet("color: orange;")

    def resizeEvent(self, event):
        self.size_label.setText(f"Window Size: {self.width()} x {self.height()}")
        super().resizeEvent(event)

    def closeEvent(self, event):
        # Clear the Temp directory at shutdown
        shutil.rmtree("Temp")
        os.makedirs("Temp", exist_ok=True)
        event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = AppUI()
    window.show()
    app.exec_()