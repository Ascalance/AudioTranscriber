@echo off
REM Active la venv puis lance l'appli
call .\venv\Scripts\activate
python -m pip install -r .\requirements.txt
python .\audio_transcription_app\src\main.py