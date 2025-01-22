#!/bin/bash
echo "Building AudioTranscriber for macOS..."
pyinstaller --onefile --distpath ../../Builds/Mac ../src/main.py
echo "Build completed. The executable is located in the Builds/Mac folder."
