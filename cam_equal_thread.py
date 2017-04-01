import numpy as np
import cv2, time, sys, threading
from abstract_thread import *



class CamEqualThread(AbstractThread):
    '''
    This thread is associated with (and dependent on) the CaptureThread object.

    It accesses and analyzes images from the CaptureThread object,
        and adjusts camera parameters via the CaptureThread object.
    '''
    def __init__(self, cap_thread_R, cap_thread_L, mediator):

        super(CamEqualThread, self).__init__()

        # Mediator emits signal to the gui object
        self.mediator = mediator

        self.cap_thread_R = cap_thread_R
        self.cap_thread_L = cap_thread_L

        self.tolerance = 2.5 # i.e. mean(imgR) +/- 2.5
        self.learn_rate = 0.2 # learning rate for adjusting gain

    def main(self):

        self.copy_parameters()

        self.tune_left_camera()

    def copy_parameters(self):
        '''
        Copy the the 'brightness', 'contrast', 'exposure' of the right camera to the left camera.
        '''

        parm_R = self.cap_thread_R.get_camera_parameters()
        parm_L = self.cap_thread_L.get_camera_parameters()

        for name in ['brightness', 'contrast', 'exposure']:
            if parm_R[name] != parm_L[name]:
                self.cap_thread_L.set_one_cam_parm(name=name, value=parm_R[name])

    def tune_left_camera(self):
        '''
        Adjust 'gain' of the left camera to make
            the average of the left image equals to the average of the right image, i.e. equal brightness.
        '''

        imgR = self.get_roi(self.cap_thread_R.get_image())
        imgL = self.get_roi(self.cap_thread_L.get_image())

        diff = np.average(imgR) - np.average(imgL)

        # Control the frequency of the main loop according to the difference.
        if abs(diff) > self.tolerance:
            time.sleep(1.0 / abs(diff)) # sleep time = the inverse of diff
        else:
            time.sleep(1)

        # Get the current gain value of the left camera
        gain_L = self.cap_thread_L.get_one_cam_parm(name='gain')

        # Dynamically adjust gain according to the difference
        if diff > self.tolerance:
            gain_L += (int(diff * self.learn_rate) + 1)

        elif diff < (-1 * self.tolerance):
            gain_L += (int(diff * self.learn_rate) - 1)

        else:
            return # Do nothing if it's within tolerated range

        self.cap_thread_L.set_one_cam_parm(name='gain', value=gain_L)

    def get_roi(self, img):

        rows, cols, channels = img.shape

        A = rows * 1 / 4
        B = rows * 3 / 4
        C = cols * 1 / 4
        D = cols * 3 / 4

        return img[A:B, C:D, :]

    def set_cap_threads(self, thread_R, thread_L):
        self.cap_thread_R = thread_R
        self.cap_thread_L = thread_L

