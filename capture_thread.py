import numpy as np
import cv2, time, sys, threading, json
from constants import *
from abstract_thread import *



class CaptureThread(AbstractThread):

    def __init__(self, camera):
        '''
        which_cam: could be one of the three constants [CAM_R, CAM_L or CAM_E]
        '''
        super(CaptureThread, self).__init__()

        self.cam = camera
        self.img = self.cam.read()

    def main(self):

        # Read the images from the cameras
        self.img = self.cam.read()

    def set_camera_parameters(self, parameters):

        if self.cam:
            self.cam.set_parameters(parameters)

    def get_camera_parameters(self):

        if self.cam:
            return self.cam.get_parameters()

    def set_one_cam_parm(self, name, value):

        if self.cam:
            return self.cam.set_one_parm(name, value)

    def get_one_cam_parm(self, name):

        if self.cam:
            return self.cam.get_one_parm(name)

    def get_image(self):
        return self.img


