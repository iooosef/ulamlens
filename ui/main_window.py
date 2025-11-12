from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt
from ui.ulam_pages import TakePicturePage, UploadPicturePage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UlamLens")
        self.setGeometry(100, 100, 800, 600)

        self.show_main_menu()

    def show_main_menu(self):
        # Central widget and layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        layout.setSpacing(30)
        layout.setContentsMargins(80, 60, 80, 60)
        central_widget.setLayout(layout)

        # Set background color
        self.setStyleSheet("background-color: #f5f6fa;")

        # Title label with style
        title_label = QLabel("🍲 <b>UlamLens</b> 🍲", self)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #273c75; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # Subtitle label
        subtitle_label = QLabel("<i>Choose an option:</i>", self)
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("font-size: 18px; color: #353b48; margin-bottom: 30px;")
        layout.addWidget(subtitle_label)

        # Button: Take a picture of an ulam
        self.take_picture_btn = QPushButton("📷 Take a picture of an ulam", self)
        self.take_picture_btn.setStyleSheet('''
            QPushButton {
                background-color: #00a8ff;
                color: white;
                font-size: 20px;
                border-radius: 12px;
                padding: 18px 0;
                margin-bottom: 10px;
            }
            QPushButton:hover {
                background-color: #0097e6;
            }
        ''')
        layout.addWidget(self.take_picture_btn)
        self.take_picture_btn.clicked.connect(self.show_take_picture_page)

        # Button: Upload a picture of an ulam
        self.upload_picture_btn = QPushButton("🖼️ Upload a picture of an ulam", self)
        self.upload_picture_btn.setStyleSheet('''
            QPushButton {
                background-color: #9c88ff;
                color: white;
                font-size: 20px;
                border-radius: 12px;
                padding: 18px 0;
                margin-bottom: 10px;
            }
            QPushButton:hover {
                background-color: #8c7ae6;
            }
        ''')
        layout.addWidget(self.upload_picture_btn)
        self.upload_picture_btn.clicked.connect(self.show_upload_picture_page)

        # Add stretch to center the buttons
        layout.addStretch()

    def show_take_picture_page(self):
        self.take_picture_page = TakePicturePage(self)
        self.setCentralWidget(self.take_picture_page)
        self.take_picture_page.back_btn.clicked.connect(self.show_main_menu)

    def show_upload_picture_page(self):
        self.upload_picture_page = UploadPicturePage(self)
        self.setCentralWidget(self.upload_picture_page)
        self.upload_picture_page.back_btn.clicked.connect(self.show_main_menu)
