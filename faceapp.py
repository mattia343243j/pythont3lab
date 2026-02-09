from pdb import main
import sys
import cv2
import time
import os
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QComboBox

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QSlider, QFrame
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap, QFont




class App(QWidget):

    def detect_cameras(self, max_devices=5):
        cameras = []
        for i in range(max_devices):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cameras.append(i)
                cap.release()
        return cameras


    def __init__(self):
        super().__init__()

        # ===== CAMERA SELECTOR =====
        self.camera_selector = QComboBox()
        self.available_cameras = self.detect_cameras()

        for cam in self.available_cameras:
            self.camera_selector.addItem(f"Telecamera {cam}", cam)

        self.camera_selector.setFixedWidth(200)


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
        self.invert_colors = False
        self.face_zoom_margin = 0.45

        # ===== STATISTICHE =====
        self.photo_count = 0
        self.video_count = 0

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

        center = QHBoxLayout()
        center.setSpacing(20)


        

        # ===== ZOOM AREA (SINISTRA) =====
        zoom_box = QVBoxLayout()
        zoom_box.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 35)
        self.zoom_slider.setValue(10)
        self.zoom_slider.setFixedWidth(280)
        self.zoom_slider.valueChanged.connect(self.set_zoom)

        self.btn_auto_zoom = QPushButton("AUTO ZOOM FACE")
        self.btn_auto_zoom.setCheckable(True)
        self.btn_auto_zoom.clicked.connect(self.toggle_auto_zoom)

        self.btn_change_color = QPushButton("CAMBIA COLORE RIQUADRO")
        self.btn_change_color.clicked.connect(self.cycle_face_color)

        self.btn_invert_colors = QPushButton("INVERTI COLORI")
        self.btn_invert_colors.setCheckable(True)   
        self.btn_invert_colors.clicked.connect(self.toggle_invert_colors)     

        for b in (self.btn_auto_zoom, self.btn_change_color):
            b.setStyleSheet("""
        QPushButton {
            background:#141414;
            color:#8f9aa3;
            border:1px solid #2f2f2f;
            border-radius:600px;
            padding:10px 130px;
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
        zoom_box.addWidget(self.btn_invert_colors)
        zoom_box.addWidget(self.btn_change_color)
        zoom_box.addStretch()


        # ===== VIDEO (DESTRA) =====
        self.video = QLabel("Camera inattiva")
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setMinimumSize(10, 300)
        self.video.setStyleSheet("""
        background:#000000;
        border:2px solid #2a2a2a;
        border-radius:100px;
                                 
        color:#ffffff;
        """)

        # ===== CENTER LAYOUT (SINISTRA + DESTRA) =====
        center.addLayout(zoom_box, 1)     # sinistra: controlli
        center.addWidget(self.video, 3)   # destra: camera grande

        main.addLayout(center)
        



        # ===== STATS PANEL =====
        self.stats_frame = QFrame()
        self.stats_frame.setFixedHeight(90)
        self.stats_frame.setStyleSheet("""
            QFrame {
                background:#2a2a2a;
                border:1px solid #2a2a2a;
                border-radius:12px;
            }
        """)

        stats_layout = QHBoxLayout(self.stats_frame)
        stats_layout.setContentsMargins(18, 10, 18, 10)
        stats_layout.setSpacing(30)

        self.lbl_photos = QLabel("FOTO\n0")
        self.lbl_videos = QLabel("VIDEO\n0")
        self.lbl_storage = QLabel("MEMORIA\n0 MB")

        for lbl in (self.lbl_photos, self.lbl_videos, self.lbl_storage):
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("""
                QLabel {
                    color:#ffffff;
                    font-size:15px;
                    font-weight:600;
                              background:#1a1a1a;
                    border:1px solid #333;
                }
            """)

        stats_layout.addWidget(self.lbl_photos)
        stats_layout.addWidget(self.lbl_videos)
        stats_layout.addWidget(self.lbl_storage)
        main.addWidget(self.stats_frame)

        # ===== CONTROLS =====
        controls = QHBoxLayout()
        controls.setSpacing(18)

# selezione camera
        self.camera_selector = QComboBox()
        self.available_cameras = self.detect_cameras()

        for cam in self.available_cameras:
            self.camera_selector.addItem(f"Telecamera {cam}", cam)

        controls.addWidget(self.camera_selector)  # 👈 QUI

        # pulsanti
        self.btn_scan = QPushButton("Attiva Fotocamera")
        self.btn_photo = QPushButton("Scatta foto")
        self.btn_record = QPushButton("Registra video")
        self.btn_open_photos = QPushButton("Apri foto salvate")
        self.btn_open_videos = QPushButton("Apri video salvati")
        # colelgamenti pulsanti
        self.btn_scan.clicked.connect(self.toggle_camera)
        self.btn_photo.clicked.connect(self.take_photo)
        self.btn_record.clicked.connect(self.toggle_recording)
        self.btn_open_photos.clicked.connect(self.open_photos_folder)
        self.btn_open_videos.clicked.connect(self.open_video_folder)


        controls.addWidget(self.btn_scan)
        controls.addWidget(self.btn_photo)
        controls.addWidget(self.btn_record)
        controls.addWidget(self.btn_open_photos)
        controls.addWidget(self.btn_open_videos)

        main.addLayout(controls)


        # ===== TIMER =====
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

        self.update_stats()

    # ================= LOGICA =================

    def update_stats(self):
        foto_files = os.listdir("foto")
        video_files = os.listdir("video")

        self.photo_count = len(foto_files)
        self.video_count = len(video_files)

        size = 0                 
        for folder in ("foto", "video"):
            for f in os.listdir(folder):
                size += os.path.getsize(os.path.join(folder, f))

        size_mb = size / (1024 * 1024)

        self.lbl_photos.setText(f"FOTO\n{self.photo_count}")
        self.lbl_videos.setText(f"VIDEO\n{self.video_count}")
        self.lbl_storage.setText(f"MEMORIA\n{size_mb:.2f} MB")

    def set_zoom(self, value):
        self.zoom = value / 10.0

    def open_photos_folder(self):
        folder_path = os.path.abspath("foto")
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
    def open_video_folder(self):
        folder_path = os.path.abspath("video")
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))

    def cycle_face_color(self):
        self.face_color_index = (self.face_color_index + 1) % len(self.face_colors)

    def toggle_auto_zoom(self):
        self.auto_zoom_face = self.btn_auto_zoom.isChecked()
    
    def toggle_invert_colors(self):
        self.invert_colors = self.btn_invert_colors.isChecked()    

    def toggle_camera(self):
        if self.cap is None:
            cam_index = self.camera_selector.currentData()
            self.cap = cv2.VideoCapture(cam_index)
            self.timer.start(30)
            self.btn_scan.setText("Chiudi Fotocamera")
        else:
            self.timer.stop()
            self.cap.release()
            self.cap = None
            self.video.setText("Camera inattiva")
            self.btn_scan.setText("Attiva Fotocamera")


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

        if self.recording:
            cv2.circle(frame, (24, 24), 8, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (40, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 0, 255), 2)

            if self.video_writer:
                self.video_writer.write(frame)
        if self.invert_colors:
            frame = cv2.bitwise_not(frame)

        
        self.last_frame = frame.copy()
        self.show_frame(frame)

    def show_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, c = rgb.shape
        img = QImage(rgb.data, w, h, c * w, QImage.Format.Format_RGB888)
        self.video.setPixmap(QPixmap.fromImage(img))

    def take_photo(self):
        if self.last_frame is not None:
            cv2.imwrite(
                f"foto/foto_{time.strftime('%Y%m%d_%H%M%S')}.jpg",
                self.last_frame
            )
            self.update_stats()

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

            self.update_stats()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = App()
    w.show()
    sys.exit(app.exec())
