import sys
import subprocess
import platform
from PyQt5 import QtWidgets

def check_and_install_dependencies():
    missing = []
    # Check torch
    try:
        import torch
    except ImportError:
        missing.append('torch')
    # Check whisper
    try:
        import whisper
    except ImportError:
        missing.append('openai-whisper')
    # Check ffmpeg
    ffmpeg_installed = False
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        ffmpeg_installed = True
    except Exception:
        ffmpeg_installed = False
    if not ffmpeg_installed:
        missing.append('ffmpeg')
    if missing:
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setWindowTitle('Missing dependencies')
        text = 'Some dependencies are missing:\n\n'
        for dep in missing:
            text += f'- {dep}\n'
        text += '\nWould you like to try automatic installation?'
        msg.setText(text)
        msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        ret = msg.exec_()
        if ret == QtWidgets.QMessageBox.Yes:
            pip_missing = [d for d in missing if d != 'ffmpeg']
            if pip_missing:
                try:
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + pip_missing)
                except Exception as e:
                    QtWidgets.QMessageBox.critical(None, 'Error', f"Pip install failed: {e}")
                    return False
            if 'ffmpeg' in missing:
                os_name = platform.system()
                if os_name == 'Windows':
                    ffmpeg_url = 'https://www.gyan.dev/ffmpeg/builds/'
                    install_hint = "Download the ZIP archive, extract it, and add the 'bin' folder to your PATH."
                elif os_name == 'Darwin':
                    ffmpeg_url = 'https://evermeet.cx/ffmpeg/'
                    install_hint = "You can also use Homebrew: brew install ffmpeg."
                elif os_name == 'Linux':
                    ffmpeg_url = 'https://ffmpeg.org/download.html#build-linux'
                    install_hint = "You can also use your package manager: sudo apt install ffmpeg (Debian/Ubuntu), sudo dnf install ffmpeg (Fedora), etc."
                else:
                    ffmpeg_url = 'https://ffmpeg.org/download.html'
                    install_hint = "See the official documentation."
                QtWidgets.QMessageBox.information(None, 'ffmpeg required',
                    f"ffmpeg is not installed or not in PATH.\n\n" +
                    f"Detected system: {os_name}\n" +
                    f"Download page: {ffmpeg_url}\n" +
                    f"{install_hint}\n\nAfter installation, restart the application.")
                return False
            QtWidgets.QMessageBox.information(None, 'Success', 'Installation complete. Please restart the application.')
            return False
        else:
            QtWidgets.QMessageBox.critical(None, 'Missing dependencies',
                'The application cannot start without these dependencies.')
            return False
    return True
