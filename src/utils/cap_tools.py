import cv2
from cvzone import FPS

def cap_available():
    return list(filter(lambda x:cv2.VideoCapture(x).isOpened(),range(10)))
