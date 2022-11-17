#!/usr/bin/python3
from control import Control
import socketserver
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
from PIL import Image
import numpy as np
import math


REMOTE_MJPEG_URL = 'http://monsters.local:8000/?action=stream'
REMOTE_CONTROL_URL = 'http://monsters.local:5000'
control = Control(REMOTE_CONTROL_URL)


def correct_img(img):
    kernel_size = 5
    grayscale = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(grayscale, (kernel_size, kernel_size), 0)


def detect_edges(img):
    low_t = 100
    high_t = 150
    return cv2.Canny(img, low_t, high_t)


def mask(img):
    height = img.shape[0]
    width = img.shape[1] - 10
    vertices = np.array([[(5, height), (5, 200), (100, 150), (300, 150),
                        (width, 200), (width, height)]], dtype=np.int32)
    mask = np.zeros_like(img)
    cv2.fillPoly(mask, vertices, 255)
    return cv2.bitwise_and(img, img, mask=mask)


def draw_lines(img, lines, color=[255, 0, 0], thickness=7):
    if lines is None:
        return
    for x1, y1, x2, y2 in lines:
        cv2.line(img, (x1, y1), (x2, y2), color, thickness)


def detect_lines(img):
    rho = 5
    theta = np.pi / 180
    threshold = 15
    min_line_len = 100
    max_line_gap = 50
    lines = cv2.HoughLinesP(img, rho, theta, threshold, np.array(
        []), minLineLength=min_line_len, maxLineGap=max_line_gap)
    left_line = None
    right_line = None
    if lines is not None:
        accepted_range_low = math.tan(math.pi/180*20)
        accepted_range_high = math.tan(math.pi/180*70)
        lines_collection = list(map(lambda x: (x[0],
                                               (x[0][1] - x[0][3]) /
                                               (x[0][0]-x[0][2]),
                                               math.sqrt(
            math.pow(x[0][1] - x[0][3], 2) + math.pow(x[0][0]-x[0][2], 2))), lines))
        lines_collection = list(filter(lambda x: (abs(x[1]) > accepted_range_low and
                                                  abs(x[1]) < accepted_range_high), lines_collection))
        left_lines = list(filter(lambda x: x[1] < 0, lines_collection))
        right_lines = list(filter(lambda x: x[1] > 0, lines_collection))
        if any(left_lines):
            left_line = max(left_lines, key=lambda x: x[2])
        if any(right_lines):
            right_line = min(right_lines, key=lambda x: x[2])

    if left_line is None:
        left_line = ((0, 0, 0, img.shape[0]), 0)
    if right_line is None:
        right_line = ((img.shape[1], 0, img.shape[1], img.shape[0]), 0)
    return [left_line[0], right_line[0]]


def line_intersection(line1, line2):
    xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
    ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]

    div = det(xdiff, ydiff)
    if div == 0:
        return None

    d = (det(*line1), det(*line2))
    x = det(d, xdiff) / div
    y = det(d, ydiff) / div
    return x, y


def act(lines):
    left_line = lines[0]
    right_line = lines[1]

    int = line_intersection(((left_line[0], left_line[1]), (left_line[2], left_line[3])), ((
        right_line[0], right_line[1]), (right_line[2], right_line[3])))
    if int is None:
        control.set_motors(0, 0, 0, 0)
        return

    if int[0] > 200:
        control.set_motors(0, 0, 2000, 2000)
        print("right")
    if int[0] < 200:
        control.set_motors(2000, 2000, 0, 0)
        print("left")


def process(img):

    corrected_img = correct_img(img)
    edges = detect_edges(corrected_img)
    masked_img = mask(edges)
    lines = detect_lines(masked_img)
    act(lines)
    result = img.copy()
    draw_lines(result, lines)

    return cv2.hconcat([
        cv2.cvtColor(corrected_img, cv2.COLOR_GRAY2BGR),
        cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR),
        cv2.cvtColor(masked_img, cv2.COLOR_GRAY2BGR),
        result])


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
    control.set_motors(0, 0, 0, 0)
    server.serve_forever()


if __name__ == '__main__':
    main()
