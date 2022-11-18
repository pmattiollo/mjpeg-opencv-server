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
    img_transf = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    img_transf[:, :, 2] = cv2.equalizeHist(img_transf[:, :, 2])
    # mask of green (36,25,25) ~ (86, 255,255)
    # mask = cv2.inRange(hsv, (36, 25, 25), (86, 255,255))
    # mask = cv2.inRange(img_transf, (0, 0, 36), (255, 255,200))

    # slice the green
    # imask = mask>0
    # green = np.zeros_like(img, np.uint8)
    # green[imask] = img[imask]
    # img = green
    img = cv2.cvtColor(img_transf, cv2.COLOR_HSV2BGR)
    # brightness = 50
    # contrast = 70
    # img = np.int16(img)
    # img = img * (contrast/127+1) - contrast + brightness
    # img = np.clip(img, 0, 255)
    # img = np.uint8(img)
    kernel_size = 5
    grayscale = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.medianBlur(grayscale, kernel_size, 0)

    return img


def detect_edges(img):
    low_t = 180
    high_t = 220
    edges = cv2.Canny(img, low_t, high_t)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    dilated = cv2.dilate(edges, kernel, iterations=2)
    dilated = cv2.erode(dilated, kernel, iterations=2)

    return dilated


def mask(img):
    height = img.shape[0]
    width = img.shape[1] - 10
    vertices = np.array([[(-400, height), (100, 150), (300, 150),
                         (width+400, height)]], dtype=np.int32)
    mask = np.zeros_like(img)
    cv2.fillPoly(mask, vertices, 255)
    return cv2.bitwise_and(img, img, mask=mask)


def draw_lines(img, lines, color=[255, 0, 0], thickness=7):
    if lines is None:
        return
    for x1, y1, x2, y2 in lines:
        cv2.line(img, (x1, y1), (x2, y2), color, thickness)


def detect_lines(img):
    rho = 2
    theta = np.pi / 180
    threshold = 100
    min_line_len = 60
    max_line_gap = 20
    lines = cv2.HoughLinesP(img, rho, theta, threshold, np.array(
        []), minLineLength=min_line_len, maxLineGap=max_line_gap)
    left_line = None
    right_line = None
    if lines is not None:
        accepted_range_low = math.tan(math.pi/180*10)
        accepted_range_high = math.tan(math.pi/180*80)
        lines_collection = list(map(lambda x: (x[0],
                                               (x[0][1] - x[0][3]) /
                                               (x[0][0]-x[0][2]),
                                               math.sqrt(
            math.pow(x[0][1] - x[0][3], 2) + math.pow(x[0][0]-x[0][2], 2))), lines))
        lines_collection = list(filter(lambda x: (abs(x[1]) > accepted_range_low and
                                                  abs(x[1]) < accepted_range_high), lines_collection))
        left_lines = list(filter(lambda x: x[1] < 0 and (
            x[0][0] < 200 or x[0][2] < 200), lines_collection))
        right_lines = list(filter(lambda x:  x[1] > 0 and (
            x[0][0] > 200 or x[0][2] > 200), lines_collection))
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
    # sensor = control.get_sensor_data()
    # print(sensor)
    int = line_intersection(((left_line[0], left_line[1]), (left_line[2], left_line[3])), ((
        right_line[0], right_line[1]), (right_line[2], right_line[3])))
    if int is None:
        control.set_motors(0, 0, 0, 0)
        print("stop")
        return

    if int[0] < 150:
        control.set_motors(-700, -700, 700, 700)
        print("left")
    elif int[0] > 250:
        control.set_motors(700, 700, -700, -700)
        print("right")
    else:
        control.set_motors(1000, 1000, 1000, 1000)
        print("straight")


def process(img):

    corrected_img = correct_img(img)
    edges = detect_edges(corrected_img)
    masked_img = mask(edges)
    lines = detect_lines(masked_img)
    act(lines)
    draw_lines(img, lines)

    return cv2.hconcat([
        cv2.cvtColor(corrected_img, cv2.COLOR_GRAY2BGR),
        cv2.cvtColor(masked_img, cv2.COLOR_GRAY2BGR),
        img])


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
