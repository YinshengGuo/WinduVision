import numpy as np
import cv2, time, sys, math, json
from abstract_thread import *



class CamTuneThread(AbstractThread):

    def __init__(self, cap_thread, mediator):

        super(CamTuneThread, self).__init__()

        self.cap_thread = cap_thread
        self.mediator = mediator

        self.connect_signals(mediator = mediator,
                             signal_names = ['auto_cam_resumed',
                                             'auto_cam_paused' ,
                                             'set_info_text'   ,
                                             'update_cam_parm' ])

        self.__init__parameters()

    def __init__parameters(self):

        with open('parameters/auto_cam.json', 'r') as fh:
            parms = json.loads(fh.read())

        L = ['goal',
             'tolerance', # i.e. goal +/- tolerance
             'learn_rate', # learning rate for adjusting gain
             'gain_max',
             'gain_min',
             'exposure_max',
             'exposure_min']

        for name in L:
            setattr(self, name, parms[name])

    def main(self):

        self.check_gain()
        self.check_exposure()

        gain = self.cap_thread.get_one_cam_parm('gain')
        exposure = self.cap_thread.get_one_cam_parm('exposure')
        img = self.get_roi(self.cap_thread.get_image())
        mean = np.average(img)

        self.emit_info(mean)

        diff = self.goal - mean

        # Do nothing if difference is within tolerated range, so slow down and return
        if abs(diff) <= self.tolerance:
            # Update the gui to display the correct values
            self.update_gui(name='gain', value=gain)
            self.update_gui(name='exposure', value=exposure)
            time.sleep(1)
            return

        gain_min = self.gain_min
        gain_max = self.gain_max
        expo_min = self.exposure_min
        expo_max = self.exposure_max

        # ------ Adjusting GAIN ------ #
        # Dynamically adjust gain according to the difference
        if diff > self.tolerance:
            gain += (int(diff * self.learn_rate) + 1)
        elif diff < (-1 * self.tolerance):
            gain += (int(diff * self.learn_rate) - 1)

        # ------ Set GAIN ------ #
        # If the adjusted gain is within the allowed range
        # Set gain and quickly move on to the next iteration
        if gain >= gain_min and gain <= gain_max:
            self.set_cam(name='gain', value=gain)
            time.sleep(0.05) # Speed up for the next iteration
            return

        # ------ GAIN out of range  ------ #
        # ------ Adjusting EXPOSURE ------ #
        # If gain out of range, adjust exposure
        if gain > gain_max:
            exposure = exposure - 1 # exposure brighter
            # Update the gui to display the boundary (max) value
            self.update_gui(name='gain', value=gain_max)
        elif gain < gain_min:
            exposure = exposure + 1 # exposure darker
            # Update the gui to display the boundary (min) value
            self.update_gui(name='gain', value=gain_min)

        # ------ Set EXPOSURE ------ #
        if exposure >= expo_min and exposure <= expo_max:
            gain = (self.gain_min + self.gain_max) / 2 # Since gain is out of range, set it to the mid value
            self.set_cam(name='gain', value=gain)
            self.set_cam(name='exposure', value=exposure)
            time.sleep(0.1) # Takes a while before the exposure change takes effect
            return

        # ------ EXPOSURE out of range ------ #
        # ------ Do nothing in the end ------ #
        # Nothing to do if the exposure is out of range, so slow down and return
        if exposure > expo_max:
            # Update the gui to display the boundary (max) value
            self.update_gui(name='exposure', value=expo_max)
        elif exposure < expo_min:
            # Update the gui to display the boundary (min) value
            self.update_gui(name='exposure', value=expo_min)
        time.sleep(1)

    def check_gain(self):

        gain = self.cap_thread.get_one_cam_parm('gain')

        if gain < self.gain_min:
            self.set_cam(name='gain', value=self.gain_min)
        elif gain > self.gain_max:
            self.set_cam(name='gain', value=self.gain_max)

    def check_exposure(self):

        exposure = self.cap_thread.get_one_cam_parm('exposure')

        if exposure < self.exposure_min:
            self.set_cam(name='exposure', value=self.exposure_min)
        elif exposure > self.exposure_max:
            self.set_cam(name='exposure', value=self.exposure_max)

    def emit_info(self, mean):

        text = 'Tuning camR image mean: {}'.format(mean)

        data = {'line': 4,
                'text': text}

        self.mediator.emit_signal( signal_name = 'set_info_text',
                                   arg = data )

    def set_cam(self, name, value):
        ret = self.cap_thread.set_one_cam_parm(name, value)
        if ret:
            self.update_gui(name, value)

    def update_gui(self, name, value):
        which_cam = self.cap_thread.get_which_cam()

        data = {'which_cam': which_cam,
                'name'     : name     ,
                'value'    : value    }

        self.mediator.emit_signal('update_cam_parm', data)

    def before_resuming(self):
        self.mediator.emit_signal(signal_name = 'auto_cam_resumed')
        return True

    def after_paused(self):
        self.mediator.emit_signal(signal_name = 'auto_cam_paused')
        return True

    def get_roi(self, img):

        rows, cols, channels = img.shape

        A = rows * 1 / 4
        B = rows * 3 / 4
        C = cols * 1 / 4
        D = cols * 3 / 4

        return img[A:B, C:D, :]

    def set_cap_thread(self, thread):
        self.cap_thread = thread


