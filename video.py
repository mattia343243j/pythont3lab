import numpy as np
import cv2 as cv

# 🔹 carica il detector facciale
face_cascade = cv.CascadeClassifier(
    cv.data.haarcascades + "haarcascade_frontalface_default.xml"
)

cap = cv.VideoCapture(0)
if not cap.isOpened():
    print("Cannot open camera")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Can't receive frame (stream end?). Exiting ...")
        break

    frame_flipped = cv.flip(frame, 1)

    # 🔹 converti in scala di grigi
    gray = cv.cvtColor(frame_flipped, cv.COLOR_BGR2GRAY)

    # 🔹 rileva le facce
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(60, 60)
    )

    # 🔹 disegna il tracking
    for (x, y, w, h) in faces:
        cv.rectangle(
            frame_flipped,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            2
        )

    cv.imshow('frame', frame_flipped)

    if cv.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv.destroyAllWindows()
   