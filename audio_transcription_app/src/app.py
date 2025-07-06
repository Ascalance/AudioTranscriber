from PyQt5 import QtWidgets, QtGui, QtCore
import os
import json
import logging
import shutil
import datetime
import warnings
import keyring
import subprocess
from tools.general.audio_recorder import AudioRecorder
from tools.offline.transcriber import Transcriber
from tools.app_threads.transcription_thread import TranscriptionThread
from tools.app_threads.online_transcription_thread import OnlineTranscriptionThread

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SETTINGS_USER_DIR = os.path.join(BASE_DIR, "Settings", "user")
SETTINGS_APP_DIR = os.path.join(BASE_DIR, "Settings", "app")
SETTINGS_FILE = os.path.join(SETTINGS_USER_DIR, "settings.json")
LICENSE_PATHS = [
    os.path.join(SETTINGS_USER_DIR, "LICENSE"),
    os.path.join(os.path.dirname(__file__), "LICENSE"),
]
I18N_DIR = os.path.join(SETTINGS_APP_DIR, "i18n")
LANGUAGES = {
    # Europe
    "Français (Europe)": "fr_FR.json",
    "English (Europe)": "en_US.json",
    "Deutsch (Europe)": "de_DE.json",
    "Español (Europe)": "es_ES.json",
    "Português (Europe)": "pt_PT.json",
    "Русский (Europe/Asia)": "ru_RU.json",
    # Asie
    "中文 (Asia)": "zh_CN.json",
    "日本語 (Asia)": "ja_JP.json",
    "한국어 (Asia)": "ko_KR.json",
    "हिन्दी (Asia)": "hi_IN.json"
}

# Ensure folders exist
for folder in ["Logs", "Records/Audio", "Records/Transcription", "Temp"]:
    os.makedirs(folder, exist_ok=True)

# Logging is now configured in main.py to ensure all logs go to Logs/log.txt

# Redirect Whisper FP16 warning to log only
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

# Optionally, log the warning manually at startup
logging.warning("FP16 is not supported on CPU; using FP32 instead (Whisper). This warning is suppressed in the terminal.")

def load_settings():
    notify_missing = False
    missing_keys = []
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            try:
                user_settings = json.load(f)
            except Exception as e:
                logging.error(f"Failed to load settings: {e}")
                user_settings = {}
        # Charger les paramètres par défaut
        default_settings_path = os.path.join(SETTINGS_APP_DIR, "default_settings.json")
        if os.path.exists(default_settings_path):
            with open(default_settings_path, "r", encoding="utf-8") as f:
                default_settings = json.load(f)
            # Synchroniser les clés manquantes
            for section in default_settings:
                if section not in user_settings:
                    user_settings[section] = default_settings[section]
                    notify_missing = True
                    missing_keys.append(section)
                elif isinstance(default_settings[section], dict):
                    for key in default_settings[section]:
                        if key not in user_settings[section]:
                            user_settings[section][key] = default_settings[section][key]
                            notify_missing = True
                            missing_keys.append(key)
            if notify_missing:
                with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                    json.dump(user_settings, f, indent=2)
                # Notification dans la langue de l'utilisateur
                lang = user_settings.get("ui", {}).get("language", "English (Europe)")
                lang_file = LANGUAGES.get(lang, "en_US.json")
                translations = load_translation(lang_file)
                msg = translations.get("msg_settings_sync", "Some settings were missing and have been restored to default values.")
                QtWidgets.QMessageBox.information(None, translations.get("label_settings", "Settings"), msg)
            return user_settings
        return user_settings
    # Si settings.json n'existe pas, copie le fichier de paramètres par défaut
    default_settings_path = os.path.join(SETTINGS_APP_DIR, "default_settings.json")
    if os.path.exists(default_settings_path):
        with open(default_settings_path, "r", encoding="utf-8") as f:
            default_settings = json.load(f)
        os.makedirs(SETTINGS_USER_DIR, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_settings, f, indent=2)
        return default_settings
    # Fallback si le fichier par défaut n'existe pas
    return {
        "ui": {
            "theme": "light",
            "whisper_mode": "whisper offline",
            "choose_language": "Detect Language Automatically",
            "whisper_model": "Turbo",
            "temp_audio": True,
            "online_model": "whisper-1",
            "online_temp_audio": True,
            "language": "English (Europe)",
            "open_transcription_folder": True,
            "window_width": 530,
            "window_height": 700
        },
        "first_run": True
    }

