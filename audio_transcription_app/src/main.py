
# -------------------
# AudioTranscriber Main Entrypoint
# -------------------

from tools.utils.logging_config import configure_logging
configure_logging()

import sys
from PyQt5 import QtWidgets
from tools.utils.logging_config import start_new_log_session, end_log_session
from tools.utils.dependencies import check_and_install_dependencies
from app import AppUI

if __name__ == "__main__":
    configure_logging()
    start_new_log_session()
    app = QtWidgets.QApplication([])
    app.aboutToQuit.connect(end_log_session)
    if not check_and_install_dependencies():
        sys.exit(1)
    window = AppUI()
    window.show()
    # Force menu bar to be native (pour Windows/Linux)
    window.menuBar().setNativeMenuBar(False)
    app.exec_()