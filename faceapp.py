import sys
import os
import time
import cv2
import requests       
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QSlider, QFrame,
    QComboBox, QFileDialog
)
from PyQt6.QtCore import QTimer, Qt, QUrl
from PyQt6.QtGui import QImage, QPixmap, QFont, QDesktopServices
class FaceAccessApp(QWidget):



    def open_log_file(self):
        log_path = os.path.join(os.getcwd(), "registro_eventi.txt")

    
        if not os.path.exists(log_path):
            with open(log_path, "w", encoding="utf-8"):
                pass

        QDesktopServices.openUrl(QUrl.fromLocalFile(log_path))


    def write_log(self, message):
        log_path = os.path.join(os.getcwd(), "registro_eventi.txt")

        now = time.strftime("%d/%m/%Y %H:%M:%S")

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{now} - {self.city_name} - {message}\n")

    def __init__(self):
        super().__init__()

        # ── Variabili di geolocalizzazione via IP ───────────────
        self.city_name = "Località sconosciuta"
        self.last_geo_update = 0
        self.geo_update_interval = 60  # aggiorna ogni 60 secondi

        self.setWindowTitle("Accesso Biometrico")
        self.resize(1020, 900)

        # Variabili di stato
        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

        self.last_frame = None
        self.prev_gray = None

        self.recording = False
        self.motion_recording = False
        self.video_writer = None
        self.last_motion_time = 0.0

        self.motion_enabled = False
        self.motion_threshold = 25
        self.motion_area_threshold = 5000
        self.max_motion_duration = 5.0  # secondi di inattività prima di fermare

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

        if self.face_cascade.empty():
            print("errore , non va ")

        self.init_ui()
        self.update_stats()

    def update_city_from_ip(self):
       

        try:
            r = requests.get("http://ip-api.com/json/", timeout=6)
            r.raise_for_status()
            data = r.json()

            if data.get("status") == "success":
                city = data.get("city") or ""
                region = data.get("regionName") or ""
                country = data.get("country") or ""

                parts = [p for p in [city, region, country] if p and p.strip()]
                if parts:
                    self.city_name = ", ".join(parts)
                else:
                    self.city_name = "Località sconosciuta"
            else:
                self.city_name = "Località sconosciuta"

        except Exception:
            self.city_name = "Località sconosciuta"   # fallisce silenziosamente

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


        # ── AREA CENTRALE ───────────────────────────────────────
        center_layout = QHBoxLayout()
        center_layout.setSpacing(20)

        # Pannello sinistro comandi
        left_panel = QVBoxLayout()
        left_panel.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 40)
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
        self.btn_motion.clicked.connect(self.toggle_motion_detection)

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

        # Area video
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

        # ── STATISTICHE ──────────────────────────────────────────
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

        # ── PULSANTI AZIONI ─────────────────────────────────────
        actions = QHBoxLayout()
        actions.setSpacing(12)

        self.btn_scan   = QPushButton("Attiva Fotocamera")
        self.btn_photo  = QPushButton("Scatta foto")
        self.btn_record = QPushButton("Registra video")

        self.btn_scan.clicked.connect(self.toggle_camera)
        self.btn_photo.clicked.connect(self.take_photo)
        self.btn_record.clicked.connect(self.toggle_manual_recording)

        actions.addWidget(self.btn_scan)
        actions.addWidget(self.btn_photo)
        actions.addWidget(self.btn_record)
        main_layout.addLayout(actions)

        # ── STRUMENTI ────────────────────────────────────────────
        tools = QHBoxLayout()
        tools.setSpacing(12)

        self.btn_photo_dir   = QPushButton("Scegli cartella foto")
        self.btn_video_dir   = QPushButton("Scegli cartella video")
        self.btn_open_photos = QPushButton("Apri foto salvate")
        self.btn_open_videos = QPushButton("Apri video salvati")
        self.btn_open_log = QPushButton("Apri registro eventi") 


        self.btn_photo_dir.clicked.connect(self.choose_photo_dir)
        self.btn_video_dir.clicked.connect(self.choose_video_dir)
        self.btn_open_photos.clicked.connect(self.open_photos_folder)
        self.btn_open_videos.clicked.connect(self.open_videos_folder)
        self.btn_open_log.clicked.connect(self.open_log_file)

        self.camera_combo = QComboBox()
        self.camera_combo.setFixedWidth(180)
        self.refresh_cameras()

        tools.addWidget(self.btn_photo_dir)
        tools.addWidget(self.btn_video_dir)
        tools.addWidget(self.btn_open_photos)
        tools.addWidget(self.btn_open_videos)
        tools.addWidget(self.btn_open_log)
        tools.addWidget(self.camera_combo)

        main_layout.addLayout(tools)

    

    def refresh_cameras(self):
        self.camera_combo.clear()
        cameras = self.detect_cameras()
        for idx in cameras:
            self.camera_combo.addItem(f"Camera {idx}", idx)
        if cameras:
            self.camera_combo.setCurrentIndex(0)

    def detect_cameras(self, max_index=10):
        cams = []
        for i in range(max_index):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cams.append(i)
            cap.release()
        return cams

    def toggle_camera(self):
        if self.cap is not None and self.cap.isOpened():
            self.timer.stop()
            self.cap.release()
            self.cap = None
            self.video_label.setText("Camera inattiva")
            self.btn_scan.setText("Attiva Fotocamera")
            if self.recording:
                self._stop_recording()
        else:
            idx = self.camera_combo.currentData()
            if idx is None:
                self.video_label.setText("Nessuna camera selezionata")
                return

            self.cap = cv2.VideoCapture(idx)
            if not self.cap.isOpened():
                self.video_label.setText("Errore: impossibile aprire la camera")
                return

            self.timer.start(33)  # ~30 fps
            self.btn_scan.setText("Chiudi Fotocamera")
            self.video_label.setText("")

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

        # ── Motion Detection ────────────────────────────────
        if self.motion_enabled:
            if self.prev_gray is None:
                self.prev_gray = gray
            else:
                delta = cv2.absdiff(self.prev_gray, gray)
                thresh = cv2.threshold(delta, self.motion_threshold, 255, cv2.THRESH_BINARY)[1]
                thresh = cv2.dilate(thresh, None, iterations=2)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                motion_detected = any(cv2.contourArea(c) > self.motion_area_threshold for c in contours)

                current_time = time.time()

                if motion_detected:
                    self.last_motion_time = current_time

                if not self.recording and motion_detected:
                    self.start_recording(motion_mode=True)

                if self.motion_recording and (current_time - self.last_motion_time > self.max_motion_duration):
                    self._stop_recording()

            self.prev_gray = gray.copy()

        # ── Auto-zoom viso ──────────────────────────────────
        if self.auto_zoom_face and len(faces) > 0:
            x, y, fw, fh = max(faces, key=lambda f: f[2]*f[3])
            margin = int(fw * self.face_zoom_margin)
            crop = display_frame[
                max(0, y-margin):y+fh+margin,
                max(0, x-margin):x+fw+margin
            ]
            if crop.size > 0:
                display_frame = cv2.resize(crop, (w, h), interpolation=cv2.INTER_LINEAR)

        # ── Zoom manuale ────────────────────────────────────
        elif self.zoom > 1.0:
            nw, nh = int(w / self.zoom), int(h / self.zoom)
            x1 = (w - nw) // 2
            y1 = (h - nh) // 2
            cropped = display_frame[y1:y1+nh, x1:x1+nw]
            if cropped.size > 0:
                display_frame = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

        # ── Disegna rettangoli visi ─────────────────────────
        color = self.face_colors[self.face_color_index]
        for (x, y, fw, fh) in faces:
            cv2.rectangle(display_frame, (x, y), (x+fw, y+fh), color, 2)

        # ── Indicatore registrazione ────────────────────────
        if self.recording:
            cv2.circle(display_frame, (24, 24), 8, (0, 0, 255), -1)
            cv2.putText(display_frame, "REC", (40, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # ── Inversione colori ───────────────────────────────
        if self.invert_colors:
            display_frame = cv2.bitwise_not(display_frame)

        # ── Aggiornamento località via IP ───────────────────
        current_time = time.time()
        if current_time - self.last_geo_update > self.geo_update_interval:
            self.update_city_from_ip()
            self.last_geo_update = current_time

        # ── Overlay testo ───────────────────────────────────
        now = time.strftime("%d/%m/%Y %H:%M:%S")

        cv2.putText(display_frame, now,
                    (20, h - 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255),
                    2)

        cv2.putText(display_frame, f"📍 {self.city_name}",
                    (20, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255),
                    2)

        self.last_frame = display_frame.copy()

        if self.video_writer is not None and self.recording:
            self.video_writer.write(display_frame)

        self.show_frame(display_frame)

    def show_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        self.video_label.setPixmap(pixmap.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))

    def set_zoom(self, value):
        self.zoom = value / 10.0

    def toggle_auto_zoom(self):
        self.auto_zoom_face = self.btn_auto_zoom.isChecked()

    def toggle_invert_colors(self):
        self.invert_colors = self.btn_invert.isChecked()

    def cycle_face_color(self):
        self.face_color_index = (self.face_color_index + 1) % len(self.face_colors)

    def toggle_motion_detection(self):
        self.motion_enabled = self.btn_motion.isChecked()
        if not self.motion_enabled:
            self.prev_gray = None
            if self.motion_recording:
                self._stop_recording()

    def start_recording(self, motion_mode=False):

        if self.cap is None or not self.cap.isOpened():
            return

        prefix = "motion" if motion_mode else "video"
        filename = os.path.join(
            self.video_dir,
            f"{prefix}_{time.strftime('%Y%m%d_%H%M%S')}.avi"
        )

        w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        self.video_writer = cv2.VideoWriter(filename, fourcc, 25.0, (w, h))

        if not self.video_writer.isOpened():
            print("Errore: impossibile creare il VideoWriter")
            return

        self.recording = True
        self.write_log(f" Inizio registrazione: {os.path.basename(filename)}")

        self.motion_recording = motion_mode
        self.last_motion_time = time.time()

        if motion_mode:
            self.btn_record.setText("Stop (motion)")
        else:
            self.btn_record.setText("Stop video")

    def toggle_manual_recording(self):
        if self.cap is None or not self.cap.isOpened():
            return

        if not self.recording:
            self.start_recording(motion_mode=False)
        else:
            self._stop_recording()

    def _stop_recording(self):
        self.recording = False
        self.motion_recording = False
        self.last_motion_time = 0.0
        self.write_log(" Registrazione terminata")


        self.btn_record.setText("Registra video")

        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None

        self.update_stats()

    def take_photo(self):
        if self.last_frame is not None:
            filename = f"foto_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
            path = os.path.join(self.photo_dir, filename)
            cv2.imwrite(path, self.last_frame)

            self.write_log(f" Foto scattata: {filename}")

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
        photo_count = len([f for f in os.listdir(self.photo_dir) if f.lower().endswith(('.jpg','.jpeg','.png'))])
        video_count = len([f for f in os.listdir(self.video_dir) if f.lower().endswith(('.avi','.mp4'))])

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