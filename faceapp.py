import sys
import os
import time
import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QSlider, QFrame,
    QComboBox, QFileDialog
)
from PyQt6.QtCore import QTimer, Qt, QUrl
from PyQt6.QtGui import QImage, QPixmap, QFont, QDesktopServices


class FaceAccessApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Accesso Biometrico")
        self.resize(1020, 900)

        # =====================================
        #  VARIABILI DI STATO
        # =====================================
        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

        self.last_frame = None
        self.prev_gray = None

        self.recording = False
        self.video_writer = None

        self.motion_enabled = False
        self.motion_start_time = None
        self.motion_threshold = 5.0
        self.motion_area_threshold = 5000
        self.max_motion_duration = 5  # secondi

        self.zoom = 1.0
        self.auto_zoom_face = False
        self.invert_colors = False
        self.face_zoom_margin = 0.45

        self.photo_dir = os.path.abspath("foto")
        self.video_dir = os.path.abspath("video")
        os.makedirs(self.photo_dir, exist_ok=True)
        os.makedirs(self.video_dir, exist_ok=True)

        self.face_colors = [
            (0, 255, 0), (255, 0, 0), (0, 0, 255),
            (0, 255, 255), (255, 255, 0), (255, 0, 255),
            (255, 255, 255), (0, 165, 255)
        ]
        self.face_color_index = 0

        # Face detector
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        self.init_ui()
        self.update_stats()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #0f1115;
                color: #e6e6e6;
            }
            QPushButton {
                background-color: #FF8000;
                border: 1px solid #2a2f3a;
                border-radius: 10px;
                padding: 10px 14px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #222632; }
            QPushButton:pressed { background-color: #2d3242; }
            QPushButton:checked {
                background-color: #0f2a33;
                border-color: #5bc0de;
                color: #5bc0de;
            }
            QComboBox {
                background-color: #1a1d24;
                border: 1px solid #2a2f3a;
                border-radius: 8px;
                padding: 6px;
            }
            QSlider::groove:horizontal {
                background: #2a2f3a;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #5bc0de;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)

        # ====================
        #   AREA CENTRALE
        # ====================
        center_layout = QHBoxLayout()
        center_layout.setSpacing(20)

        # Controlli sinistra
        left_panel = QVBoxLayout()
        left_panel.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 35)
        self.zoom_slider.setValue(10)
        self.zoom_slider.setFixedWidth(280)
        self.zoom_slider.valueChanged.connect(self.set_zoom)

        self.btn_auto_zoom = QPushButton("AUTO ZOOM FACE")
        self.btn_auto_zoom.setCheckable(True)
        self.btn_auto_zoom.clicked.connect(self.toggle_auto_zoom)

        self.btn_invert = QPushButton("INVERTI COLORI")
        self.btn_invert.setCheckable(True)
        self.btn_invert.clicked.connect(self.toggle_invert_colors)

        self.btn_color = QPushButton("CAMBIA COLORE RIQUADRO")
        self.btn_color.clicked.connect(self.cycle_face_color)

        self.btn_motion = QPushButton("Motion Record")
        self.btn_motion.setCheckable(True)
        self.btn_motion.clicked.connect(self.toggle_motion)

        for btn in (self.btn_auto_zoom, self.btn_invert, self.btn_color, self.btn_motion):
            btn.setStyleSheet("""
                QPushButton {
                    background:#141414; color:#8f9aa3;
                    border:1px solid #2f2f2f; border-radius:600px;
                    padding:10px 40px;
                }
                QPushButton:hover { background:#1c1c1c; }
                QPushButton:checked {
                    background:#0f2a33; color:#5bc0de; border-color:#5bc0de;
                }
            """)

        left_panel.addWidget(self.zoom_slider)
        left_panel.addWidget(self.btn_auto_zoom)
        left_panel.addWidget(self.btn_invert)
        left_panel.addWidget(self.btn_color)
        left_panel.addWidget(self.btn_motion)
        left_panel.addStretch()

        # Video area (centro-destra)
        self.video_label = QLabel("Camera inattiva")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #000;
                border: 1px solid #2a2f3a;
                border-radius: 24px;
                color: #aaa;
                font-size: 18px;
                font-weight: 600;
            }
        """)

        center_layout.addLayout(left_panel, 1)
        center_layout.addWidget(self.video_label, 3)

        main_layout.addLayout(center_layout)

        # ====================
        #   STATISTICHE
        # ====================
        stats_frame = QFrame()
        stats_frame.setFixedHeight(90)
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #151821;
                border: 1px solid #232836;
                border-radius: 16px;
            }
        """)
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(18, 10, 18, 10)
        stats_layout.setSpacing(30)

        self.lbl_photos  = QLabel("FOTO\n0")
        self.lbl_videos  = QLabel("VIDEO\n0")
        self.lbl_storage = QLabel("MEMORIA\n0 MB")

        for lbl in (self.lbl_photos, self.lbl_videos, self.lbl_storage):
            lbl.setStyleSheet("""
                QLabel {
                    background-color: #0f1115;
                    border-radius: 10px;
                    padding: 10px;
                    font-size: 14px;
                    font-weight: 600;
                }
            """)
            stats_layout.addWidget(lbl)

        main_layout.addWidget(stats_frame)

        # ====================
        #   PULSANTI AZIONI
        # ====================
        actions = QHBoxLayout()
        actions.setSpacing(12)

        self.btn_scan = QPushButton("Attiva Fotocamera")
        self.btn_photo = QPushButton("Scatta foto")
        self.btn_record = QPushButton("Registra video")

        self.btn_scan.clicked.connect(self.toggle_camera)
        self.btn_photo.clicked.connect(self.take_photo)
        self.btn_record.clicked.connect(self.toggle_recording)

        actions.addWidget(self.btn_scan)
        actions.addWidget(self.btn_photo)
        actions.addWidget(self.btn_record)
        main_layout.addLayout(actions)

        # ====================
        #   STRUMENTI
        # ====================
        tools = QHBoxLayout()
        tools.setSpacing(12)

        self.btn_photo_dir = QPushButton("Scegli cartella foto")
        self.btn_video_dir = QPushButton("Scegli cartella video")
        self.btn_open_photos = QPushButton("Apri foto salvate")
        self.btn_open_videos = QPushButton("Apri video salvati")

        self.btn_photo_dir.clicked.connect(self.choose_photo_dir)
        self.btn_video_dir.clicked.connect(self.choose_video_dir)
        self.btn_open_photos.clicked.connect(self.open_photos_folder)
        self.btn_open_videos.clicked.connect(self.open_videos_folder)

        self.camera_combo = QComboBox()
        self.camera_combo.setFixedWidth(180)
        self.refresh_cameras()

        tools.addWidget(self.btn_photo_dir)
        tools.addWidget(self.btn_video_dir)
        tools.addWidget(self.btn_open_photos)
        tools.addWidget(self.btn_open_videos)
        tools.addWidget(self.camera_combo)

        main_layout.addLayout(tools)

    # =====================================
    #   METODI DI SUPPORTO
    # =====================================

    def refresh_cameras(self):
        self.camera_combo.clear()
        cameras = self.detect_cameras()
        for idx in cameras:
            self.camera_combo.addItem(f"Camera {idx}", idx)
        if cameras:
            self.camera_combo.setCurrentIndex(0)

    def detect_cameras(self, max_index=8):
        cams = []
        for i in range(max_index):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cams.append(i)
                cap.release()
        return cams

    def toggle_camera(self):
        if self.cap is None or not self.cap.isOpened():
            idx = self.camera_combo.currentData()
            if idx is None:
                return
            self.cap = cv2.VideoCapture(idx)
            if not self.cap.isOpened():
                self.video_label.setText("Errore: impossibile aprire la camera")
                return
            self.timer.start(33)  # ~30 fps
            self.btn_scan.setText("Chiudi Fotocamera")
            self.video_label.setText("")
        else:
            self.timer.stop()
            self.cap.release()
            self.cap = None
            self.video_label.setText("Camera inattiva")
            self.btn_scan.setText("Attiva Fotocamera")

    def update_frame(self):
        if self.cap is None or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

        display_frame = frame.copy()

        # Motion detection
        if self.motion_enabled:
            if self.prev_gray is None:
                self.prev_gray = gray
            else:
                delta = cv2.absdiff(self.prev_gray, gray)
                thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
                thresh = cv2.dilate(thresh, None, iterations=2)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                motion_detected = any(cv2.contourArea(c) > self.motion_area_threshold for c in contours)

                if motion_detected and not self.recording:
                    self.start_motion_recording()

                self.prev_gray = gray

        # Auto-zoom viso
        if self.auto_zoom_face and len(faces) > 0:
            x, y, fw, fh = max(faces, key=lambda f: f[2]*f[3])
            margin = int(fw * self.face_zoom_margin)
            crop = display_frame[
                max(0, y-margin):y+fh+margin,
                max(0, x-margin):x+fw+margin
            ]
            if crop.size > 0:
                display_frame = cv2.resize(crop, (w, h))

        # Zoom manuale
        elif self.zoom > 1.0:
            nw, nh = int(w / self.zoom), int(h / self.zoom)
            x1 = (w - nw) // 2
            y1 = (h - nh) // 2
            cropped = display_frame[y1:y1+nh, x1:x1+nw]
            display_frame = cv2.resize(cropped, (w, h))

        # Disegna rettangoli visi
        color = self.face_colors[self.face_color_index]
        for (x, y, fw, fh) in faces:
            cv2.rectangle(display_frame, (x, y), (x+fw, y+fh), color, 2)

        # Indicatore registrazione
        if self.recording:
            cv2.circle(display_frame, (24, 24), 8, (0, 0, 255), -1)
            cv2.putText(display_frame, "REC", (40, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Inversione colori
        if self.invert_colors:
            display_frame = cv2.bitwise_not(display_frame)

        # Salva frame per foto e registrazione
        self.last_frame = display_frame.copy()

        if self.video_writer is not None:
            self.video_writer.write(display_frame)

        # Mostra
        self.show_frame(display_frame)

    def show_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qimg))

    def set_zoom(self, value):
        self.zoom = value / 10.0

    def toggle_auto_zoom(self):
        self.auto_zoom_face = self.btn_auto_zoom.isChecked()

    def toggle_invert_colors(self):
        self.invert_colors = self.btn_invert.isChecked()

    def cycle_face_color(self):
        self.face_color_index = (self.face_color_index + 1) % len(self.face_colors)

    def toggle_motion(self):
        self.motion_enabled = self.btn_motion.isChecked()
        if not self.motion_enabled:
            self.prev_gray = None

    def start_motion_recording(self):
        if self.cap is None or not self.cap.isOpened():
            return

        filename = os.path.join(self.video_dir, f"motion_{time.strftime('%Y%m%d_%H%M%S')}.avi")
        w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.video_writer = cv2.VideoWriter(
            filename, cv2.VideoWriter_fourcc(*"MJPG"), 30, (w, h)
        )
        self.recording = True
        self.motion_start_time = time.time()
        self.btn_record.setText("Stop (motion)")

    def toggle_recording(self):
        if self.cap is None or not self.cap.isOpened():
            return

        if not self.recording:
            filename = os.path.join(self.video_dir, f"video_{time.strftime('%Y%m%d_%H%M%S')}.avi")
            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            self.video_writer = cv2.VideoWriter(
                filename, cv2.VideoWriter_fourcc(*"MJPG"), 30, (w, h)
            )
            self.recording = True
            self.btn_record.setText("Stop video")
        else:
            self._stop_recording()

    def _stop_recording(self):
        self.recording = False
        self.btn_record.setText("Registra video")
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        self.update_stats()

    def take_photo(self):
        if self.last_frame is not None:
            path = os.path.join(self.photo_dir, f"foto_{time.strftime('%Y%m%d_%H%M%S')}.jpg")
            cv2.imwrite(path, self.last_frame)
            self.update_stats()

    def choose_photo_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Cartella foto", self.photo_dir)
        if folder:
            self.photo_dir = folder

    def choose_video_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Cartella video", self.video_dir)
        if folder:
            self.video_dir = folder

    def open_photos_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.photo_dir))

    def open_videos_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.video_dir))

    def update_stats(self):
        photo_count = len(os.listdir(self.photo_dir))
        video_count = len(os.listdir(self.video_dir))

        total_size = 0
        for folder in (self.photo_dir, self.video_dir):
            for fname in os.listdir(folder):
                total_size += os.path.getsize(os.path.join(folder, fname))

        size_mb = total_size / (1024 * 1024)

        self.lbl_photos.setText(f"FOTO\n{photo_count}")
        self.lbl_videos.setText(f"VIDEO\n{video_count}")
        self.lbl_storage.setText(f"MEMORIA\n{size_mb:.1f} MB")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = FaceAccessApp()
    window.show()
    sys.exit(app.exec())