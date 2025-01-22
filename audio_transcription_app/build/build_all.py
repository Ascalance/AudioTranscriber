import os
import subprocess
import platform

def build_windows():
    print("Building AudioTranscriber for Windows...")
    subprocess.run(["pyinstaller", "--onefile", "--distpath", "../../../Builds/Windows", "../../src/main.py"])
    print("Build completed. The executable is located in the Builds/Windows folder.")

def build_linux():
    print("Building AudioTranscriber for Linux...")
    subprocess.run(["pyinstaller", "--onefile", "--distpath", "../../../Builds/Linux", "../../src/main.py"])
    print("Build completed. The executable is located in the Builds/Linux folder.")

def build_mac():
    print("Building AudioTranscriber for macOS...")
    subprocess.run(["pyinstaller", "--onefile", "--distpath", "../../../Builds/Mac", "../../src/main.py"])
    print("Build completed. The executable is located in the Builds/Mac folder.")

def main():
    print("Select the target platform:")
    print("1. Windows")
    print("2. Linux")
    print("3. macOS")
    choice = input("Enter the number of the target platform: ")

    if choice == "1":
        build_windows()
    elif choice == "2":
        build_linux()
    elif choice == "3":
        build_mac()
    else:
        print("Invalid choice. Please select a valid platform.")

if __name__ == "__main__":
    main()
