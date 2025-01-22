#!/bin/bash
echo "Building AudioTranscriber for Linux..."
pyinstaller --onefile --distpath ../../Builds/Linux ../src/main.py
echo "Build completed. The executable is located in the Builds/Linux folder."
