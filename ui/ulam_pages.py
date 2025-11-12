import os
import os
import cv2
try:
    import openai
except Exception:
    openai = None
    print('[init] openai package not available; analysis calls will be disabled or use fallback.')
try:
    import requests
except Exception:
    requests = None
    print('[init] requests package not available; HTTP fallback disabled.')
import tempfile
import json
import base64
import threading
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QApplication, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QStackedLayout, QSizePolicy, QSpacerItem
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap

class TakePicturePage(QWidget):
    analysis_finished = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.captured_image = None
        self.camera_active = True
        self._analysis_cancelled = False
        # OpenAI API key: prefer environment variable, fall back to None
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')

        # Initialize UI; if init_ui is missing for any reason, create a minimal fallback UI
        try:
            self.init_ui()
        except Exception as e:
            print(f"[init_ui] init_ui failed: {e}. Creating fallback UI.")
            self._init_ui_fallback()
        self.cap = cv2.VideoCapture(0)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        # Ensure the analysis result signal is handled on the UI thread
        try:
            self.analysis_finished.connect(self.show_analysis_result)
        except Exception:
            # If connecting fails for some reason, we'll fallback to calling the slot directly
            pass

        # (moved analyze_btn connection to end of init_ui)
    def analyze_ulam(self):
        """Start analysis in a background thread with a cancellable dialog."""
        print("[Analyze] Button clicked.")
        if self.captured_image is None:
            print("[Analyze] No image captured.")
            QMessageBox.warning(self, "No Image", "Please capture an image first.")
            return

        # Reset cancel flag for this run
        self._analysis_cancelled = False

        # If API key missing, show N/A result immediately
        if not self.openai_api_key:
            print("[Analyze] No OpenAI API key set. Showing N/A result.")
            result_json = {
                "ulam_name": "N/A",
                "macros": {"calories": "N/A", "protein_g": "N/A", "carbs_g": "N/A", "fat_g": "N/A"},
                "health_facts": "N/A",
                "warnings": "N/A",
                "error": "OpenAI API key is not set. Please configure your API key to enable analysis."
            }
            # emit via signal to unify UI thread handling
            try:
                self.analysis_finished.emit(result_json)
            except Exception:
                self.show_analysis_result(result_json)
            return

        # Save image to temp file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            img_path = tmp.name
            cv2.imwrite(img_path, self.captured_image)
        print(f"[Analyze] Image saved to {img_path}")

        prompt = (
            "You are a nutrition and Filipino food expert. "
            "Given a photo of a Filipino viand (ulam), guess what ulam it is and return a JSON with the following structure: "
            '{\n'
            '  "ulam_name": string,\n'
            '  "macros": {\n'
            '    "calories": int,\n'
            '    "protein_g": float,\n'
            '    "carbs_g": float,\n'
            '    "fat_g": float\n'
            '  },\n'
            '  "health_facts": string,\n'
            '  "warnings": string\n'
            '}\n'
            "If you are unsure, make your best guess."
        )

        # Create cancellable loading dialog
        loading = QDialog(self)
        loading.setWindowTitle("Analyzing Ulam...")
        loading.setModal(True)
        dlg_layout = QVBoxLayout(loading)
        msg = QLabel("Analyzing the captured image. Please wait...")
        msg.setAlignment(Qt.AlignCenter)
        dlg_layout.addWidget(msg)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(lambda: self._set_analysis_cancelled(loading))
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        dlg_layout.addLayout(btn_row)
        loading.show()
        QApplication.processEvents()

        def run_analysis():
            result_json = {}
            try:
                if self._analysis_cancelled:
                    result_json = {"error": "Analysis cancelled by user."}
                    return
                openai.api_key = self.openai_api_key

                with open(img_path, "rb") as f:
                    image_bytes = f.read()
                b64 = base64.b64encode(image_bytes).decode('ascii')
                print(f"[Analyze] Image bytes length: {len(image_bytes)}")

                # Prefer new OpenAI client (openai.OpenAI) if available
                if openai is None:
                    result_json = {"error": "openai package not installed. Install 'openai' to enable analysis."}
                    raw_text = ''
                elif hasattr(openai, "OpenAI"):
                    client = openai.OpenAI(api_key=self.openai_api_key)
                    # Try vision-capable model first; if unavailable, fall back to text-only models
                    tried_models = []
                    raw_text = None
                    vision_models = ["gpt-4-vision-preview"]
                    text_fallback_models = ["gpt-4", "gpt-3.5-turbo"]
                    # Attempt vision models
                    for mname in vision_models:
                        tried_models.append(mname)
                        try:
                            resp = client.responses.create(
                                model=mname,
                                input=[
                                    {"role": "user", "content": [
                                        {"type": "input_text", "text": prompt},
                                        {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"}
                                    ]}
                                ],
                                max_output_tokens=500
                            )
                            raw_text = getattr(resp, 'output_text', None)
                            if not raw_text:
                                parts = []
                                for item in getattr(resp, 'output', []):
                                    for c in item.get('content', []):
                                        txt = c.get('text') or c.get('title') or ''
                                        if txt:
                                            parts.append(txt)
                                raw_text = "\n".join(parts)
                            print(f"[Analyze] Raw response (new API, {mname}): {raw_text}")
                            break
                        except Exception as err:
                            err_str = str(err)
                            print(f"[Analyze] Model {mname} failed: {err_str}")
                            # If model doesn't exist, continue to text-only fallback
                            continue

                    # If no vision result, try text-only models (image will be omitted; results will be guesses)
                    if not raw_text:
                        # Try direct HTTP multipart/form-data upload as a last resort
                        if requests is not None:
                            endpoint = os.environ.get('OPENAI_IMAGE_ENDPOINT', 'https://api.openai.com/v1/responses')
                            model_for_request = 'gpt-4-vision-preview'
                            headers = {"Authorization": f"Bearer {self.openai_api_key}"}
                            try:
                                with open(img_path, 'rb') as imgf:
                                    files = {"image": (os.path.basename(img_path), imgf, "image/jpeg")}
                                    data = {"model": model_for_request, "input": prompt}
                                    print(f"[Analyze] Attempting HTTP POST to {endpoint} with model {model_for_request}")
                                    resp = requests.post(endpoint, headers=headers, files=files, data=data, timeout=60)
                                if resp.status_code == 200:
                                    try:
                                        rj = resp.json()
                                    except Exception:
                                        rj = {}
                                    # Try common response fields
                                    raw_text = rj.get('output_text') or rj.get('text') or ''
                                    if not raw_text:
                                        out = rj.get('output') or rj.get('choices') or []
                                        parts = []
                                        for item in out:
                                            if isinstance(item, dict):
                                                # responses API
                                                for c in item.get('content', []):
                                                    txt = c.get('text') or c.get('title') or ''
                                                    if txt:
                                                        parts.append(txt)
                                            elif isinstance(item, str):
                                                parts.append(item)
                                        raw_text = "\n".join(parts)
                                    print(f"[Analyze] Raw response (http fallback): {raw_text}")
                                else:
                                    print(f"[Analyze] HTTP fallback returned {resp.status_code}: {resp.text}")
                            except Exception as err:
                                print(f"[Analyze] HTTP fallback failed: {err}")
                        else:
                            print('[Analyze] requests not available; skipping HTTP fallback')
                        for mname in text_fallback_models:
                            tried_models.append(mname)
                            try:
                                resp = client.responses.create(
                                    model=mname,
                                    input=prompt + "\n\nNOTE: The image could not be attached; provide your best-guess JSON based on common Filipino ulam. Mark values as 'estimate' where unsure.",
                                    max_output_tokens=500
                                )
                                raw_text = getattr(resp, 'output_text', None)
                                if not raw_text:
                                    parts = []
                                    for item in getattr(resp, 'output', []):
                                        for c in item.get('content', []):
                                            txt = c.get('text') or c.get('title') or ''
                                            if txt:
                                                parts.append(txt)
                                    raw_text = "\n".join(parts)
                                print(f"[Analyze] Raw response (new API fallback, {mname}): {raw_text}")
                                break
                            except Exception as err:
                                print(f"[Analyze] Text model {mname} failed: {err}")
                                continue
                    if not raw_text:
                        raw_text = ""
                else:
                    # Legacy fallback using ChatCompletion (may not support images)
                    try:
                        response = openai.ChatCompletion.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {"role": "system", "content": prompt},
                                {"role": "user", "content": "Image attachment omitted (vision model unavailable). Please provide best-guess JSON as described."}
                            ],
                            max_tokens=500
                        )
                        raw_text = response.choices[0].message['content']
                        print(f"[Analyze] Raw response (legacy fallback): {raw_text}")
                    except Exception as err:
                        print(f"[Analyze] Legacy ChatCompletion failed: {err}")
                        raw_text = ''

                # After obtaining raw_text (from new or legacy API), try to extract JSON
                try:
                    json_start = raw_text.find('{')
                    json_end = raw_text.rfind('}') + 1
                    json_str = raw_text[json_start:json_end]
                    result_json = json.loads(json_str)
                except Exception as ex:
                    print(f"[Analyze] Failed to parse JSON: {ex}")
                    result_json = {"error": "Could not parse JSON", "raw": raw_text}
            except Exception as e:
                print(f"[Analyze] Exception: {e}")
                result_json = {"error": str(e)}
            finally:
                # close loading dialog in main thread
                try:
                    loading.done(0)
                except Exception:
                    pass
                # emit result to main thread
                try:
                    self.analysis_finished.emit(result_json)
                except Exception:
                    # fallback: call directly
                    self.show_analysis_result(result_json)

        # run in background
        thread = threading.Thread(target=run_analysis, daemon=True)
        thread.start()

    def show_analysis_result(self, result_json):
        dlg = QDialog(self)
        dlg.setWindowTitle("Ulam Analysis Result")
        dlg.setMinimumWidth(400)
        layout = QVBoxLayout()
        dlg.setLayout(layout)

        if 'error' in result_json:
            label = QLabel(f"<b>Error:</b> {result_json['error']}")
            layout.addWidget(label)
            if 'raw' in result_json:
                text = QTextEdit()
                text.setReadOnly(True)
                text.setText(result_json['raw'])
                layout.addWidget(text)
        else:
            # Pretty display
            ulam = result_json.get('ulam_name', 'Unknown')
            macros = result_json.get('macros', {})
            facts = result_json.get('health_facts', '')
            warnings = result_json.get('warnings', '')
            html = f"""
            <h2>{ulam}</h2>
            <h3>Macros</h3>
            <ul>
                <li><b>Calories:</b> {macros.get('calories', '?')}</li>
                <li><b>Protein:</b> {macros.get('protein_g', '?')} g</li>
                <li><b>Carbs:</b> {macros.get('carbs_g', '?')} g</li>
                <li><b>Fat:</b> {macros.get('fat_g', '?')} g</li>
            </ul>
            <h3>Health Facts</h3>
            <p>{facts}</p>
            <h3>Warnings</h3>
            <p style='color:#e84118'>{warnings}</p>
            """
            label = QLabel(html)
            label.setWordWrap(True)
            layout.addWidget(label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dlg.accept)
        layout.addWidget(buttons)
        dlg.exec_()

    def _set_analysis_cancelled(self, dlg=None):
        """Mark analysis as cancelled and close the loading dialog if provided."""
        self._analysis_cancelled = True
        try:
            if dlg is not None:
                dlg.done(0)
        except Exception:
            pass

    def _init_ui_fallback(self):
        """Create a minimal UI if init_ui is unavailable to avoid crashes."""
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        label = QLabel("Camera UI failed to initialize. Minimal UI loaded.")
        label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(label)
        self.back_btn = QPushButton("⬅️ Back")
        self.main_layout.addWidget(self.back_btn)

    def init_ui(self):
        # Camera preview area (fills most of the window)
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

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

        self.analyze_btn.setEnabled(False)
        self.analyze_btn.hide()
        self.button_row.addWidget(self.analyze_btn)
        self.analyze_btn.clicked.connect(self.analyze_ulam)

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
        self.analyze_btn.setEnabled(True)
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
        self.analyze_btn.setEnabled(False)
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
