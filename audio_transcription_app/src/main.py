import subprocess
import sys
import platform
from PyQt5 import QtWidgets, QtCore
from app import AppUI

def check_and_install_dependencies():
    missing = []
    # Vérifie torch
    try:
        import torch
    except ImportError:
        missing.append('torch')
    # Vérifie whisper
    try:
        import whisper
    except ImportError:
        missing.append('openai-whisper')
    # Vérifie ffmpeg
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
        msg.setWindowTitle('Dépendances manquantes')
        text = 'Certaines dépendances sont manquantes :\n\n'
        for dep in missing:
            text += f'- {dep}\n'
        text += '\nVoulez-vous tenter une installation automatique ?'
        msg.setText(text)
        msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        ret = msg.exec_()
        if ret == QtWidgets.QMessageBox.Yes:
            # Installation automatique
            pip_missing = [d for d in missing if d != 'ffmpeg']
            if pip_missing:
                try:
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + pip_missing)
                except Exception as e:
                    QtWidgets.QMessageBox.critical(None, 'Erreur', f"Échec de l'installation pip : {e}")
                    return False
            if 'ffmpeg' in missing:
                os_name = platform.system()
                if os_name == 'Windows':
                    ffmpeg_url = 'https://www.gyan.dev/ffmpeg/builds/'
                    install_hint = "Téléchargez l'archive ZIP, extrayez-la et ajoutez le dossier 'bin' au PATH."
                elif os_name == 'Darwin':
                    ffmpeg_url = 'https://evermeet.cx/ffmpeg/'
                    install_hint = "Vous pouvez aussi utiliser Homebrew : brew install ffmpeg."
                elif os_name == 'Linux':
                    ffmpeg_url = 'https://ffmpeg.org/download.html#build-linux'
                    install_hint = "Vous pouvez aussi utiliser votre gestionnaire de paquets : sudo apt install ffmpeg (Debian/Ubuntu), sudo dnf install ffmpeg (Fedora), etc."
                else:
                    ffmpeg_url = 'https://ffmpeg.org/download.html'
                    install_hint = "Consultez la documentation officielle."
                QtWidgets.QMessageBox.information(None, 'ffmpeg requis',
                    f"ffmpeg n'est pas installé ou n'est pas dans le PATH.\n\n" +
                    f"Système détecté : {os_name}\n" +
                    f"Page de téléchargement : {ffmpeg_url}\n" +
                    f"{install_hint}\n\nAprès installation, redémarrez l'application.")
                return False
            QtWidgets.QMessageBox.information(None, 'Succès', 'Installation terminée. Veuillez redémarrer l’application.')
            return False
        else:
            QtWidgets.QMessageBox.critical(None, 'Dépendances manquantes',
                'L’application ne peut pas démarrer sans ces dépendances.')
            return False
    return True

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    if not check_and_install_dependencies():
        sys.exit(1)
    window = AppUI()
    window.show()
    app.exec_()