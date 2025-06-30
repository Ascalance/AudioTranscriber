from PyQt5 import QtWidgets, QtGui, QtCore
import os
import json
import logging
import shutil
import datetime
import warnings
import keyring
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

logging.basicConfig(filename=os.path.join("Logs", 'log.txt'), level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    def __init__(self):
        self.settings = load_settings()
        self.translations = {}
        super().__init__()
        lang_name = self.settings["ui"].get("language") or "English (Europe)"
        self.set_language(lang_name)
        if self.settings.get("first_run", True):
            self.show_first_run_popup()
            self.settings["first_run"] = False
            save_settings(self.settings)
        self.initUI()
        self.set_theme(self.settings["ui"].get("theme", "light"))
        # Load API key from keyring if present
        api_key = keyring.get_password(SERVICE_NAME, "user")
        if api_key:
            self.api_key_input.setText(api_key)

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
        self.setWindowTitle(self.t("app_title"))
        self.setFixedSize(530, 700)
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QtWidgets.QVBoxLayout(central_widget)
        self.recorder = AudioRecorder()
        self.record_button = self.create_button(self.t("btn_record"), self.start_recording)
        self.stop_button = self.create_button(self.t("btn_stop"), self.stop_recording, enabled=False)
        self.import_button = self.create_button(self.t("btn_import") if self.t("btn_import") != "btn_import" else self.t("menu_file"), self.import_audio)
        self.clear_temp_button = self.create_button(self.t("btn_clear_temp") if self.t("btn_clear_temp") != "btn_clear_temp" else "Clear Temp Folder", self.clear_temp_folder)
        # Build reverse map for translated labels
        global WHISPER_MODE_REVERSE_MAP
        WHISPER_MODE_REVERSE_MAP = {
            self.t(v) if self.t(v) != v else v: k for k, v in WHISPER_MODE_MAP.items()
        }
        self.whisper_mode_combo = self.create_combo_box([
            self.t(WHISPER_MODE_MAP["online"]) if self.t(WHISPER_MODE_MAP["online"]) != WHISPER_MODE_MAP["online"] else "Whisper Online",
            self.t(WHISPER_MODE_MAP["offline"]) if self.t(WHISPER_MODE_MAP["offline"]) != WHISPER_MODE_MAP["offline"] else "Whisper Offline"
        ], default=self._get_mode_combo_default())
        self.whisper_mode_combo.currentTextChanged.connect(self.switch_whisper_mode)
        # Offline widgets
        self.language_label = self.create_label(self.t("label_language"))
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
        self.model_label = self.create_label(self.t("label_model") if self.t("label_model") != "label_model" else "Choose Whisper Model:")
        self.model_combo = self.create_combo_box([
            self.t("combo_turbo") if self.t("combo_turbo") != "combo_turbo" else "Turbo",
            self.t("combo_tiny") if self.t("combo_tiny") != "combo_tiny" else "Tiny",
            self.t("combo_base") if self.t("combo_base") != "combo_base" else "Base",
            self.t("combo_small") if self.t("combo_small") != "combo_small" else "Small",
            self.t("combo_medium") if self.t("combo_medium") != "combo_medium" else "Medium",
            self.t("combo_large") if self.t("combo_large") != "combo_large" else "Large"
        ], default="Turbo")
        self.file_choice_label = self.create_label(self.t("label_file_choice") if self.t("label_file_choice") != "label_file_choice" else "Choose File to Transcribe:")
        self.file_choice_combo = self.create_combo_box([
            self.t("combo_last_recorded") if self.t("combo_last_recorded") != "combo_last_recorded" else "Last Recorded",
            self.t("combo_imported") if self.t("combo_imported") != "combo_imported" else "Imported"
        ])
        self.delete_temp_audio_checkbox = self.create_check_box(self.t("checkbox_delete_temp") if self.t("checkbox_delete_temp") != "checkbox_delete_temp" else "Temporary audio (will be deleted after transcription)", checked=True)
        self.layout.addWidget(self.delete_temp_audio_checkbox)
        self.open_folder_checkbox_offline = self.create_check_box(self.t("checkbox_open_folder") if self.t("checkbox_open_folder") != "checkbox_open_folder" else "Open transcription folder after completion", checked=self.settings["ui"].get("open_transcription_folder", True))
        self.open_folder_checkbox_offline.stateChanged.connect(lambda _: self.on_open_folder_changed(self.open_folder_checkbox_offline.isChecked()))
        self.layout.addWidget(self.open_folder_checkbox_offline)
        self.transcription_button = self.create_button(self.t("btn_transcribe"), self.start_offline_transcription)
        # Online widgets
        self.api_key_label = self.create_label(self.t("label_api_key") if self.t("label_api_key") != "label_api_key" else "OpenAI API Key:")
        api_key_layout = QtWidgets.QHBoxLayout()
        self.api_key_input = QtWidgets.QLineEdit()
        self.api_key_input.setEchoMode(QtWidgets.QLineEdit.Password)
        api_key_layout.addWidget(self.api_key_input)
        self.api_key_eye_button = QtWidgets.QPushButton()
        self.api_key_eye_button.setCheckable(True)
        # Try to use a standard Qt eye icon, fallback to text if not available
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
        self.layout.addLayout(api_key_layout)
        self.online_model_label = self.create_label(self.t("label_online_model") if self.t("label_online_model") != "label_online_model" else "Choose Online Model:")
        self.online_model_combo = self.create_combo_box([
            self.t("combo_whisper1") if self.t("combo_whisper1") != "combo_whisper1" else "whisper-1",
            self.t("combo_whisper2") if self.t("combo_whisper2") != "combo_whisper2" else "whisper-2"
        ], default="whisper-1")
        self.online_temp_audio_checkbox = self.create_check_box(self.t("checkbox_online_temp") if self.t("checkbox_online_temp") != "checkbox_online_temp" else "Temporary audio (will be deleted after online transcription)", checked=True)
        self.layout.addWidget(self.online_temp_audio_checkbox)
        self.open_folder_checkbox_online = self.create_check_box(self.t("checkbox_open_folder") if self.t("checkbox_open_folder") != "checkbox_open_folder" else "Open transcription folder after completion", checked=self.settings["ui"].get("open_transcription_folder", True))
        self.open_folder_checkbox_online.stateChanged.connect(lambda _: self.on_open_folder_changed(self.open_folder_checkbox_online.isChecked()))
        self.layout.addWidget(self.open_folder_checkbox_online)
        self.online_transcription_button = self.create_button(self.t("btn_transcribe"), self.start_online_transcription)
        self.status_label = self.create_label(self.t("status_ready") if self.t("status_ready") != "status_ready" else "Status: Ready", font_size=16, bold=True, alignment=QtCore.Qt.AlignCenter)
        self.size_label = self.create_label(f"{self.t('label_window_size') if self.t('label_window_size') != 'label_window_size' else 'Window Size:'} {self.width()} x {self.height()}", alignment=QtCore.Qt.AlignCenter)
        self.create_menu()
        self.update_status(self.t("status_ready") if self.t("status_ready") != "status_ready" else "Status: Ready", "blue")
        self.transcription_button.installEventFilter(self)
        self.online_transcription_button.installEventFilter(self)
        self.switch_whisper_mode(self.whisper_mode_combo.currentText())

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
        return check_box

    def create_menu(self):
        menubar = self.menuBar()
        menubar.clear()
        settings_menu = menubar.addMenu(self.t('label_settings') if self.t('label_settings') != 'label_settings' else 'Settings')
        theme_menu = settings_menu.addMenu(self.t('label_theme'))
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
        # Ajout du menu de langue
        lang_menu = settings_menu.addMenu(self.t('label_language'))
        self.lang_actions = {}
        lang_group = QtWidgets.QActionGroup(self)
        for lang_name in LANGUAGES:
            action = QtWidgets.QAction(lang_name, self)
            action.setCheckable(True)
            if self.settings["ui"].get("language", "Français") == lang_name:
                action.setChecked(True)
            action.triggered.connect(lambda checked, l=lang_name: self.change_language(l))
            lang_group.addAction(action)
            lang_menu.addAction(action)
            self.lang_actions[lang_name] = action
        # Ajout du menu de taille de fenêtre
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
        # Ajout du bouton de réinitialisation des paramètres
        reset_action = QtWidgets.QAction(self.t('btn_reset_settings') if self.t('btn_reset_settings') != 'btn_reset_settings' else 'Reset to Default', self)
        reset_action.triggered.connect(self.reset_settings_to_default)
        settings_menu.addAction(reset_action)
        # Ajout de la gestion de la clé API dans les paramètres
        api_key_action = QtWidgets.QAction(self.t('menu_manage_api_key') if self.t('menu_manage_api_key') != 'menu_manage_api_key' else 'Gérer la clé API OpenAI', self)
        api_key_action.triggered.connect(self.show_api_key_dialog)
        settings_menu.addAction(api_key_action)
        # Ajout du menu Crédits à la fin
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
        self.api_key_label.setText(self.t("label_api_key") if self.t("label_api_key") != "label_api_key" else "OpenAI API Key:")
        self.online_model_label.setText(self.t("label_online_model") if self.t("label_online_model") != "label_online_model" else "Choose Online Model:")
        self.online_temp_audio_checkbox.setText(self.t("checkbox_online_temp") if self.t("checkbox_online_temp") != "checkbox_online_temp" else "Temporary audio (will be deleted after online transcription)")
        self.open_folder_checkbox_online.setText(self.t("checkbox_open_folder") if self.t("checkbox_open_folder") != "checkbox_open_folder" else "Open transcription folder after completion")
        self.online_transcription_button.setText(self.t("btn_transcribe"))
        self.status_label.setText(self.t("status_ready") if self.t("status_ready") != "status_ready" else "Status: Ready")
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
        self.status_label.setText(self.t(text) if self.t(text) != text else text)
        self.status_label.setStyleSheet(f"color: {color};")
        logging.info(f"Status updated: {text} (color: {color})")

    def reset_status(self):
        self.update_status(self.t("status_ready") if self.t("status_ready") != "status_ready" else "Status: Ready", "blue")
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
        online_widgets = [self.api_key_label, self.api_key_input, self.api_key_eye_button, self.online_model_label, self.online_model_combo, self.online_temp_audio_checkbox, self.open_folder_checkbox_online, self.online_transcription_button]
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
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, self.t("dialog_import_title") if self.t("dialog_import_title") != "dialog_import_title" else "Import Audio File", "", self.t("dialog_import_filter") if self.t("dialog_import_filter") != "dialog_import_filter" else "Audio Files (*.wav *.mp3 *.flac *.m4a *.aac *.ogg *.wma);;All Files (*)", options=options)
        if file_path:
            self.imported_file_path = file_path
            self.last_recorded_file_path = file_path
            self.update_status(self.t("status_audio_imported") if self.t("status_audio_imported") != "status_audio_imported" else "Status: Audio imported", "orange")

    def clear_temp_folder(self):
        reply = QtWidgets.QMessageBox.question(self, self.t('dialog_clear_temp_title') if self.t('dialog_clear_temp_title') != 'dialog_clear_temp_title' else 'Clear Temp Folder', self.t('dialog_clear_temp_text') if self.t('dialog_clear_temp_text') != 'dialog_clear_temp_text' else 'Are you sure you want to clear the Temp folder?', QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
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
            self.update_status(self.t("status_temp_cleared") if self.t("status_temp_cleared") != "status_temp_cleared" else "Status: Temp folder cleared", "green")
            QtCore.QTimer.singleShot(2000, self.reset_status)
        else:
            self.update_status("Status: Temp folder clear cancelled", "orange")
            QtCore.QTimer.singleShot(2000, self.reset_status)

    def start_offline_transcription(self):
        if self.is_recording:
            logging.warning("Attempted transcription while recording.")
            self.update_status("Status: Cannot transcribe while recording", "red")
            return
        if self.is_transcribing:
            logging.warning("Transcription already in progress.")
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
            logging.error("No file selected for transcription.")
            self.update_status("Status: No file selected for transcription", "red")
            self.is_transcribing = False
            self.transcription_button.setEnabled(True)
            return
        self.open_folder_after = self.open_folder_checkbox_offline.isChecked()
        logging.info(f"Starting offline transcription: file={file_path}, save_path={save_path}, language={language}, model={model}, delete_after={delete_after_transcription}")
        self.transcription_thread = TranscriptionThread(self.transcriber, file_path, save_path, language, model, delete_after_transcription)
        self.transcription_thread.transcription_completed.connect(self.on_transcription_completed)
        self.transcription_thread.start()

    def on_transcription_completed(self, status, color):
        logging.info(f"Offline transcription completed. Status: {status}, Color: {color}")
        self.update_status(status, color)
        self.is_transcribing = False
        self.transcription_button.setEnabled(True)
        if getattr(self, 'open_folder_after', False):
            folder = os.path.abspath(os.path.join("Records", "Transcription"))
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(folder))
            logging.info(f"Opened transcription folder: {folder}")
        QtCore.QTimer.singleShot(2000, lambda: self.update_status("Status: Ready", "blue"))

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
        file_path = self.imported_file_path or self.last_recorded_file_path
        if not file_path:
            logging.error("No audio file selected for online transcription.")
            self.update_status("Status: No audio file selected", "red")
            return
        model = self.online_model_combo.currentText()
        delete_temp = self.online_temp_audio_checkbox.isChecked()
        save_path = os.path.join("Records", "Transcription", datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_online.txt")
        self.update_status("Status: Online transcription in progress...", "purple")
        self.open_folder_after_online = self.open_folder_checkbox_online.isChecked()
        logging.info(f"Starting online transcription: file={file_path}, save_path={save_path}, model={model}, delete_temp={delete_temp}")
        self.online_thread = OnlineTranscriptionThread(api_key, file_path, model, delete_temp, save_path)
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
        QtCore.QTimer.singleShot(2000, lambda: self.update_status("Status: Ready", "blue"))

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
