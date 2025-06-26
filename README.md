# AudioTranscriber

AudioTranscriber is a modern PyQt5 application for recording, importing, and transcribing audio files (Whisper OpenAI online/offline). It features advanced user settings management, light/dark themes, and a polished user experience.

## Main Features
- Direct audio recording or import of files (wav, mp3, flac, etc.)
- Offline transcription (local Whisper models) or online (OpenAI Whisper API)
- Automatic language detection or manual selection
- Whisper model selection (offline and online)
- Clear interface: dynamic widgets depending on the mode (online/offline)
- Customizable light/dark theme
- Customizable welcome message on first launch
- Optional automatic opening of the transcription folder after completion
- Persistent saving of all user settings
- Export transcriptions to .txt
- Easy cleaning of the Temp folder
- License and credits accessible from the menu

## Requirements
- Python 3.8+
- ffmpeg (for handling some audio formats)

## Installation
1. Clone the repository:
    ```sh
    git clone https://github.com/IA91/AudioTranscriber.git
    cd AudioTranscriber
    ```
2. Create a virtual environment (recommended):
    ```sh
    python -m venv venv
    # Activate the venv (Windows PowerShell)
    .\venv\Scripts\Activate.ps1
    # or (Windows CMD)
    venv\Scripts\activate
    ```
3. Install Python dependencies:
    ```sh
    pip install -r requirements.txt
    ```
4. Install ffmpeg:
    - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
    - **macOS**: via Homebrew
        ```sh
        brew install ffmpeg
        ```
    - **Linux**: via your package manager
        ```sh
        sudo apt-get install ffmpeg
        ```

## Usage
1. Run the application:
    ```sh
    python audio_transcription_app/src/main.py
    ```
2. Use the graphical interface to record, import, and transcribe your audio files.
3. Configure your preferences (mode, model, language, theme, etc.) via the UI.

## User Settings
- All settings are saved in `Settings/user/settings.json`.
- The welcome message can be customized in `Settings/app/first_run_message.txt`.
- The dark theme is defined in `Settings/app/dark_stylesheet.qss`.

## Main Dependencies
- torch
- numpy
- openai
- openai-whisper
- PyQt5
- sounddevice
- pydub
- requests

## Contributing
Contributions are welcome! Fork the repository and submit a pull request.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Credits
Author: Baptiste Lusseau  
GitHub: Ascalance