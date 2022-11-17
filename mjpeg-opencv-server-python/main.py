#!/usr/bin/python3
import socketserver
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
from PIL import Image
import numpy as np


REMOTE_MJPEG_URL = 'http://monsters.local:8000/?action=stream'
low_t = 100
high_t = 200

def increase_brightness(img, value=30):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    lim = 255 - value
    v[v > lim] = 255
    v[v <= lim] += value

    final_hsv = cv2.merge((h, s, v))
    img = cv2.cvtColor(final_hsv, cv2.COLOR_HSV2BGR)
    return img

def draw_lines(img, lines, color=[255, 0, 0], thickness=7):
    try:
        for line in lines:
            for x1, y1, x2, y2 in line:
                cv2.line(img, (x1, y1), (x2, y2), color, thickness)
    except:
        pass


def process(img):
    kernel_size = 5
    grayscale = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(grayscale, (kernel_size, kernel_size), 0)

    height = img.shape[0]
    width = img.shape[1] -10
    vertices = np.array([[(5,height),(5, 200), (100, 150), (300, 150),
                        (width, 200),(width,height)]], dtype=np.int32)

    edges = cv2.Canny(blur, low_t, high_t)
    mask = np.zeros_like(edges)
    cv2.fillPoly(mask, vertices, 255)
    masked_edges = cv2.bitwise_and(edges, edges, mask=mask)
    rho = 3
    theta = np.pi / 180
    threshold = 15
    min_line_len = 60
    max_line_gap = 50
    lines = cv2.HoughLinesP(masked_edges, rho, theta, threshold, np.array(
        []), minLineLength=min_line_len, maxLineGap=max_line_gap)
    result = img.copy()
    draw_lines(result, lines)

    return cv2.vconcat([
        cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR),
        cv2.bitwise_and(img, img, mask=mask),
        cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR),cv2.cvtColor(masked_edges, cv2.COLOR_GRAY2BGR), result])


class CamHandler(BaseHTTPRequestHandler):
    def __init__(self, request: bytes, client_address: tuple[str, int], server: socketserver.BaseServer):
        self.capture = cv2.VideoCapture(REMOTE_MJPEG_URL)
        self.to_exit = False
        super().__init__(request, client_address, server)

    def do_GET(self):
        if self.path.endswith('.mjpg'):
            self.send_response(200)
            self.send_header(
                'Content-type', 'multipart/x-mixed-replace; boundary=jpgboundary')
            self.end_headers()
            while not self.to_exit:
                rc, img = self.capture.read()
                img = process(img)
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
            self.wfile.write(str.encode(
                '<img src="http://localhost:8080/cam.mjpg"/>'))
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
