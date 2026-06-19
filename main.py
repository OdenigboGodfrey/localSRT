import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QComboBox, 
    QProgressBar, QSpinBox
)
from PyQt6.QtCore import Qt
from shared import APP_NAME
from worker import Worker


# -----------------------
# UI MAIN WINDOW
# -----------------------
class App(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(APP_NAME)
        self.resize(550, 600)
        self.setMinimumSize(450, 450)

        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                color: #333333;
            }
            QLabel {
                color: #495057;
            }
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
            QPushButton:pressed {
                background-color: #0a58ca;
            }
            QSpinBox, QComboBox {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 5px;
                min-height: 25px;
            }
            QSpinBox:focus, QComboBox:focus {
                border: 1px solid #86b7fe;
            }
            QProgressBar {
                border: 1px solid #ced4da;
                border-radius: 5px;
                text-align: center;
                background-color: #e9ecef;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #198754;
                border-radius: 4px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # --- AI Disclaimer Box ---
        disclaimer_text = (
            "⚠️ <b>Notice:</b> Because this application uses AI to generate subtitles, "
            "occasional inaccuracies or omissions may occur.<br>"
            "Larger models generally provide better accuracy but take longer to process."
        )
        self.disclaimer_label = QLabel(disclaimer_text)
        self.disclaimer_label.setWordWrap(True)
        self.disclaimer_label.setStyleSheet("""
            QLabel {
                background-color: #fff3cd;
                color: #664d03;
                border: 1px solid #ffecb5;
                border-radius: 6px;
                padding: 12px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.disclaimer_label)

        # --- File Status Label ---
        self.label = QLabel("No file or folder selected")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setStyleSheet("""
            QLabel {
                background-color: #e9ecef;
                border: 1px dashed #adb5bd;
                border-radius: 6px;
                padding: 15px;
                font-weight: 500;
                color: #495057;
            }
        """)
        layout.addWidget(self.label)

        # --- File Selection Buttons (Horizontal) ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_file = QPushButton("📁 Select File")
        self.btn_file.clicked.connect(self.select_file)
        btn_layout.addWidget(self.btn_file)

        self.btn_folder = QPushButton("📂 Select Folder")
        self.btn_folder.clicked.connect(self.select_folder)
        btn_layout.addWidget(self.btn_folder)
        
        layout.addLayout(btn_layout)

        # --- Divider Line ---
        line = QLabel()
        line.setStyleSheet("background-color: #dee2e6; max-height: 1px;")
        layout.addWidget(line)

        # --- Settings: Chunk Size ---
        chunk_label = QLabel("Chunk Size (seconds)")
        chunk_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(chunk_label)
        
        chunk_help = QLabel("Larger chunks take longer to process and use more memory.")
        chunk_help.setStyleSheet("color: #6c757d; font-size: 11px; font-style: italic;")
        layout.addWidget(chunk_help)

        self.chunk = QSpinBox()
        self.chunk.setRange(1, 1000)
        self.chunk.setValue(30)
        layout.addWidget(self.chunk)

        # --- Settings: Model Selection ---
        model_label = QLabel("AI Model Size")
        model_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(model_label)
        
        model_help = QLabel("Changing models will trigger a download if it's not cached locally.")
        model_help.setStyleSheet("color: #6c757d; font-size: 11px; font-style: italic;")
        layout.addWidget(model_help)

        self.model = QComboBox()
        self.model.addItems(["tiny", "base", "medium", "large"])
        self.model.setCurrentIndex(1)
        layout.addWidget(self.model)

        # --- Space Filler ---
        layout.addStretch()

        # --- Execution Controls ---
        self.start_btn = QPushButton("🚀 Start Processing")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #198754;
                font-size: 14px;
                padding: 10px;
            }
            QPushButton:hover { background-color: #157347; }
            QPushButton:pressed { background-color: #146c43; }
        """)
        self.start_btn.clicked.connect(self.start)
        layout.addWidget(self.start_btn)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.setLayout(layout)

        self.path = None
        self.worker = None

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video",
            "",
            "Videos (*.mp4 *.mkv *.avi *.mov)"
        )
        if file_path:
            self.path = file_path
            self.label.setText(f"📄 Selected File:\n{file_path}")

    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.path = folder_path
            self.label.setText(f"📁 Selected Folder:\n{folder_path}")

    def start(self):
        if not self.path:
            self.label.setText("⚠️ Please select a file or folder first!")
            return

        self.worker = Worker(
            self.path,
            int(self.chunk.value()),
            self.model.currentText()
        )

        self.worker.progress.connect(self.update_progress)
        self.worker.start()

    def update_progress(self, data):
        current = data.get("current", 0)
        total = data.get("total", 1) or 1
        percent = int((current / total) * 100)
        self.progress.setValue(percent)
        current_status = data.get("status", "")
        if current_status.lower() != "idle".lower():
            self.label.setText(data.get("status", ""))


# -----------------------
# RUN APP
# -----------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())