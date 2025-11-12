from PyQt5.QtWidgets import QMainWindow, QLabel
from PyQt5.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UlamLens")
        self.setGeometry(100, 100, 800, 600)
    self.label = QLabel("Welcome to UlamLens!", self)
    self.label.setGeometry(200, 250, 400, 100)
    self.label.setAlignment(Qt.AlignCenter)
