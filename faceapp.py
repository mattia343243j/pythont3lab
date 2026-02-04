import sys
import cv2

from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout
)
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage, QPixmap


class FaceApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Face App")
        self.resize(800, 600)

        # Webcam
        self.cap = None

        # Colori cerchio (BGR)
        self.colors = [
            (0, 255, 0),    # verde
            (0, 0, 255),    # rosso
            (255, 0, 0),    # blu
            (0, 255, 255),  # giallo
        ]
        self.color_index = 0

        # Face detector
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades +
            "haarcascade_frontalface_default.xml"
        )

        # UI
        self.video_label = QLabel()
        self.video_label.setFixedSize(640, 480)

        self.btn_camera = QPushButton("Apri fotocamera")
        self.btn_color = QPushButton("Cambia colore")

        self.btn_camera.clicked.connect(self.toggle_camera)
        self.btn_color.clicked.connect(self.change_color)

        buttons = QHBoxLayout()
        buttons.addWidget(self.btn_camera)
        buttons.addWidget(self.btn_color)

        layout = QVBoxLayout()
        layout.addWidget(self.video_label)
        layout.addLayout(buttons)

        self.setLayout(layout)

        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

    def toggle_camera(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(0)
            self.timer.start(30)
            self.btn_camera.setText("Chiudi fotocamera")
        else:
            self.timer.stop()
            self.cap.release()
            self.cap = None
            self.video_label.clear()
            self.btn_camera.setText("Apri fotocamera")

    def change_color(self):
        self.color_index = (self.color_index + 1) % len(self.colors)

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            center = (x + w // 2, y + h // 2)
            radius = w // 2
            cv2.circle(
                frame,
                center,
                radius,
                self.colors[self.color_index],
                3
            )

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(img))

    def closeEvent(self, event):
        if self.cap:
            self.cap.release()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FaceApp()
    window.show()
    sys.exit(app.exec())
