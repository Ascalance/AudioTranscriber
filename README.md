# AudioTranscriber

AudioTranscriber is an application for recording and transcribing audio files. It supports multiple languages and allows you to choose the Whisper model for transcription.

## Features
- Transcribe audio files to text
- Support for multiple audio formats (mp3, wav, etc.)
- Real-time transcription
- Language detection
- Speaker identification
- Export transcriptions to a .txt file

## Requirements
- Python 3.6+
- sounddevice
- numpy
- wave
- whisper
- pydub
- pyinstaller
- PyQt5

## Installation
1. Clone the repository:
    ```sh
    git clone https://github.com/IA91/AudioTranscriber.git
    cd AudioTranscriber
    ```
2. Install the required Python packages:
    ```sh
    pip install -r requirements.txt
    ```
3. Install ffmpeg:
    - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
    - **macOS**: Install via Homebrew
        ```sh
        brew install ffmpeg
        ```
    - **Linux**: Install via package manager
        ```sh
        sudo apt-get install ffmpeg
        ```

## Usage
1. Run the application:
    ```sh
    python main.py
    ```
2. Follow the on-screen instructions to upload an audio file and start transcription.

## Contributing
Contributions are welcome! Please fork the repository and create a pull request with your changes.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Credits
Author: Baptiste Lusseau
GitHub: Ascalance