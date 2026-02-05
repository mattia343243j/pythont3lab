import sys
import cv2
import time
import os

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QComboBox
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap, QFont


class App(QWidget):
    def __init__(self):
        super().__init__()

        # ===== CARTELLE =====
        os.makedirs("foto", exist_ok=True)
        os.makedirs("video", exist_ok=True)

        # ===== STATO =====
        self.subscribed = False
        self.quality = "360p"

        # ===== PREZZI PER QUALITÀ =====
        self.prices = {
            "144p": "2,99 € / mese",
            "360p": "6,99 € / mese",
            "720p": "12,99 € / mese",
            "1080p": "19,99 € / mese",
            "4K": "26,99 € / mese"
        }

        self.last_frame = None
        self.captured_photo = None

        self.recording = False
        self.video_writer = None
        self.video_filename = None

        # ===== FINESTRA =====
        self.setWindowTitle("Accesso Biometrico v1.7")
        self.resize(920, 760)
        QApplication.instance().setFont(QFont("Segoe UI Variable", 10))

        # ===== CAMERA =====
        self.cap = None
        self.face = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        # ===== LAYOUT PRINCIPALE =====
        self.main_layout = QVBoxLayout(self)

        # ================= PAYWALL =================
        self.paywall = QWidget()
        pw = QVBoxLayout(self.paywall)
        pw.setSpacing(20)

        warn = QLabel("Accesso Premium")
        warn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warn.setStyleSheet("""
            font-size:26px;
            font-weight:700;
            color:#f2f2f2;
            letter-spacing:1px;
        """)

        self.price_label = QLabel(self.prices[self.quality])
        self.price_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.price_label.setStyleSheet("""
            font-size:22px;
            font-weight:600;
            color:#5bc0de;
        """)

        info = QLabel(
            "Sblocca tutte le funzionalità:\n"
            "• Scatto foto\n"
            "• Registrazione video\n"
            "• Accesso completo alla fotocamera"
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("""
            color:#cccccc;
            font-size:14px;
            line-height:1.6;
        """)

        future = QLabel("Qualità 8K disponibile nelle versioni successive")
        future.setAlignment(Qt.AlignmentFlag.AlignCenter)
        future.setStyleSheet("""
            font-size:12px;
            color:#888888;
            font-style: italic;
        """)

        qlabel = QLabel("Qualità video")
        qlabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.quality_box = QComboBox()
        self.quality_box.addItems(["144p", "360p", "720p", "1080p", "4K"])
        self.quality_box.setCurrentText(self.quality)
        self.quality_box.currentTextChanged.connect(self.set_quality)

        self.btn_sub = QPushButton("Sblocca Premium")
        self.btn_sub.setMinimumHeight(44)
        self.btn_sub.clicked.connect(self.enable_camera)

        btn_style = """
        QPushButton {
            background-color: #1e1e1e;
            color: #eaeaea;
            border: 1px solid #3a3a3a;
            border-radius: 8px;
            padding: 8px 14px;
            font-size: 13px;
        }
        QPushButton:hover {
            background-color: #2a2a2a;
            border-color: #5bc0de;
        }
        QPushButton:pressed {
            background-color: #151515;
        }
        """

        self.btn_sub.setStyleSheet(btn_style)

        pw.addStretch()
        pw.addWidget(warn)
        pw.addWidget(self.price_label)
        pw.addSpacing(8)
        pw.addWidget(info)
        pw.addWidget(future)
        pw.addSpacing(14)
        pw.addWidget(qlabel)
        pw.addWidget(self.quality_box, alignment=Qt.AlignmentFlag.AlignCenter)
        pw.addWidget(self.btn_sub, alignment=Qt.AlignmentFlag.AlignCenter)
        pw.addStretch()

        # ================= CAMERA =================
        self.camera_widget = QWidget()
        cam = QVBoxLayout(self.camera_widget)
        cam.setSpacing(12)

        self.title = QLabel("Verifica identità")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setFont(QFont("Segoe UI Variable", 22, QFont.Weight.DemiBold))
        self.title.setStyleSheet("color:#e6e6e6; letter-spacing:1px;")

        self.video = QLabel("Camera inattiva")
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setMinimumSize(640, 480)
        self.video.setStyleSheet("""
            background:#020202;
            border:1px solid #2f2f2f;
            border-radius:6px;
            color:#777;
        """)

        self.btn_scan = QPushButton(" Avvia scansione")
        self.btn_photo = QPushButton(" Scatta foto")
        self.btn_record = QPushButton(" Registra video")

        for b in (self.btn_scan, self.btn_photo, self.btn_record):
            b.setStyleSheet(btn_style)

        self.btn_scan.clicked.connect(self.toggle_camera)
        self.btn_photo.clicked.connect(self.take_photo)
        self.btn_record.clicked.connect(self.toggle_recording)

        row = QHBoxLayout()
        row.addWidget(self.btn_scan)
        row.addWidget(self.btn_photo)
        row.addWidget(self.btn_record)

        cam.addWidget(self.title)
        cam.addWidget(self.video)
        cam.addLayout(row)

        # ===== TIMER =====
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

        self.main_layout.addWidget(self.paywall)
        self.main_layout.addWidget(self.camera_widget)
        self.camera_widget.hide()

    # ================= LOGICA =================

    def set_quality(self, q):
        self.quality = q
        self.price_label.setText(self.prices[q])
        print(f"Qualità impostata: {q} → {self.prices[q]}")

    def enable_camera(self):
        self.subscribed = True
        self.paywall.hide()
        self.camera_widget.show()

    def toggle_camera(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(0)
            self.timer.start(30)
            self.btn_scan.setText(" Ferma scansione")
        else:
            self.timer.stop()
            self.cap.release()
            self.cap = None
            self.video.setText("Camera inattiva")
            self.btn_scan.setText(" Avvia scansione")

    def update_frame(self):
        if not self.cap:
            return

        ok, frame = self.cap.read()
        if not ok:
            return

        frame = cv2.flip(frame, 1)
        self.last_frame = frame.copy()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        for x, y, w, h in self.face.detectMultiScale(gray, 1.3, 5):
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        if self.recording:
            cv2.circle(frame, (20, 20), 6, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (32, 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            if self.video_writer:
                self.video_writer.write(frame)

        self.show_frame(frame)

    def show_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, c = rgb.shape
        img = QImage(rgb.data, w, h, c * w, QImage.Format.Format_RGB888)
        self.video.setPixmap(QPixmap.fromImage(img))

    def take_photo(self):
        if self.last_frame is None:
            return

        frame = self.last_frame.copy()
        ts = time.strftime("%d/%m/%Y %H:%M:%S")

        cv2.putText(frame, ts, (10, frame.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        filename = f"foto/foto_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
        cv2.imwrite(filename, frame)
        self.captured_photo = frame

        print(f"📸 Foto salvata: {filename}")

    def toggle_recording(self):
        if self.cap is None:
            return

        if not self.recording:
            filename = f"video/video_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            self.video_writer = cv2.VideoWriter(
                filename,
                cv2.VideoWriter_fourcc(*"mp4v"),
                30,
                (w, h)
            )

            self.video_filename = filename
            self.recording = True
            self.btn_record.setText(" Stop video")
        else:
            self.recording = False
            self.btn_record.setText(" Registra video")
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None

    def closeEvent(self, event):
        if self.cap:
            self.cap.release()
        if self.video_writer:
            self.video_writer.release()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = App()
    w.show()
    sys.exit(app.exec())
