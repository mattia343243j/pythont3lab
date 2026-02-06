import sys
import cv2
import time
import os

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QSlider, QFrame
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap, QFont


class App(QWidget):
    def __init__(self):
        super().__init__()

        # ===== FILE SYSTEM =====
        os.makedirs("foto", exist_ok=True)
        os.makedirs("video", exist_ok=True)

        # ===== STATO =====
        self.cap = None
        self.last_frame = None

        self.recording = False
        self.video_writer = None

        self.zoom = 1.0
        self.auto_zoom_face = False
        self.face_zoom_margin = 0.45

        # ===== FACE COLORS (BGR) =====
        self.face_colors = [
            (0, 255, 0),
            (255, 0, 0),
            (0, 0, 255),
            (0, 255, 255),
            (255, 255, 0),
            (255, 0, 255),
            (255, 255, 255),
            (0, 165, 255)
        ]
        self.face_color_index = 0

        # ===== WINDOW =====
        self.setWindowTitle("Accesso Biometrico")
        self.resize(1020, 900)
        QApplication.instance().setFont(QFont("Segoe UI Variable", 10))

        # ===== FACE DETECTOR =====
        self.face = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        # ===== MAIN LAYOUT =====
        main = QVBoxLayout(self)
        main.setSpacing(16)

        # ===== HEADER =====
        title = QLabel("Verifica identità")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI Variable", 15, QFont.Weight.Medium))
        title.setStyleSheet("color:#cfcfcf;")
        main.addWidget(title)

        # ===== ZOOM AREA =====
        zoom_box = QVBoxLayout()
        zoom_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 35)
        self.zoom_slider.setValue(10)
        self.zoom_slider.setFixedWidth(280)
        self.zoom_slider.valueChanged.connect(self.set_zoom)

        self.btn_auto_zoom = QPushButton("AUTO ZOOM FACE")
        self.btn_auto_zoom.setCheckable(True)
        self.btn_auto_zoom.clicked.connect(self.toggle_auto_zoom)

        self.btn_change_color = QPushButton("CAMBIA COLORE RIQUIDRO")
        self.btn_change_color.clicked.connect(self.cycle_face_color)

        for b in (self.btn_auto_zoom, self.btn_change_color):
            b.setStyleSheet("""
                QPushButton {
                    background:#141414;
                    color:#8f9aa3;
                    border:1px solid #2f2f2f;
                    border-radius:6px;
                    padding:8px 18px;
                }
                QPushButton:hover {
                    background:#1c1c1c;
                }
                QPushButton:checked {
                    background:#0f2a33;
                    color:#5bc0de;
                    border-color:#5bc0de;
                }
            """)

        zoom_box.addWidget(self.zoom_slider)
        zoom_box.addWidget(self.btn_auto_zoom)
        zoom_box.addWidget(self.btn_change_color)
        main.addLayout(zoom_box)

        # ===== VIDEO =====
        self.video = QLabel("Camera inattiva")
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setMinimumSize(760, 560)
        self.video.setStyleSheet("""
            background:#020202;
            border:2px solid #2a2a2a;
            border-radius:14px;
            color:#777;
        """)
        main.addWidget(self.video)

        # ===== CONTROLS =====
        controls = QHBoxLayout()
        controls.setSpacing(18)

        self.btn_scan = QPushButton("Avvia scansione")
        self.btn_photo = QPushButton("Scatta foto")
        self.btn_record = QPushButton("Registra video")

        for b in (self.btn_scan, self.btn_photo, self.btn_record):
            b.setStyleSheet("""
                QPushButton {
                    background:#242424;
                    color:#e6e6e6;
                    border:1px solid #333;
                    border-radius:6px;
                    padding:10px 24px;
                    font-size:13px;
                }
                QPushButton:hover {
                    background:#2f2f2f;
                }
            """)

        self.btn_scan.clicked.connect(self.toggle_camera)
        self.btn_photo.clicked.connect(self.take_photo)
        self.btn_record.clicked.connect(self.toggle_recording)

        controls.addWidget(self.btn_scan)
        controls.addWidget(self.btn_photo)
        controls.addWidget(self.btn_record)
        main.addLayout(controls)

        # ===== TIMER =====
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

    # ================= LOGICA =================

    def set_zoom(self, value):
        self.zoom = value / 10.0

    def cycle_face_color(self):
        self.face_color_index = (self.face_color_index + 1) % len(self.face_colors)

    def toggle_auto_zoom(self):
        self.auto_zoom_face = self.btn_auto_zoom.isChecked()

    def toggle_camera(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(0)
            self.timer.start(30)
            self.btn_scan.setText("Ferma scansione")
        else:
            self.timer.stop()
            self.cap.release()
            self.cap = None
            self.video.setText("Camera inattiva")
            self.btn_scan.setText("Avvia scansione")

    def update_frame(self):
        if self.cap is None or not self.cap.isOpened():
            return

        ok, frame = self.cap.read()
        if not ok:
            return

        frame = cv2.flip(frame, 1)

        h, w = frame.shape[:2]
        shift = int(h * 0.08)
        frame = frame[shift:, :]
        frame = cv2.resize(frame, (w, h))

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face.detectMultiScale(gray, 1.3, 5)

        if self.auto_zoom_face and len(faces) > 0:
            x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            m = int(fw * self.face_zoom_margin)
            crop = frame[max(0, y - m):y + fh + m, max(0, x - m):x + fw + m]
            if crop.size > 0:
                frame = cv2.resize(crop, (w, h))
        else:
            if self.zoom > 1.0:
                nw, nh = int(w / self.zoom), int(h / self.zoom)
                x1, y1 = (w - nw) // 2, (h - nh) // 2
                frame = cv2.resize(frame[y1:y1 + nh, x1:x1 + nw], (w, h))

            color = self.face_colors[self.face_color_index]
            for x, y, fw, fh in faces:
                cv2.rectangle(frame, (x, y), (x + fw, y + fh), color, 2)

        # ===== BOLLINO ROSSO REC =====
        if self.recording:
            cv2.circle(frame, (24, 24), 8, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (40, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 0, 255), 2)

            if self.video_writer:
                self.video_writer.write(frame)

        self.last_frame = frame.copy()
        self.show_frame(frame)

    def show_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, c = rgb.shape
        img = QImage(rgb.data, w, h, c * w, QImage.Format.Format_RGB888)
        self.video.setPixmap(QPixmap.fromImage(img))

    def take_photo(self):
        if self.last_frame is not None:
            cv2.imwrite(f"foto/foto_{time.strftime('%Y%m%d_%H%M%S')}.jpg", self.last_frame)

    def toggle_recording(self):
        if self.cap is None:
            return

        if not self.recording:
            filename = f"video/video_{time.strftime('%Y%m%d_%H%M%S')}.avi"

            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            self.video_writer = cv2.VideoWriter(
                filename,
                cv2.VideoWriter_fourcc(*"MJPG"),
                30,
                (w, h)
            )

            self.recording = True
            self.btn_record.setText("Stop video")

        else:
            self.recording = False
            self.btn_record.setText("Registra video")

            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = App()
    w.show()
    sys.exit(app.exec())
