from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt

class TakePicturePage(QWidget):
    """Page for taking a picture of an ulam."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        label = QLabel("Take a picture of an ulam (camera integration coming soon)")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 22px; color: #273c75;")
        layout.addWidget(label)
        self.back_btn = QPushButton("⬅️ Back")
        layout.addWidget(self.back_btn)
        layout.addStretch()
        self.setLayout(layout)

class UploadPicturePage(QWidget):
    """Page for uploading a picture of an ulam."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        label = QLabel("Upload a picture of an ulam (upload feature coming soon)")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 22px; color: #273c75;")
        layout.addWidget(label)
        self.back_btn = QPushButton("⬅️ Back")
        layout.addWidget(self.back_btn)
        layout.addStretch()
        self.setLayout(layout)
