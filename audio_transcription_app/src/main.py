from PyQt5 import QtWidgets
from app import AppUI

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = AppUI()
    window.show()
    app.exec_() 