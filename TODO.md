# TODO - AudioTranscriber Improvements

## Error Handling & User Feedback
- ~~Add more detailed error messages for failed transcriptions, missing dependencies, or invalid API keys.~~
- Add progress indicators (progress bar or spinner) during long operations (recording, transcription).
- ~~Graceful handling if ffmpeg, torch, or whisper models are missing (with actionable suggestions).~~

## UI/UX Enhancements
- ~~Add drag-and-drop support for importing audio files.~~
- Make the window resizable or use an adaptive layout for different screen sizes.
- Improve accessibility (keyboard navigation, screen reader support).
- ~~Add multi-language UI (internationalization).~~

## Audio Features
- ~~Add audio playback within the app before/after transcription.~~
- Add waveform visualization during or after recording.
- ~~Support more audio formats and automatic conversion if needed.~~

## Transcription Features
- Add batch transcription (multiple files at once).
- Add transcription history with easy access to previous results.
- ~~Add export options (PDF, DOCX, SRT for subtitles).~~
- Add timestamped transcription (for subtitles or easier review).

## Settings & Profiles
- Add user profiles for saving different sets of preferences.
- Add cloud sync of settings (optional).
- Add advanced settings for Whisper (temperature, best_of, etc.).

## Performance & Architecture
- Use asynchronous I/O for file operations and network requests.
- Improve separation of concerns (MVC/MVVM pattern for PyQt).
- Add unit and integration tests for critical components.

## Security
- ~~Store API keys securely (not in plain text).~~
- ~~Option to mask/unmask API key input.~~

## Documentation
- Add in-app help or tooltips for each option.
- Add more detailed README with screenshots and troubleshooting.

## Cross-platform Packaging
- Provide a one-click installer for Windows/macOS/Linux (PyInstaller, cx_Freeze, etc.).
- Add a portable mode (no installation required).
