@echo off
echo Building AudioTranscriber for Windows...
pyinstaller --onefile --distpath ../../Builds/Windows ../src/main.py
echo Build completed. The executable is located in the Builds/Windows folder.
pause
