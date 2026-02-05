import sys
import cv2
import time

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QComboBox
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap, QFont


class App(QWidget):
    def __init__(self):
        super().__init__()

        self.subscribed = False
        self.quality = "360p"
        self.prev_time = 0.0
        self.last_frame = None
        self.captured_photo = None

        self.setWindowTitle("Accesso Biometrico v1.1")
        self.resize(900, 700)

        QApplication.instance().setFont(QFont("Segoe UI", 10))

        self.cap = None
        self.color = (255, 180, 0)

        self.face = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

# LAYOUT
        self.main_layout = QVBoxLayout(self)

# codici per pagare , SOLO layout 
        self.paywall = QWidget()
        paywall_layout = QVBoxLayout(self.paywall)
        paywall_layout.setSpacing(20)

        warning = QLabel("⚠️ È necessario abbonarsi a 2,99 € / mese")
        warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warning.setStyleSheet("font-size:18px;font-weight:600;color:#d9534f")

        info = QLabel("L'abbonamento sblocca la fotocamera e le funzioni avanzate.")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_sub = QPushButton("Abbonati")
        self.btn_sub.setMinimumHeight(40)
        self.btn_sub.setStyleSheet("""
            QPushButton {
                background:#f0ad4e;
                color:black;
                border-radius:6px;
                font-weight:600;
            }
            QPushButton:hover {
                background:#ec971f;
            }
        """)
        self.btn_sub.clicked.connect(self.enable_camera)

# codici per qualità della foto
        quality_label = QLabel("Qualità video")
        quality_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.quality_box = QComboBox()
        self.quality_box.addItems(["144p", "360p", "1080p", "4K"])
        self.quality_box.setCurrentText(self.quality)
        self.quality_box.currentTextChanged.connect(self.set_quality)

        paywall_layout.addStretch()
        paywall_layout.addWidget(warning)
        paywall_layout.addWidget(info)
        paywall_layout.addWidget(quality_label)
        paywall_layout.addWidget(self.quality_box, alignment=Qt.AlignmentFlag.AlignCenter)
        paywall_layout.addWidget(self.btn_sub, alignment=Qt.AlignmentFlag.AlignCenter)
        paywall_layout.addStretch()

 #  cmaerea
        self.camera_widget = QWidget()
        cam_layout = QVBoxLayout(self.camera_widget)
        cam_layout.setSpacing(15)

        self.title = QLabel("Verifica identità")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet("font-size:18px;font-weight:600;color:#5bc0de")

        self.video = QLabel("Camera inattiva")
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setMinimumSize(640, 480)
        self.video.setStyleSheet(
            "background:#050402;border:2px solid #5bc0de;color:#999"
        )

        self.btn_scan = QPushButton("Avvia scansione")
        self.btn_scan.setMinimumHeight(36)
        self.btn_scan.clicked.connect(self.toggle)

        self.btn_photo = QPushButton("📸 Scatta foto")
        self.btn_photo.setMinimumHeight(36)
        self.btn_photo.clicked.connect(self.take_photo)

        h = QHBoxLayout()
        h.addStretch()
        h.addWidget(self.btn_scan)
        h.addWidget(self.btn_photo)
        h.addStretch()

        cam_layout.addWidget(self.title)
        cam_layout.addWidget(self.video, alignment=Qt.AlignmentFlag.AlignCenter)
        cam_layout.addLayout(h)

# codici per il timer 
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
#  codici per pagare
        self.main_layout.addWidget(self.paywall)
        self.main_layout.addWidget(self.camera_widget)
        self.camera_widget.hide()
    
    def set_quality(self, q):
        self.quality = q

    def enable_camera(self):
        self.subscribed = True
        self.paywall.hide()
        self.camera_widget.show()

    def toggle(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(0)
            self.timer.start(30)
            self.btn_scan.setText("Interrompi scansione")
        else:
            self.timer.stop()
            self.cap.release()
            self.cap = None
            self.video.clear()
            self.video.setText("Camera inattiva")
            self.btn_scan.setText("Avvia scansione")

    def update_frame(self):
        ok, frame = self.cap.read()
        if not ok:
            return

        frame = cv2.flip(frame, 1)
        self.last_frame = frame.copy()
        
        current_time = time.perf_counter()
        fps = 1.0 / (current_time - self.prev_time) if self.prev_time else 0.0
        self.prev_time = current_time

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        for x, y, w, h in self.face.detectMultiScale(gray, 1.3, 5):
            cv2.rectangle(frame, (x, y), (x + w, y + h), self.color, 2)
            cv2.putText(
            frame,
            f"FPS: {fps:.1f} | Qualità: {self.quality}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, c = frame.shape
        img = QImage(frame.data, w, h, c * w, QImage.Format.Format_RGB888)
        self.video.setPixmap(QPixmap.fromImage(img))
def take_photo(self):
        if self.last_frame is None:
            return
        self.captured_photo = self.last_frame.copy()
        print("📸 Foto catturata (solo in memoria)")
def closeEvent(self, event):
        if self.cap:
            self.cap.release()
        event.accept()
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = App()
    w.show()
    sys.exit(app.exec())
