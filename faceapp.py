import sys
import cv2
import time

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap, QFont


class App(QWidget):
    def __init__(self):
        super().__init__()

        # FPS
        self.prev_time = 0.0

        self.setWindowTitle("Accesso Biometrico")
        self.resize(820, 620)

        QApplication.instance().setFont(QFont("Segoe UI", 10))

        self.cap = None
        self.color = (255, 180, 0)

        self.face = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        self.title = QLabel("Verifica identità")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet(
            "font-size:18px;font-weight:600;color:#ffa500"
        )

        self.video = QLabel("In attesa della scansione")
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setFixedSize(640, 480)
        self.video.setStyleSheet(
            "background:#050402;border:2px solid #4aa3df;color:#8b8c7a"
        )

        self.btn_scan = QPushButton("Avvia scansione")
        self.btn_scan.setMinimumHeight(36)
        self.btn_scan.setStyleSheet("""
            QPushButton {
                background:#4aa3df;
                color:white;
                border-radius:6px;
            }
            QPushButton:hover {
                background:#3b8cc4;
            }
        """)

        self.btn_scan.clicked.connect(self.toggle)

        h = QHBoxLayout()
        h.addStretch()
        h.addWidget(self.btn_scan)
        h.addStretch()

        v = QVBoxLayout(self)
        v.setSpacing(15)
        v.addWidget(self.title)
        v.addWidget(self.video, alignment=Qt.AlignmentFlag.AlignCenter)
        v.addLayout(h)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

    def toggle(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(0)
            self.timer.start(30)  # ~33 FPS
            self.btn_scan.setText("Interrompi scansione")
        else:
            self.timer.stop()
            self.cap.release()
            self.cap = None
            self.video.clear()
            self.video.setText("In attesa della scansione")
            self.btn_scan.setText("Avvia scansione")

    def update_frame(self):
        ok, frame = self.cap.read()
        if not ok:
            return

        # 🔄 flip per togliere effetto specchio
        frame = cv2.flip(frame, 1)

        # 🔢 FPS
        current_time = time.perf_counter()
        fps = 1.0 / (current_time - self.prev_time) if self.prev_time else 0.0
        self.prev_time = current_time

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        for x, y, w, h in self.face.detectMultiScale(gray, 1.3, 5):
            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                self.color,
                2
            )

        # 🖊️ scritta FPS
        cv2.putText(
            frame,
            f"FPS: {fps:.1f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
            cv2.LINE_AA
        )

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, c = frame.shape

        img = QImage(
            frame.data,
            w,
            h,
            c * w,
            QImage.Format.Format_RGB888
        )

        self.video.setPixmap(QPixmap.fromImage(img))

    def closeEvent(self, event):
        if self.cap:
            self.cap.release()
        event.accept()


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        w = App()
        w.show()
        sys.exit(app.exec())
    except Exception as e:
        print("ERRORE:", e)
        input("Premi INVIO per uscire...")
