import sys, cv2
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap, QFont

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Accesso Biometrico")
        self.resize(820, 620)

        QApplication.instance().setFont(QFont("Segoe UI", 10))

        self.cap = None
        self.color = (255, 180, 0)  
        self.face = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        self.title = QLabel("Verifica identità")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("font-size:18px;font-weight:600;color:#ffa500")

        self.video = QLabel("In attesa della scansione")
        self.video.setAlignment(Qt.AlignCenter)
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
        v.addWidget(self.video, alignment=Qt.AlignCenter)
        v.addLayout(h)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)

    def toggle(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(0)
            self.timer.start(30)
            self.btn_scan.setText("Interrompi scansione")
        else:
            self.timer.stop()
            self.cap.release()
            self.cap = None
            self.video.setPixmap(QPixmap())
            self.video.setText("In attesa della scansione")
            self.btn_scan.setText("Avvia scansione")

    def update(self):
        ok, f = self.cap.read()
        if not ok: return
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        for x,y,w,h in self.face.detectMultiScale(g,1.3,5):
            cv2.circle(f,(x+w//2,y+h//2),w//2,self.color,2)
        f = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
        h,w,c = f.shape
        self.video.setPixmap(QPixmap.fromImage(QImage(f.data,w,h,c*w,QImage.Format_RGB888)))

    def closeEvent(self,e):
        if self.cap: self.cap.release()
        e.accept()

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        w = App()
        w.show()
        sys.exit(app.exec())
    except Exception as e:
        print("ERRORE:", e)
        input("Premi INVIO per uscire...")

