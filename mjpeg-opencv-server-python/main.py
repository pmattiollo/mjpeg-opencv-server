#!/usr/bin/python3
import socketserver
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
from PIL import Image

face_cascade = cv2.CascadeClassifier(r'haarcascade_frontalface_default.xml')

REMOTE_MJPEG_URL = 'http://raspberrypi.local:8000/?action=stream'


def face_detect(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    if len(faces) > 0:
        for (x, y, w, h) in faces:
            face_x = float(x + w / 2.0)
            face_y = float(y + h / 2.0)
            img = cv2.circle(img, (int(face_x), int(face_y)), int((w + h) / 4), (0, 255, 0), 2)
    return img


class CamHandler(BaseHTTPRequestHandler):
    def __init__(self, request: bytes, client_address: tuple[str, int], server: socketserver.BaseServer):
        self.capture = cv2.VideoCapture(REMOTE_MJPEG_URL)
        self.to_exit = False
        super().__init__(request, client_address, server)

    def do_GET(self):
        if self.path.endswith('.mjpg'):
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=jpgboundary')
            self.end_headers()
            while not self.to_exit:
                rc, img = self.capture.read()
                img = face_detect(img)
                if not rc:
                    continue
                imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                jpg = Image.fromarray(imgRGB)
                jpg_bytes = jpg.tobytes()
                self.wfile.write(str.encode("\r\n--jpgboundary\r\n"))
                self.send_header('Content-type', 'image/jpeg')
                self.send_header('Content-length', len(jpg_bytes))
                self.end_headers()
                jpg.save(self.wfile, 'JPEG')
                time.sleep(0.05)
            return
        if self.path.endswith('.html'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(str.encode('<html><head></head><body>'))
            self.wfile.write(str.encode('<img src="' + REMOTE_MJPEG_URL + '"/>'))
            self.wfile.write(str.encode('<img src="http://localhost:8080/cam.mjpg"/>'))
            self.wfile.write(str.encode('</body></html>'))
            return


def main():
    ip = '0.0.0.0'
    port = 8080
    server = ThreadingHTTPServer((ip, port), CamHandler)
    print("server started at " + ip + ':' + str(port))
    print('find video at http://127.0.0.1:8080/index.html')
    server.serve_forever()


if __name__ == '__main__':
    main()