def save_settings(settings):
    os.makedirs(SETTINGS_USER_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

def load_translation(lang_file):
    path = os.path.join(I18N_DIR, lang_file)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# --- MODE MAPPING FOR LANGUAGE-INDEPENDENT LOGIC ---
WHISPER_MODE_MAP = {
    "online": "combo_whisper_online",
    "offline": "combo_whisper_offline"
}
WHISPER_MODE_REVERSE_MAP = {  # For lookup by translated label
    # Will be filled at runtime
}

SERVICE_NAME = "AudioTranscriber_OpenAI_API"

class AppUI(QtWidgets.QMainWindow):
    def update_online_transcribe_button_state(self):
        """
        Active/désactive le bouton online selon :
        - un fichier audio sélectionné/importé
        - une clé OpenAI renseignée
        """
        file_ok = bool(self.get_selected_audio_file())
        api_key_ok = bool(self.api_key_input.text().strip())
        self.online_transcription_button.setEnabled(file_ok and api_key_ok)

    VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')

    def get_file_choice_english(self, value):
        """
        Map localized file_choice_combo values to their English equivalents for logging.
        """
        mapping = {
            # French
            "dernier enregistrement": "Last Recorded",
            "importé": "Imported",
            # English
            "last recorded": "Last Recorded",
            "imported": "Imported",
            # German
            "letzte aufnahme": "Last Recorded",
            "importiert": "Imported",
            # Spanish
            "última grabación": "Last Recorded",
            "importado": "Imported",
            # Portuguese
            "última gravação": "Last Recorded",
            "importado": "Imported",
            # Russian
            "последняя запись": "Last Recorded",
            "импортировано": "Imported",
            # Chinese (Simplified)
            "最新录音": "Last Recorded",
            "导入": "Imported",
            # Japanese
            "最新の録音": "Last Recorded",
            "インポート": "Imported",
            # Korean
            "마지막 녹음": "Last Recorded",
            "가져오기": "Imported",
            # Hindi
            "अंतिम रिकॉर्डिंग": "Last Recorded",
            "आयातित": "Imported",
        }
        v = value.strip().lower()
        return mapping.get(v, value)
    def normalize_language(self, language):
        """
        Map any UI string for 'Detect Language Automatically' (in any language) to None for Whisper.
        """
        auto_detect_labels = [
            "Detect Language Automatically",
            "détection automatique de la langue",
            "Erkennung der Sprache automatisch",
            "Detectar idioma automáticamente",
            "Detectar idioma automaticamente",
            "Автоматическое определение языка",
            "自动检测语言",
            "言語を自動検出",
            "언어 자동 감지",
            "भाषा स्वचालित रूप से पहचानें",
            # Add more as needed for other supported UI languages
        ]
        # Also check translation key fallback
        if language is None:
            return None
        if language.strip().lower() in [l.lower() for l in auto_detect_labels]:
            return None
        return language
    def __init__(self):
        self.is_recording = False
        self.is_transcribing = False
        self.last_recorded_file_path = None
        self.imported_file_path = None
        self.transcriber = Transcriber()
        self.settings = load_settings()
        self.translations = {}
        super().__init__()
        # Enable drag and drop
        self.setAcceptDrops(True)
        # Overlay for drag-and-drop visual feedback
        self._drag_overlay = None
        lang_name = self.settings["ui"].get("language") or "English (Europe)"
        self.set_language(lang_name)
        if self.settings.get("first_run", True):
            self.show_first_run_popup()
            self.settings["first_run"] = False
            save_settings(self.settings)
        self._theme_pending = self.settings["ui"].get("theme", "light")
        self.initUI()
        # set_theme must be called after initUI (menu/actions created)
        if hasattr(self, 'light_theme_action') and hasattr(self, 'dark_theme_action'):
            self.set_theme(self._theme_pending)
        else:
            QtCore.QTimer.singleShot(0, self._apply_pending_theme)

    def _apply_pending_theme(self):
        if hasattr(self, 'light_theme_action') and hasattr(self, 'dark_theme_action'):
            self.set_theme(self._theme_pending)
        # Load API key from keyring if present
        api_key = keyring.get_password(SERVICE_NAME, "user")
        if api_key:
            self.api_key_input.setText(api_key)

    def _show_drag_overlay(self):
        if self._drag_overlay is not None:
            return
        self._drag_overlay = QtWidgets.QWidget(self)
        self._drag_overlay.setGeometry(0, 0, self.width(), self.height())
        self._drag_overlay.setStyleSheet("background-color: rgba(128, 128, 128, 120);")
        self._drag_overlay.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self._drag_overlay.show()

    def _hide_drag_overlay(self):
        if self._drag_overlay is not None:
            self._drag_overlay.hide()
            self._drag_overlay.deleteLater()
            self._drag_overlay = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    ext = os.path.splitext(url.toLocalFile())[1].lower()
                    if ext in [".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".wma"] + list(self.VIDEO_EXTENSIONS):
                        event.acceptProposedAction()
                        self._show_drag_overlay()
                        return
        event.ignore()

    def dropEvent(self, event):
        self._hide_drag_overlay()
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in [".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".wma"] + list(self.VIDEO_EXTENSIONS):
                        if ext in self.VIDEO_EXTENSIONS:
                            audio_path = self.extract_audio_from_video(file_path)
                            if audio_path:
                                self.imported_file_path = audio_path
                                self._is_temp_extracted_audio = True
                                self.update_status(self.t("status_audio_imported") if self.t("status_audio_imported") != "status_audio_imported" else "Status: Audio extracted from video and imported (drag-and-drop)", "orange")
                                logging.info(f"Video file dropped, extracted audio: {file_path} -> {audio_path}")
                            else:
                                QtWidgets.QMessageBox.warning(self, "Import Error", "Failed to extract audio from video file.")
                                return
                        else:
                            self.imported_file_path = file_path
                            self._is_temp_extracted_audio = False
                            self.update_status(self.t("status_audio_imported") if self.t("status_audio_imported") != "status_audio_imported" else "Status: Audio imported (drag-and-drop)", "orange")
                            logging.info(f"Audio file imported via drag-and-drop: {file_path}")
                        self.transcription_button.setEnabled(True)
                        return
        event.ignore()

    def dragLeaveEvent(self, event):
        self._hide_drag_overlay()

    def set_language(self, lang_name):
        lang_file = LANGUAGES.get(lang_name, "fr_FR.json")
        self.translations = load_translation(lang_file)
        self.settings["ui"]["language"] = lang_name
        save_settings(self.settings)

    def t(self, key):
        return self.translations.get(key, key)

    def show_first_run_popup(self):
        message_path = os.path.join(SETTINGS_APP_DIR, "first_run_message.txt")
        msg = "Welcome!\n\nFirst run message file not found."
        if os.path.exists(message_path):
            with open(message_path, "r", encoding="utf-8") as f:
                msg = f.read()
        QtWidgets.QMessageBox.information(self, "First Launch", msg)

    def initUI(self):
        # --- INITIALISATION DU LAYOUT ET CENTRAL WIDGET EN PREMIER ---
        self.setWindowTitle(self.t("app_title"))
        width = self.settings["ui"].get("window_width", 530)
        height = self.settings["ui"].get("window_height", 700)
        self.setFixedSize(width, height)
        self.create_menu()
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QtWidgets.QVBoxLayout(central_widget)

        # --- WIDGETS COMMUNS ---
        self.recorder = AudioRecorder()
        self.record_button = self.create_button(self.t("btn_record"), self.start_recording)
        self.stop_button = self.create_button(self.t("btn_stop"), self.stop_recording, enabled=False)
        self.import_button = self.create_button(self.t("btn_import") if self.t("btn_import") != "btn_import" else self.t("menu_file"), self.import_audio)

        self.clear_temp_button = self.create_button(self.t("btn_clear_temp") if self.t("btn_clear_temp") != "btn_clear_temp" else "Clear Temp Folder", self.clear_temp_folder)
        # --- COMBO MODE (online/offline) ---
        global WHISPER_MODE_REVERSE_MAP
        WHISPER_MODE_REVERSE_MAP = {
            self.t(v) if self.t(v) != v else v: k for k, v in WHISPER_MODE_MAP.items()
        }
        self.whisper_mode_combo = self.create_combo_box([
            self.t(WHISPER_MODE_MAP["online"]) if self.t(WHISPER_MODE_MAP["online"]) != WHISPER_MODE_MAP["online"] else "Whisper Online",
            self.t(WHISPER_MODE_MAP["offline"]) if self.t(WHISPER_MODE_MAP["offline"]) != WHISPER_MODE_MAP["offline"] else "Whisper Offline"
        ], default=self._get_mode_combo_default())
        self.whisper_mode_combo.currentTextChanged.connect(self.switch_whisper_mode)

        # Ajout explicite des boutons communs au layout
        self.layout.addWidget(self.record_button)
        self.layout.addWidget(self.stop_button)
        self.layout.addWidget(self.import_button)
        self.layout.addWidget(self.clear_temp_button)

        # Ajout du combo Whisper mode (online/offline) juste après les boutons communs
        self.layout.addWidget(self.whisper_mode_combo)

        # --- WIDGETS OFFLINE ---
        self.language_label = self.create_label(self.t("label_language"))
        self.layout.addWidget(self.language_label)
        self.language_combo = self.create_combo_box([
            self.t("combo_detect_language") if self.t("combo_detect_language") != "combo_detect_language" else "Detect Language Automatically",
            self.t("combo_french") if self.t("combo_french") != "combo_french" else "French",
            self.t("combo_english") if self.t("combo_english") != "combo_english" else "English",
            self.t("combo_spanish") if self.t("combo_spanish") != "combo_spanish" else "Spanish",
            self.t("combo_german") if self.t("combo_german") != "combo_german" else "German",
            self.t("combo_chinese") if self.t("combo_chinese") != "combo_chinese" else "Chinese",
            self.t("combo_japanese") if self.t("combo_japanese") != "combo_japanese" else "Japanese",
            self.t("combo_russian") if self.t("combo_russian") != "combo_russian" else "Russian",
            self.t("combo_portuguese") if self.t("combo_portuguese") != "combo_portuguese" else "Portuguese",
            self.t("combo_italian") if self.t("combo_italian") != "combo_italian" else "Italian",
            self.t("combo_korean") if self.t("combo_korean") != "combo_korean" else "Korean"
        ])
        self.language_combo.currentTextChanged.connect(self.on_language_changed)
        self.layout.addWidget(self.language_combo)
        self.model_label = self.create_label(self.t("label_model") if self.t("label_model") != "label_model" else "Choose Whisper Model:")
        self.layout.addWidget(self.model_label)
        self.model_combo = self.create_combo_box([
            self.t("combo_turbo") if self.t("combo_turbo") != "combo_turbo" else "Turbo",
            self.t("combo_tiny") if self.t("combo_tiny") != "combo_tiny" else "Tiny",
            self.t("combo_base") if self.t("combo_base") != "combo_base" else "Base",
            self.t("combo_small") if self.t("combo_small") != "combo_small" else "Small",
            self.t("combo_medium") if self.t("combo_medium") != "combo_medium" else "Medium",
            self.t("combo_large") if self.t("combo_large") != "combo_large" else "Large"
        ], default="Turbo")
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        self.layout.addWidget(self.model_combo)

        # --- WIDGETS COMMUNS ONLINE/OFFLINE : CHOIX DU FICHIER ---
        self.file_choice_label = QtWidgets.QLabel(self.t("label_file_choice") if self.t("label_file_choice") != "label_file_choice" else "Choose File to Transcribe:")
        self.file_choice_label.setFont(QtGui.QFont("Arial", 12))
        self.file_choice_combo = QtWidgets.QComboBox()
        self.file_choice_combo.setFont(QtGui.QFont("Arial", 12))
        self.file_choice_combo.addItems([
            self.t("combo_last_recorded") if self.t("combo_last_recorded") != "combo_last_recorded" else "Last Recorded",
            self.t("combo_imported") if self.t("combo_imported") != "combo_imported" else "Imported"
        ])

        # --- WIDGETS OFFLINE (suite) ---
        self.delete_temp_audio_checkbox = self.create_check_box(self.t("checkbox_delete_temp") if self.t("checkbox_delete_temp") != "checkbox_delete_temp" else "Temporary audio (will be deleted after transcription)", checked=True)
        self.delete_temp_audio_checkbox.stateChanged.connect(lambda state: self.on_temp_audio_changed(self.delete_temp_audio_checkbox.isChecked()))
        self.open_folder_checkbox_offline = self.create_check_box(self.t("checkbox_open_folder") if self.t("checkbox_open_folder") != "checkbox_open_folder" else "Open transcription folder after completion", checked=self.settings["ui"].get("open_transcription_folder", True))
        self.open_folder_checkbox_offline.stateChanged.connect(lambda _: self.on_open_folder_changed(self.open_folder_checkbox_offline.isChecked()))
        self.transcription_button = QtWidgets.QPushButton(self.t("btn_transcribe"))
        self.transcription_button.setFont(QtGui.QFont("Arial", 12))
        self.transcription_button.clicked.connect(self.start_offline_transcription)
        self.transcription_button.setEnabled(False)

        # --- WIDGETS ONLINE ---
        self.api_key_label = QtWidgets.QLabel(self.t("label_api_key") if self.t("label_api_key") != "label_api_key" else "OpenAI API Key:")
        self.api_key_label.setFont(QtGui.QFont("Arial", 12))
        api_key_layout = QtWidgets.QHBoxLayout()
        self.api_key_input = QtWidgets.QLineEdit()
        self.api_key_input.setFont(QtGui.QFont("Arial", 12))
        self.api_key_input.setEchoMode(QtWidgets.QLineEdit.Password)
        api_key_layout.addWidget(self.api_key_input)
        self.api_key_eye_button = QtWidgets.QPushButton()
        self.api_key_eye_button.setCheckable(True)
        eye_icon = QtGui.QIcon.fromTheme("view-password-show")
        eye_off_icon = QtGui.QIcon.fromTheme("view-password-hide")
        if not eye_icon.isNull() and not eye_off_icon.isNull():
            self.api_key_eye_button.setIcon(eye_icon)
            self.api_key_eye_button.setIconSize(QtCore.QSize(20, 20))
        else:
            self.api_key_eye_button.setText("👁")
        self.api_key_eye_button.setToolTip(self.t("mask_unmask_api_key") if self.t("mask_unmask_api_key") != "mask_unmask_api_key" else "Show/Hide API Key")
        self.api_key_eye_button.clicked.connect(self.toggle_api_key_visibility)
        api_key_layout.addWidget(self.api_key_eye_button)

        self.online_model_label = QtWidgets.QLabel(self.t("label_online_model") if self.t("label_online_model") != "label_online_model" else "Choose Online Model:")
        self.online_model_label.setFont(QtGui.QFont("Arial", 12))
        self.online_model_combo = QtWidgets.QComboBox()
        self.online_model_combo.setFont(QtGui.QFont("Arial", 12))
        self.online_model_combo.addItems([
            self.t("combo_whisper1") if self.t("combo_whisper1") != "combo_whisper1" else "whisper-1",
            self.t("combo_whisper2") if self.t("combo_whisper2") != "combo_whisper2" else "whisper-2"
        ])
        self.online_model_combo.setCurrentText("whisper-1")
        self.online_model_combo.currentTextChanged.connect(self.on_online_model_changed)

        self.online_temp_audio_checkbox = self.create_check_box(self.t("checkbox_online_temp") if self.t("checkbox_online_temp") != "checkbox_online_temp" else "Temporary audio (will be deleted after online transcription)", checked=True)
        self.online_temp_audio_checkbox.stateChanged.connect(lambda state: self.on_online_temp_audio_changed(self.online_temp_audio_checkbox.isChecked()))
        self.open_folder_checkbox_online = self.create_check_box(self.t("checkbox_open_folder") if self.t("checkbox_open_folder") != "checkbox_open_folder" else "Open transcription folder after completion", checked=self.settings["ui"].get("open_transcription_folder", True))
        self.open_folder_checkbox_online.stateChanged.connect(lambda _: self.on_open_folder_changed(self.open_folder_checkbox_online.isChecked()))
        self.online_transcription_button = QtWidgets.QPushButton(self.t("btn_transcribe"))
        self.online_transcription_button.setFont(QtGui.QFont("Arial", 12))
        self.online_transcription_button.clicked.connect(self.start_online_transcription)
        self.online_transcription_button.setEnabled(False)

        # --- AJOUT DES WIDGETS AU LAYOUT ---
        # Widgets communs (déjà ajoutés par les helpers create_button/create_label/create_combo_box)

        # Widgets offline (ordre logique)
        self.layout.addWidget(self.language_label)
        self.layout.addWidget(self.language_combo)
        self.layout.addWidget(self.model_label)
        self.layout.addWidget(self.model_combo)
        # Ajout du choix de fichier juste après le modèle (offline)
        self.layout.addWidget(self.file_choice_label)
        self.layout.addWidget(self.file_choice_combo)
        self.layout.addWidget(self.delete_temp_audio_checkbox)
        self.layout.addWidget(self.open_folder_checkbox_offline)
        self.layout.addWidget(self.transcription_button)

        # Widgets online (ordre logique)
        self.layout.addWidget(self.api_key_label)
        self.layout.addLayout(api_key_layout)
        self.layout.addWidget(self.online_model_label)
        self.layout.addWidget(self.online_model_combo)
        # Ajout du choix de fichier juste après le modèle (online)
        # (Pas de nouvel ajout, même widgets que offline, déjà dans le layout)
        self.layout.addWidget(self.online_temp_audio_checkbox)
        self.layout.addWidget(self.open_folder_checkbox_online)
        self.layout.addWidget(self.online_transcription_button)

        # Masquer tous les widgets online par défaut (affichés par switch_whisper_mode)
        for w in [self.api_key_label, self.api_key_input, self.api_key_eye_button, self.online_model_label, self.online_model_combo, self.file_choice_label, self.file_choice_combo, self.online_transcription_button, self.online_temp_audio_checkbox, self.open_folder_checkbox_online]:
            w.hide() if hasattr(w, 'hide') else None

        # --- Connexions pour l'activation dynamique du bouton online ---
        self.api_key_input.textChanged.connect(self.update_online_transcribe_button_state)
        self.file_choice_combo.currentTextChanged.connect(self.update_online_transcribe_button_state)
        # Appel initial pour l'état correct au démarrage
        self.update_online_transcribe_button_state()

        # Status label (centré au milieu du layout principal)
        self.status_label = QtWidgets.QLabel(self.t("status_ready") if self.t("status_ready") != "status_ready" else "Status: Ready")
        self.status_label.setFont(QtGui.QFont("Arial", 16, QtGui.QFont.Bold))
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.addWidget(self.status_label)
        # Size label (tout en bas)
        self.size_label = QtWidgets.QLabel(f"{self.t('label_window_size') if self.t('label_window_size') != 'label_window_size' else 'Window Size:'} {self.width()} x {self.height()}")
        self.size_label.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.addWidget(self.size_label)

        # Always show status as ready at the end of UI init
        self.update_status(self.t("status_ready") if self.t("status_ready") != "status_ready" else "Status: Ready", "blue")

        # Appliquer le mode Whisper selon les paramètres utilisateur
        mode = self.settings["ui"].get("whisper_mode", "offline").strip().lower()
        label = self.t(WHISPER_MODE_MAP.get(mode, "combo_whisper_offline"))
        if label == WHISPER_MODE_MAP.get(mode, "combo_whisper_offline"):
            label = "Whisper Online" if mode == "online" else "Whisper Offline"
        self.switch_whisper_mode(label)

    def on_export_format_changed(self, value):
        pass  # Suppression du menu déroulant : plus rien à faire ici

    def _set_ui_defaults(self):
        # Set mode by internal value
        mode = self.settings["ui"].get("whisper_mode", "offline").strip().lower()
        label = self.t(WHISPER_MODE_MAP.get(mode, "combo_whisper_offline"))
        if label == WHISPER_MODE_MAP.get(mode, "combo_whisper_offline"):
            label = "Whisper Online" if mode == "online" else "Whisper Offline"
        self.whisper_mode_combo.setCurrentText(label)
        self.language_combo.setCurrentText(self.settings["ui"].get("choose_language", "Detect Language Automatically"))
        self.model_combo.setCurrentText(self.settings["ui"].get("whisper_model", "Turbo"))
        self.delete_temp_audio_checkbox.setChecked(self.settings["ui"].get("temp_audio", True))
        self.online_model_combo.setCurrentText(self.settings["ui"].get("online_model", "whisper-1"))
        self.online_temp_audio_checkbox.setChecked(self.settings["ui"].get("online_temp_audio", True))
        self.open_folder_checkbox_offline.setChecked(self.settings["ui"].get("open_transcription_folder", True))
        self.open_folder_checkbox_online.setChecked(self.settings["ui"].get("open_transcription_folder", True))

    def _get_mode_combo_default(self):
        mode = self.settings["ui"].get("whisper_mode", "offline").strip().lower()
        label = self.t(WHISPER_MODE_MAP.get(mode, "combo_whisper_offline"))
        if label == WHISPER_MODE_MAP.get(mode, "combo_whisper_offline"):
            label = "Whisper Online" if mode == "online" else "Whisper Offline"
        return label


    def create_button(self, text, callback, enabled=True):
        button = QtWidgets.QPushButton(text)
        button.setFont(QtGui.QFont("Arial", 12))
        button.clicked.connect(callback)
        button.setEnabled(enabled)
        return button

    def create_label(self, text, font_size=12, bold=False, alignment=None):
        label = QtWidgets.QLabel(text)
        font = QtGui.QFont("Arial", font_size)
        if bold:
            font.setBold(True)
        label.setFont(font)
        if alignment:
            label.setAlignment(alignment)
        return label

    def create_combo_box(self, items, default=None):
        combo_box = QtWidgets.QComboBox()
        combo_box.setFont(QtGui.QFont("Arial", 12))
        combo_box.addItems(items)
        if default:
            combo_box.setCurrentText(default)
        return combo_box

    def create_check_box(self, text, checked=False):
        check_box = QtWidgets.QCheckBox(text)
        check_box.setChecked(checked)
        return check_box

    def create_menu(self):
        menubar = self.menuBar()
        menubar.clear()
        # --- Paramètres ---
        settings_menu = menubar.addMenu(self.t('label_settings') if self.t('label_settings') != 'label_settings' else 'Settings')
        # Thème
        theme_menu = settings_menu.addMenu(self.t('label_theme') if self.t('label_theme') != 'label_theme' else 'Theme')
        self.light_theme_action = QtWidgets.QAction(self.t('theme_light') if self.t('theme_light') != 'theme_light' else 'Light Mode', self)
        self.light_theme_action.setCheckable(True)
        self.dark_theme_action = QtWidgets.QAction(self.t('theme_dark') if self.t('theme_dark') != 'theme_dark' else 'Dark Mode', self)
        self.dark_theme_action.setCheckable(True)
        theme_group = QtWidgets.QActionGroup(self)
        theme_group.addAction(self.light_theme_action)
        theme_group.addAction(self.dark_theme_action)
        theme_menu.addAction(self.light_theme_action)
        theme_menu.addAction(self.dark_theme_action)
        self.light_theme_action.triggered.connect(lambda: self.set_theme('light'))
        self.dark_theme_action.triggered.connect(lambda: self.set_theme('dark'))
        if self.settings["ui"].get("theme", "light") == "dark":
            self.dark_theme_action.setChecked(True)
        else:
            self.light_theme_action.setChecked(True)
        # Langue
        lang_menu = settings_menu.addMenu(self.t('label_language') if self.t('label_language') != 'label_language' else 'Language')
        self.lang_actions = {}
        lang_group = QtWidgets.QActionGroup(self)
        for lang_name in LANGUAGES:
            action = QtWidgets.QAction(lang_name, self)
            action.setCheckable(True)
            if self.settings["ui"].get("language", "Français (Europe)") == lang_name:
                action.setChecked(True)
            action.triggered.connect(lambda checked, l=lang_name: self.change_language(l))
            lang_group.addAction(action)
            lang_menu.addAction(action)
            self.lang_actions[lang_name] = action
        # Taille de fenêtre
        size_menu = settings_menu.addMenu(self.t('label_window_size') if self.t('label_window_size') != 'label_window_size' else 'Window Size:')
        self.width_box = QtWidgets.QSpinBox()
        self.width_box.setRange(300, 1920)
        self.width_box.setValue(self.settings["ui"].get("window_width", 530))
        self.height_box = QtWidgets.QSpinBox()
        self.height_box.setRange(300, 1920)
        self.height_box.setValue(self.settings["ui"].get("window_height", 700))
        width_action = QtWidgets.QWidgetAction(self)
        width_action.setDefaultWidget(self.width_box)
        height_action = QtWidgets.QWidgetAction(self)
        height_action.setDefaultWidget(self.height_box)
        size_menu.addAction(width_action)
        size_menu.addAction(height_action)
        apply_action = QtWidgets.QAction(self.t('btn_apply_size') if self.t('btn_apply_size') != 'btn_apply_size' else 'Apply', self)
        apply_action.triggered.connect(self.apply_window_size)
        size_menu.addAction(apply_action)
        # Réinitialisation des paramètres
        reset_action = QtWidgets.QAction(self.t('btn_reset_settings') if self.t('btn_reset_settings') != 'btn_reset_settings' else 'Reset to Default', self)
        reset_action.triggered.connect(self.reset_settings_to_default)
        settings_menu.addAction(reset_action)
        # Gestion de la clé API
        api_key_action = QtWidgets.QAction(self.t('menu_manage_api_key') if self.t('menu_manage_api_key') != 'menu_manage_api_key' else 'Manage OpenAI API Key', self)
        api_key_action.triggered.connect(self.show_api_key_dialog)
        settings_menu.addAction(api_key_action)
        # --- Crédits ---
        credits_menu = menubar.addMenu(self.t('menu_credits') if self.t('menu_credits') != 'menu_credits' else 'Credits')
        author_action = QtWidgets.QAction(self.t('menu_author') if self.t('menu_author') != 'menu_author' else 'Author', self)
        author_action.triggered.connect(self.show_author_info)
        credits_menu.addAction(author_action)
        license_action = QtWidgets.QAction(self.t('menu_license') if self.t('menu_license') != 'menu_license' else 'License', self)
        license_action.triggered.connect(self.show_license_info)
        credits_menu.addAction(license_action)

    def refresh_ui_texts(self):
        self.setWindowTitle(self.t("app_title"))
        self.record_button.setText(self.t("btn_record"))
        self.stop_button.setText(self.t("btn_stop"))
        self.import_button.setText(self.t("btn_import") if self.t("btn_import") != "btn_import" else self.t("menu_file"))
        self.clear_temp_button.setText(self.t("btn_clear_temp") if self.t("btn_clear_temp") != "btn_clear_temp" else "Clear Temp Folder")
        self.language_label.setText(self.t("label_language"))
        self.model_label.setText(self.t("label_model") if self.t("label_model") != "label_model" else "Choose Whisper Model:")
        self.file_choice_label.setText(self.t("label_file_choice") if self.t("label_file_choice") != "label_file_choice" else "Choose File to Transcribe:")
        self.delete_temp_audio_checkbox.setText(self.t("checkbox_delete_temp") if self.t("checkbox_delete_temp") != "checkbox_delete_temp" else "Temporary audio (will be deleted after transcription)")
        self.open_folder_checkbox_offline.setText(self.t("checkbox_open_folder") if self.t("checkbox_open_folder") != "checkbox_open_folder" else "Open transcription folder after completion")
        self.transcription_button.setText(self.t("btn_transcribe"))
        # Online widgets: check existence before updating
        if hasattr(self, 'api_key_label'):
            self.api_key_label.setText(self.t("label_api_key") if self.t("label_api_key") != "label_api_key" else "OpenAI API Key:")
        if hasattr(self, 'online_model_label'):
            self.online_model_label.setText(self.t("label_online_model") if self.t("label_online_model") != "label_online_model" else "Choose Online Model:")
        if hasattr(self, 'online_temp_audio_checkbox'):
            self.online_temp_audio_checkbox.setText(self.t("checkbox_online_temp") if self.t("checkbox_online_temp") != "checkbox_online_temp" else "Temporary audio (will be deleted after online transcription)")
        if hasattr(self, 'open_folder_checkbox_online'):
            self.open_folder_checkbox_online.setText(self.t("checkbox_open_folder") if self.t("checkbox_open_folder") != "checkbox_open_folder" else "Open transcription folder after completion")
        if hasattr(self, 'online_transcription_button'):
            self.online_transcription_button.setText(self.t("btn_transcribe"))
        if hasattr(self, 'status_label'):
            self.status_label.setText(self.t("status_ready") if self.t("status_ready") != "status_ready" else "Status: Ready")
        if hasattr(self, 'size_label'):
            self.size_label.setText(f"{self.t('label_window_size') if self.t('label_window_size') != 'label_window_size' else 'Window Size:'} {self.width()} x {self.height()}")
        # ComboBox items
        self.whisper_mode_combo.setItemText(0, self.t(WHISPER_MODE_MAP["online"]) if self.t(WHISPER_MODE_MAP["online"]) != WHISPER_MODE_MAP["online"] else "Whisper Online")
        self.whisper_mode_combo.setItemText(1, self.t(WHISPER_MODE_MAP["offline"]) if self.t(WHISPER_MODE_MAP["offline"]) != WHISPER_MODE_MAP["offline"] else "Whisper Offline")
        # Update combo selection to match internal value
        mode = self.settings["ui"].get("whisper_mode", "offline").strip().lower()
        label = self.t(WHISPER_MODE_MAP.get(mode, "combo_whisper_offline"))
        if label == WHISPER_MODE_MAP.get(mode, "combo_whisper_offline"):
            label = "Whisper Online" if mode == "online" else "Whisper Offline"
        self.whisper_mode_combo.setCurrentText(label)
        self.language_combo.clear()
        self.language_combo.addItems([
            self.t("combo_detect_language") if self.t("combo_detect_language") != "combo_detect_language" else "Detect Language Automatically",
            self.t("combo_french") if self.t("combo_french") != "combo_french" else "French",
            self.t("combo_english") if self.t("combo_english") != "combo_english" else "English",
            self.t("combo_spanish") if self.t("combo_spanish") != "combo_spanish" else "Spanish",
            self.t("combo_german") if self.t("combo_german") != "combo_german" else "German",
            self.t("combo_chinese") if self.t("combo_chinese") != "combo_chinese" else "Chinese",
            self.t("combo_japanese") if self.t("combo_japanese") != "combo_japanese" else "Japanese",
            self.t("combo_russian") if self.t("combo_russian") != "combo_russian" else "Russian",
            self.t("combo_portuguese") if self.t("combo_portuguese") != "combo_portuguese" else "Portuguese",
            self.t("combo_italian") if self.t("combo_italian") != "combo_italian" else "Italian",
            self.t("combo_korean") if self.t("combo_korean") != "combo_korean" else "Korean"
        ])
        self.model_combo.clear()
        self.model_combo.addItems([
            self.t("combo_turbo") if self.t("combo_turbo") != "combo_turbo" else "Turbo",
            self.t("combo_tiny") if self.t("combo_tiny") != "combo_tiny" else "Tiny",
            self.t("combo_base") if self.t("combo_base") != "combo_base" else "Base",
            self.t("combo_small") if self.t("combo_small") != "combo_small" else "Small",
            self.t("combo_medium") if self.t("combo_medium") != "combo_medium" else "Medium",
            self.t("combo_large") if self.t("combo_large") != "combo_large" else "Large"
        ])
        self.file_choice_combo.clear()
        self.file_choice_combo.addItems([
            self.t("combo_last_recorded") if self.t("combo_last_recorded") != "combo_last_recorded" else "Last Recorded",
            self.t("combo_imported") if self.t("combo_imported") != "combo_imported" else "Imported"
        ])
        if hasattr(self, 'online_model_combo'):
            self.online_model_combo.clear()
            self.online_model_combo.addItems([
                self.t("combo_whisper1") if self.t("combo_whisper1") != "combo_whisper1" else "whisper-1",
                self.t("combo_whisper2") if self.t("combo_whisper2") != "combo_whisper2" else "whisper-2"
            ])
        # Rafraîchir les menus
        self.menuBar().clear()
        self.create_menu()

    def change_language(self, lang_name):
        self.set_language(lang_name)
        self.refresh_ui_texts()

    def restart_app(self):
        import sys, os
        os.execl(sys.executable, sys.executable, *sys.argv)

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
        # Always log status updates and errors
        self.status_label.setText(self.t(text) if self.t(text) != text else text)
        self.status_label.setStyleSheet(f"color: {color};")
        if color.lower() == "red" or text.lower().startswith("erreur") or text.lower().startswith("error"):
            logging.error(f"Status error: {text} (color: {color})")
        else:
            logging.info(f"Status updated: {text} (color: {color})")

    def reset_status(self):
        self.update_status(self.t("status_ready") if self.t("status_ready") != "status_ready" else "Status: Ready", "blue")
        self.record_button.setEnabled(True)

    def toggle_recording_buttons(self, recording):
        self.record_button.setEnabled(not recording)
        self.stop_button.setEnabled(recording)
        self.transcription_button.setEnabled(not recording)

    def resizeEvent(self, event):
        if hasattr(self, 'size_label') and self.size_label:
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

    def switch_whisper_mode(self, mode_label):
        # Map translated label to internal value
        mode = WHISPER_MODE_REVERSE_MAP.get(mode_label, None)
        if mode is None:
            # fallback: try English
            if mode_label.lower() == "whisper online":
                mode = "online"
            else:
                mode = "offline"
        offline_widgets = [
            self.language_label, self.language_combo, self.model_label, self.model_combo,
            self.file_choice_label, self.file_choice_combo, self.delete_temp_audio_checkbox, self.open_folder_checkbox_offline, self.transcription_button
        ]
        # Only include online widgets that exist
        online_widgets = []
        for attr in ["api_key_label", "api_key_input", "api_key_eye_button", "online_model_label", "online_model_combo", "online_temp_audio_checkbox", "open_folder_checkbox_online", "online_transcription_button"]:
            if hasattr(self, attr):
                online_widgets.append(getattr(self, attr))
        if mode == "online":
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
        self.settings["ui"]["whisper_mode"] = mode
        save_settings(self.settings)
        # Après avoir changé de mode, vérifie si un fichier est dispo
        if not self.last_recorded_file_path and not self.imported_file_path:
            self.transcription_button.setEnabled(False)
        else:
            self.transcription_button.setEnabled(True)

    def start_recording(self):
        # Suppression de la visualisation
        # self.recorder.set_visualization_callback(None)
        # self.waveform_window = WaveformWindow(self)
        # self.recorder.set_visualization_callback(self.waveform_window.update_waveform)
        self.recorder.start_recording()  # Logging is handled in AudioRecorder
        self.toggle_recording_buttons(recording=True)
        self.update_status("Status: Recording...", "orange")

    def stop_recording(self):
        self.recorder.stop_recording()
        self.is_recording = False
        # Suppression de la fermeture de la fenêtre de visualisation
        # if hasattr(self, 'waveform_window') and self.waveform_window:
        #     self.waveform_window.close()
        #     self.waveform_window = None
        if self.delete_temp_audio_checkbox.isChecked():
            audio_save_path = os.path.join("Temp", datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".wav")
        else:
            audio_save_path = os.path.join("Records", "Audio", datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".wav")
        self.recorder.save_recording(audio_save_path)
        self.last_recorded_file_path = os.path.abspath(audio_save_path)
        logging.info(f"Audio enregistré sauvegardé dans : {self.last_recorded_file_path}")
        if not os.path.exists(self.last_recorded_file_path):
            logging.error(f"Fichier d'enregistrement non trouvé : {self.last_recorded_file_path}")
        self.update_status("Status: Recording completed", "orange")
        self.toggle_recording_buttons(recording=False)
        self.transcription_button.setEnabled(True)

    def get_selected_audio_file(self):
        file_choice = self.file_choice_combo.currentText().strip()
        file_choice_en = self.get_file_choice_english(file_choice)
        logging.info(f"ComboBox file_choice value: {file_choice} (en: {file_choice_en})")
        file_choice = file_choice.lower()
        last_keywords = ["last", "dernier"]
        if any(k in file_choice for k in last_keywords):
            # Recherche dynamique du dernier fichier enregistré (Temp/ ou Records/Audio/)
            candidates = []
            for folder in [os.path.join("Records", "Audio"), "Temp"]:
                if os.path.exists(folder):
                    wavs = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith('.wav')]
                    candidates.extend(wavs)
            if not candidates:
                logging.error("Aucun fichier d'enregistrement trouvé.")
                return None
            # Trie par date de modification décroissante
            candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            last_path = candidates[0]
            if os.path.exists(last_path):
                self.last_recorded_file_path = last_path
                return last_path
            else:
                logging.error(f"Last recorded file does not exist: {last_path}")
                return None
        elif "import" in file_choice and self.imported_file_path:
            if os.path.exists(self.imported_file_path):
                return self.imported_file_path
            else:
                logging.error(f"Imported file does not exist: {self.imported_file_path}")
                return None
        return None

    def extract_audio_from_video(self, video_path):
        """
        Extract audio from a video file to a temporary WAV file for transcription.
        Returns the path to the extracted audio file, or None if extraction failed.
        """
        audio_output = os.path.join("Temp", "extracted_audio.wav")
        try:
            result = subprocess.run([
                "ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_output
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if os.path.exists(audio_output):
                return audio_output
        except Exception as e:
            logging.error(f"Failed to extract audio from video: {video_path} | {e}")
        return None

    def import_audio(self):
        options = QtWidgets.QFileDialog.Options()
        file_filter = self.t("dialog_import_filter") if self.t("dialog_import_filter") != "dialog_import_filter" else "Audio/Video Files (*.wav *.mp3 *.flac *.m4a *.aac *.ogg *.wma *.mp4 *.avi *.mov *.mkv *.webm);;All Files (*)"
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, self.t("dialog_import_title") if self.t("dialog_import_title") != "dialog_import_title" else "Import Audio/Video File", "", file_filter, options=options)
        if file_path:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in self.VIDEO_EXTENSIONS:
                audio_path = self.extract_audio_from_video(file_path)
                if audio_path:
                    self.imported_file_path = audio_path
                    self._is_temp_extracted_audio = True
                    self.update_status(self.t("status_audio_imported") if self.t("status_audio_imported") != "status_audio_imported" else "Status: Audio extracted from video and imported", "orange")
                    logging.info(f"Imported video file, extracted audio: {file_path} -> {audio_path}")
                else:
                    QtWidgets.QMessageBox.warning(self, "Import Error", "Failed to extract audio from video file.")
                    return
            else:
                self.imported_file_path = file_path
                self._is_temp_extracted_audio = False
                self.update_status(self.t("status_audio_imported") if self.t("status_audio_imported") != "status_audio_imported" else "Status: Audio imported", "orange")
                logging.info(f"Imported audio file: {file_path}")
            self.transcription_button.setEnabled(True)
            self.update_online_transcribe_button_state()

    def get_unique_transcription_path(self):
        base_dir = os.path.join("Records", "Transcription")
        base_name = "transcription"
        ext = ".txt"
        i = 1
        while True:
            path = os.path.join(base_dir, f"{base_name}({i}){ext}")
            if not os.path.exists(path):
                return path
            i += 1

    def start_offline_transcription(self):
        if getattr(self, 'is_recording', False):
            logging.warning("Attempted transcription while recording.")
            self.update_status("Status: Cannot transcribe while recording", "red")
            return
        if getattr(self, 'is_transcribing', False):
            logging.warning("Transcription already in progress.")
            self.update_status("Status: Transcription already in progress", "red")
            return
        file_path = self.get_selected_audio_file()
        logging.info(f"Chemin utilisé pour la transcription : {file_path}")
        if not file_path:
            QtWidgets.QMessageBox.warning(self, self.t("btn_transcribe"), self.t("msg_no_audio_file") if self.t("msg_no_audio_file") != "msg_no_audio_file" else "Aucun fichier audio valide trouvé pour la transcription.\nVérifiez qu'un enregistrement existe dans Records/Audio ou Temp.")
            self.update_status("Status: No file selected for transcription", "red")
            self.transcription_button.setEnabled(False)
            self.update_online_transcribe_button_state()
            return
        self.is_transcribing = True
        self.transcription_button.setEnabled(False)
        self.update_online_transcribe_button_state()
        self.update_status("Status: Transcribing...", "purple")
        # Export format UI supprimé : toujours TXT
        export_format = "TXT"
        base_path = self.get_unique_transcription_path()
        save_path = base_path
        language = self.language_combo.currentText()
        language = self.normalize_language(language)
        model = self.model_combo.currentText()
        # Determine if temp audio should be deleted after transcription
        delete_after_transcription = False
        file_choice = self.file_choice_combo.currentText().strip()
        file_choice_en = self.get_file_choice_english(file_choice)
        if (file_choice_en.lower() == "last recorded" or file_choice_en.lower() == "dernier enregistrement") and self.delete_temp_audio_checkbox.isChecked():
            delete_after_transcription = True
        self.open_folder_after = self.open_folder_checkbox_offline.isChecked()
        logging.info(f"Starting offline transcription: file={file_path}, save_path={save_path}, language={language}, model={model}, delete_after={delete_after_transcription}, export_format={export_format}")
        self.transcription_thread = TranscriptionThread(self.transcriber, file_path, save_path, language, model, delete_after_transcription, export_format)
        self.transcription_thread.transcription_completed.connect(self.on_transcription_completed)
        self.transcription_thread.start()

    def on_transcription_completed(self, status, color):
        logging.info(f"Offline transcription completed. Status: {status}, Color: {color}")
        self.update_status(status, color)
        self.is_transcribing = False
        self.transcription_button.setEnabled(True)
        # Clean up extracted audio if needed
        if getattr(self, '_is_temp_extracted_audio', False):
            try:
                if self.imported_file_path and os.path.exists(self.imported_file_path):
                    os.remove(self.imported_file_path)
                    logging.info(f"Deleted temporary extracted audio: {self.imported_file_path}")
            except Exception as e:
                logging.error(f"Failed to delete temporary extracted audio: {e}")
            self._is_temp_extracted_audio = False
        if getattr(self, 'open_folder_after', False) and color == "green":
            folder = os.path.abspath(os.path.join("Records", "Transcription"))
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(folder))
            logging.info(f"Opened transcription folder: {folder}")
        QtCore.QTimer.singleShot(2000, lambda: self.update_status(self.t("status_ready") if self.t("status_ready") != "status_ready" else "Status: Ready", "blue"))

    def start_online_transcription(self):
        api_key = self.api_key_input.text().strip()
        if not api_key:
            # Try to load from keyring
            api_key = keyring.get_password(SERVICE_NAME, "user")
            if api_key:
                self.api_key_input.setText(api_key)
            else:
                logging.error("No OpenAI API key provided.")
                self.update_status("Status: Please enter your OpenAI API key", "red")
                return
        file_path = self.get_selected_audio_file()
        if not file_path:
            QtWidgets.QMessageBox.warning(self, self.t("btn_transcribe"), self.t("msg_no_audio_file") if self.t("msg_no_audio_file") != "msg_no_audio_file" else "No valid audio file selected for transcription.")
            self.update_status("Status: No file selected for transcription", "red")
            return
        language = self.language_combo.currentText()
        language = self.normalize_language(language)
        model = self.online_model_combo.currentText()
        delete_temp = self.online_temp_audio_checkbox.isChecked()
        # Export format UI supprimé : toujours TXT
        export_format = "TXT"
        base_path = os.path.join("Records", "Transcription", datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_online.txt")
        save_path = base_path
        self.update_status("Status: Online transcription in progress...", "purple")
        self.open_folder_after_online = self.open_folder_checkbox_online.isChecked()
        logging.info(f"Starting online transcription: file={file_path}, save_path={save_path}, language={language}, model={model}, delete_temp={delete_temp}, export_format={export_format}")
        self.online_thread = OnlineTranscriptionThread(api_key, file_path, model, delete_temp, save_path, language=language, export_format=export_format)
        self.online_thread.transcription_completed.connect(self.on_online_transcription_completed)
        self.online_transcription_button.setEnabled(False)
        self.online_thread.start()

    def on_online_transcription_completed(self, status, color):
        logging.info(f"Online transcription completed. Status: {status}, Color: {color}")
        self.update_status(status, color)
        self.online_transcription_button.setEnabled(True)
        if getattr(self, 'open_folder_after_online', False):
            folder = os.path.abspath(os.path.join("Records", "Transcription"))
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(folder))
            logging.info(f"Opened transcription folder: {folder}")
        QtCore.QTimer.singleShot(2000, lambda: self.update_status(self.t("status_ready") if self.t("status_ready") != "status_ready" else "Status: Ready", "blue"))

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
    def on_open_folder_changed(self, checked):
        self.settings["ui"]["open_transcription_folder"] = checked
        save_settings(self.settings)
        self.open_folder_checkbox_offline.setChecked(checked)
        self.open_folder_checkbox_online.setChecked(checked)

    def apply_window_size(self):
        width = self.width_box.value()
        height = self.height_box.value()
        self.setFixedSize(width, height)
        self.settings["ui"]["window_width"] = width
        self.settings["ui"]["window_height"] = height
        save_settings(self.settings)

    def reset_settings_to_default(self):
        reply = QtWidgets.QMessageBox.question(
            self,
            self.t('label_settings'),
            self.t('dialog_reset_settings_text') if self.t('dialog_reset_settings_text') != 'dialog_reset_settings_text' else 'Are you sure you want to reset all settings to default?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            default_settings_path = os.path.join(SETTINGS_APP_DIR, "default_settings.json")
            if os.path.exists(default_settings_path):
                with open(default_settings_path, "r", encoding="utf-8") as f:
                    default_settings = json.load(f)
                with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                    json.dump(default_settings, f, indent=2)
                self.settings = default_settings
                self.set_language(self.settings["ui"].get("language", "English (Europe)"))
                self.refresh_ui_texts()
                self.set_theme(self.settings["ui"].get("theme", "light"))
                self.setFixedSize(self.settings["ui"].get("window_width", 530), self.settings["ui"].get("window_height", 700))
                QtWidgets.QMessageBox.information(self, self.t('label_settings'), self.t('msg_settings_reset') if self.t('msg_settings_reset') != 'msg_settings_reset' else 'Settings have been reset to default.')

    def toggle_api_key_visibility(self):
        if self.api_key_input.echoMode() == QtWidgets.QLineEdit.Password:
            self.api_key_input.setEchoMode(QtWidgets.QLineEdit.Normal)
            # Change icon to eye-off if available
            eye_off_icon = QtGui.QIcon.fromTheme("view-password-hide")
            if not eye_off_icon.isNull():
                self.api_key_eye_button.setIcon(eye_off_icon)
            else:
                self.api_key_eye_button.setText("🙈")
        else:
            self.api_key_input.setEchoMode(QtWidgets.QLineEdit.Password)
            eye_icon = QtGui.QIcon.fromTheme("view-password-show")
            if not eye_icon.isNull():
                self.api_key_eye_button.setIcon(eye_icon)
            else:
                self.api_key_eye_button.setText("👁")

    def show_api_key_dialog(self):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(self.t('menu_manage_api_key') if self.t('menu_manage_api_key') != 'menu_manage_api_key' else 'Gérer la clé API OpenAI')
        layout = QtWidgets.QVBoxLayout(dlg)
        label = QtWidgets.QLabel(self.t('label_api_key') if self.t('label_api_key') != 'label_api_key' else 'OpenAI API Key:')
        layout.addWidget(label)
        api_key_layout = QtWidgets.QHBoxLayout()
        api_key_input = QtWidgets.QLineEdit()
        api_key_input.setEchoMode(QtWidgets.QLineEdit.Password)
        # Charger la clé existante si présente
        api_key = keyring.get_password(SERVICE_NAME, "user")
        if api_key:
            api_key_input.setText(api_key)
        api_key_layout.addWidget(api_key_input)
        # Ajout du bouton œil
        api_key_eye_button = QtWidgets.QPushButton()
        api_key_eye_button.setCheckable(True)
        eye_icon = QtGui.QIcon.fromTheme("view-password-show")
        eye_off_icon = QtGui.QIcon.fromTheme("view-password-hide")
        if not eye_icon.isNull() and not eye_off_icon.isNull():
            api_key_eye_button.setIcon(eye_icon)
            api_key_eye_button.setIconSize(QtCore.QSize(20, 20))
        else:
            api_key_eye_button.setText("👁")
        api_key_eye_button.setToolTip(self.t("mask_unmask_api_key") if self.t("mask_unmask_api_key") != "mask_unmask_api_key" else "Show/Hide API Key")
        def toggle_visibility():
            if api_key_input.echoMode() == QtWidgets.QLineEdit.Password:
                api_key_input.setEchoMode(QtWidgets.QLineEdit.Normal)
                if not eye_off_icon.isNull():
                    api_key_eye_button.setIcon(eye_off_icon)
                else:
                    api_key_eye_button.setText("🙈")
            else:
                api_key_input.setEchoMode(QtWidgets.QLineEdit.Password)
                if not eye_icon.isNull():
                    api_key_eye_button.setIcon(eye_icon)
                else:
                    api_key_eye_button.setText("👁")
        api_key_eye_button.clicked.connect(toggle_visibility)
        api_key_layout.addWidget(api_key_eye_button)
        layout.addLayout(api_key_layout)
        btn_layout = QtWidgets.QHBoxLayout()
        save_btn = QtWidgets.QPushButton(self.t('btn_save_api_key') if self.t('btn_save_api_key') != 'btn_save_api_key' else 'Enregistrer')
        delete_btn = QtWidgets.QPushButton(self.t('btn_delete_api_key') if self.t('btn_delete_api_key') != 'btn_delete_api_key' else 'Supprimer')
        close_btn = QtWidgets.QPushButton(self.t('btn_close') if self.t('btn_close') != 'btn_close' else 'Fermer')
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        def save():
            val = api_key_input.text().strip()
            if val:
                keyring.set_password(SERVICE_NAME, "user", val)
                QtWidgets.QMessageBox.information(dlg, self.t("label_api_key"), self.t("msg_api_key_saved") if self.t("msg_api_key_saved") != "msg_api_key_saved" else "API key saved securely.")
            else:
                QtWidgets.QMessageBox.warning(dlg, self.t("label_api_key"), self.t("msg_api_key_empty") if self.t("msg_api_key_empty") != "msg_api_key_empty" else "API key is empty.")
        def delete():
            try:
                keyring.delete_password(SERVICE_NAME, "user")
                api_key_input.clear()
                QtWidgets.QMessageBox.information(dlg, self.t("label_api_key"), self.t("msg_api_key_deleted") if self.t("msg_api_key_deleted") != "msg_api_key_deleted" else "API key deleted from secure storage.")
            except keyring.errors.PasswordDeleteError:
                QtWidgets.QMessageBox.warning(dlg, self.t("label_api_key"), self.t("msg_api_key_not_found") if self.t("msg_api_key_not_found") != "msg_api_key_not_found" else "No API key found in secure storage.")
        save_btn.clicked.connect(save)
        delete_btn.clicked.connect(delete)
        close_btn.clicked.connect(dlg.accept)
        dlg.exec_()

    def clear_temp_folder(self):
        reply = QtWidgets.QMessageBox.question(self, self.t('dialog_clear_temp_title') if self.t('dialog_clear_temp_title') != 'dialog_clear_temp_title' else 'Clear Temp Folder', self.t('dialog_clear_temp_text') if self.t('dialog_clear_temp_text') != 'dialog_clear_temp' else 'Are you sure you want to clear the Temp folder?', QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
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
            self.last_recorded_file_path = None
            self.imported_file_path = None
            self.transcription_button.setEnabled(False)  # Désactive le bouton
            self.update_status(self.t("status_temp_cleared") if self.t("status_temp_cleared") != "status_temp_cleared" else "Status: Temp folder cleared", "green")
            QtCore.QTimer.singleShot(2000, self.reset_status)
        else:
            self.update_status("Status: Temp folder clear cancelled", "orange")
            QtCore.QTimer.singleShot(2000, self.reset_status)
