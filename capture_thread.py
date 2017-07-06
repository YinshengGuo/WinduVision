import numpy as np
import cv2, time, sys, threading, json
from root_constants import *
from abstract_thread import *



class CaptureThread(AbstractThread):

    def __init__(self, camera, mediator):
        '''
        which_cam: could be one of the three constants [CAM_R, CAM_L or CAM_E]
        '''
        super(CaptureThread, self).__init__()

        self.cam = camera
        self.which_cam = camera.get_which_cam()
        self.mediator = mediator
        self.connect_signals(mediator, ['set_info_text'])

        self.img = self.cam.read()

        self.t_series = [time.clock() for i in range(30)]

    def main(self):

        # Read the images from the cameras
        self.img = self.cam.read()

        self.emit_fps_info()

    def emit_fps_info(self):
        '''
        Emits real-time frame-rate info to the gui
        '''

        # Shift time series by one
        self.t_series[1:] = self.t_series[:-1]

        # Get the current time -> First in the series
        self.t_series[0] = time.clock()

        # Calculate frame rate
        rate = len(self.t_series) / (self.t_series[0] - self.t_series[-1])

        # Emit to different lines of text window...
        #     for different cameras
        line = {CAM_R: 0, CAM_L: 1, CAM_E: 2}

        which_cam = self.cam.get_which_cam() # CAM_R, CAM_L or CAM_E
        text = 'Capture thread {}: {} fps'.format(which_cam, rate)

        data = {'line': line[which_cam],
                'text': text}

        self.mediator.emit_signal( signal_name = 'set_info_text',
                                   arg = data )

    def get_image(self):
        return self.img

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

    def get_which_cam(self):
        return self.which_cam

