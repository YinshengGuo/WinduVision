import numpy as np
import cv2, time, sys, math
from abstract_thread import *



class CamTuneThread(AbstractThread):

    def __init__(self, cap_thread, mediator):

        super(CamTuneThread, self).__init__()

        self.cap_thread = cap_thread
        self.mediator = mediator

        self.connect_signals(mediator = self.mediator,
                             signal_names = ['auto_cam_resumed', 'auto_cam_paused'])

        self.goal = 100.0
        self.tolerance = 2.5 # i.e. 100 +/- 2.5

        self.learn_rate = 0.1 # learning rate for adjusting gain

        self.gain_max = 100
        self.gain_min = 0

        self.exposure_max = -1
        self.exposure_min = -7

    def main(self):

        gain = self.cap_thread.get_one_cam_parm('gain')
        exposure = self.cap_thread.get_one_cam_parm('exposure')

        set = self.cap_thread.set_one_cam_parm

        if gain < self.gain_min:
            set(name='gain', value=self.gain_min)
        elif gain > self.gain_max:
            set(name='gain', value=self.gain_max)

        if exposure < self.exposure_min:
            set(name='exposure', value=self.exposure_min)
        if exposure > self.exposure_max:
            set(name='exposure', value=self.exposure_max)



        img = self.get_roi(self.cap_thread.get_image())
        diff = self.goal - np.average(img)

        # Control the frequency of the main loop according to the difference.
        if abs(diff) > self.tolerance:
            time.sleep(1.0 / abs(diff)) # sleep time = the inverse of diff
        else:
            time.sleep(1)



        # print 'gain={}, exposure={}, mean={}, diff={}'.format(gain, exposure, np.average(img), diff)

        # Dynamically adjust gain according to the difference
        if diff > self.tolerance:
            gain += (int(diff * self.learn_rate) + 1)

        elif diff < (-1 * self.tolerance):
            gain += (int(diff * self.learn_rate) - 1)

        else:
            return # Do nothing if it's within tolerated range



        # If gain out of range, adjust exposure without adjusting gain
        if gain > self.gain_max:
            exposure = exposure - 1
            if exposure >= self.exposure_min:
                set(name='exposure', value=exposure)
            return

        elif gain < self.gain_min:
            exposure = exposure + 1
            if exposure <= self.exposure_max:
                set(name='exposure', value=exposure)
            return

        else:
            set(name='gain', value=gain)

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

