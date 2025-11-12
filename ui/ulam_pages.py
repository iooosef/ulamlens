import cv2
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QApplication
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap

class TakePicturePage(QWidget):
    """Page for taking a picture of an ulam using the laptop's camera."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.captured_image = None
        self.camera_active = True
        self.init_ui()
        self.cap = cv2.VideoCapture(0)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def init_ui(self):
        from PyQt5.QtWidgets import QStackedLayout, QSizePolicy, QSpacerItem

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Camera preview area (fills most of the window)
        self.video_container = QWidget(self)
        self.video_container_layout = QStackedLayout()
        self.video_container.setLayout(self.video_container_layout)
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background: #222; border-radius: 18px;")
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_container_layout.addWidget(self.video_label)

        # Loading overlay
        self.loading_label = QLabel("<b>Loading camera...</b>", self)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("background: rgba(245,246,250,0.85); color: #273c75; font-size: 32px; border-radius: 18px;")
        self.video_container_layout.addWidget(self.loading_label)
        self.video_container_layout.setCurrentWidget(self.loading_label)

        self.main_layout.addWidget(self.video_container, stretch=1)

        # Modern button row (large, spaced, horizontal)
        self.button_row = QHBoxLayout()
        self.button_row.setSpacing(30)
        self.button_row.setContentsMargins(40, 20, 40, 20)

        self.capture_btn = QPushButton("📸 Capture")
        self.capture_btn.setMinimumHeight(60)
        self.capture_btn.setMinimumWidth(180)
        self.capture_btn.setStyleSheet('''
            QPushButton {
                background-color: #00a8ff;
                color: white;
                font-size: 24px;
                border-radius: 16px;
                padding: 18px 36px;
            }
            QPushButton:hover {
                background-color: #0097e6;
            }
        ''')
        self.capture_btn.clicked.connect(self.capture_image)
        self.button_row.addWidget(self.capture_btn)

        self.analyze_btn = QPushButton("Analyze")
        self.analyze_btn.setMinimumHeight(60)
        self.analyze_btn.setMinimumWidth(180)
        self.analyze_btn.setStyleSheet('''
            QPushButton {
                background-color: #44bd32;
                color: white;
                font-size: 24px;
                border-radius: 16px;
                padding: 18px 36px;
            }
            QPushButton:hover {
                background-color: #4cd137;
            }
        ''')
        self.analyze_btn.hide()
        self.button_row.addWidget(self.analyze_btn)

        self.retake_btn = QPushButton("Retake")
        self.retake_btn.setMinimumHeight(60)
        self.retake_btn.setMinimumWidth(180)
        self.retake_btn.setStyleSheet('''
            QPushButton {
                background-color: #e84118;
                color: white;
                font-size: 24px;
                border-radius: 16px;
                padding: 18px 36px;
            }
            QPushButton:hover {
                background-color: #c23616;
            }
        ''')
        self.retake_btn.hide()
        self.button_row.addWidget(self.retake_btn)

        # Add a back button for navigation compatibility
        self.back_btn = QPushButton("⬅️ Back")
        self.back_btn.setMinimumHeight(60)
        self.back_btn.setMinimumWidth(120)
        self.back_btn.setStyleSheet('''
            QPushButton {
                background-color: #353b48;
                color: white;
                font-size: 20px;
                border-radius: 16px;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #2f3640;
            }
        ''')
        self.button_row.addWidget(self.back_btn)

        self.main_layout.addLayout(self.button_row)

        # Spacer to push buttons to bottom
        self.main_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def update_frame(self):
        if self.camera_active:
            ret, frame = self.cap.read()
            if ret:
                self.frame = frame
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image).scaled(self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.video_label.setPixmap(pixmap)
                # Hide loading overlay when first frame is received
                if self.video_container_layout.currentWidget() == self.loading_label:
                    self.video_container_layout.setCurrentWidget(self.video_label)

    def capture_image(self):
        # Show loading overlay while freezing
        self.video_container_layout.setCurrentWidget(self.loading_label)
        QApplication.processEvents()
        ret, frame = self.cap.read()
        if ret:
            self.captured_image = frame
            self.camera_active = False
            self.timer.stop()
            self.cap.release()
            self.show_captured_image()

    def show_captured_image(self):
        rgb_image = cv2.cvtColor(self.captured_image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image).scaled(self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_label.setPixmap(pixmap)
        self.video_container_layout.setCurrentWidget(self.video_label)
        # Show analyze/retake, hide capture
        self.capture_btn.hide()
        self.analyze_btn.show()
        self.retake_btn.show()
        # Only connect retake_btn once
        if not hasattr(self, '_retake_connected'):
            self.retake_btn.clicked.connect(self.retake_picture)
            self._retake_connected = True

    def retake_picture(self):
        self.cap = cv2.VideoCapture(0)
        self.camera_active = True
        self.timer.start(30)
        self.capture_btn.show()
        self.analyze_btn.hide()
        self.retake_btn.hide()
        self.video_container_layout.setCurrentWidget(self.loading_label)

    def closeEvent(self, event):
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        event.accept()

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
