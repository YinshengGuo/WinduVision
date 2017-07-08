import numpy as np
import cv2, time, sys, threading, json
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
        self.connect_signals(mediator, 'set_info_text')

        self.cap_thread_R = cap_thread_R
        self.cap_thread_L = cap_thread_L

        self.__init__parameters()

    def __init__parameters(self):

        with open('parameters/auto_cam.json', 'r') as fh:
            parms = json.loads(fh.read())

        L = ['tolerance', # i.e. +/- tolerance
             'learn_rate'] # learning rate for adjusting gain

        for name in L:
            setattr(self, name, parms[name])

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
                self.set_camL(name=name, value=parm_R[name])

    def tune_left_camera(self):
        '''
        Adjust 'gain' of the left camera to make
            the average of the left image equals to the average of the right image, i.e. equal brightness.
        '''

        imgR = self.get_roi(self.cap_thread_R.get_image())
        imgL = self.get_roi(self.cap_thread_L.get_image())

        mean_R = np.average(imgR)
        mean_L = np.average(imgL)

        self.emit_info(mean_L)

        diff = mean_R - mean_L

        # Control the frequency of the main loop according to the difference.
        if abs(diff) > self.tolerance:
            time.sleep(0.1)
        else:
            time.sleep(1)

        # Get the current gain value of the left camera
        gain_L = self.cap_thread_L.get_one_cam_parm(name='gain')

        # Dynamically adjust gain according to the difference
        if abs(diff) <= self.tolerance:
            # Do nothing if it's within tolerated range
            # Update the gui to display the correct value
            self.update_gui(name='gain', value=gain_L)
            return

        elif diff > self.tolerance:
            gain_L += (int(diff * self.learn_rate) + 1)

        else: # diff < - self.tolerance
            gain_L += (int(diff * self.learn_rate) - 1)

        self.set_camL(name='gain', value=gain_L)

        # There's nothing to do if gain_L is out of range
        # So slow down the loop and return
        if gain_L < 0:
            # Update the gui to display the boundary (min) value
            self.update_gui(name='gain', value=0)
        elif gain_L > 127:
            # Update the gui to display the boundary (max) value
            self.update_gui(name='gain', value=127)
        time.sleep(1)
        return

    def emit_info(self, mean):

        text = 'Equalizing camL image mean: {}'.format(mean)

        data = {'line': 5,
                'text': text}

        self.mediator.emit_signal( signal_name = 'set_info_text',
                                   arg = data )

    def set_camL(self, name, value):
        ret = self.cap_thread_L.set_one_cam_parm(name, value)
        if ret:
            self.update_gui(name, value)

    def update_gui(self, name, value):
        which_cam = self.cap_thread_L.get_which_cam()

        data = {'which_cam': which_cam,
                'name'     : name     ,
                'value'    : value    }

        self.mediator.emit_signal('update_cam_parm', data)

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


