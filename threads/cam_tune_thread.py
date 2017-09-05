import numpy as np
import cv2, time, sys, math, json
from abstract_thread import *



class CamTuneThread(AbstractThread):
    '''
    This thread is associated with (and dependent on) the CaptureThread object.

    It accesses and analyzes images from the CaptureThread object,
        and adjusts camera parameters via the CaptureThread object.
    '''

    def __init__(self, cap_thread_R, cap_thread_L, mediator):

        super(CamTuneThread, self).__init__()

        self.cap_thread_R = cap_thread_R
        self.cap_thread_L = cap_thread_L
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
        # The default sleep time is 1 second
        # The following methods decide whether to speed up or not
        self.sleep_time = 1

        # ------ RIGHT Camera ------ #
        # Check gain and exposure value of the right camera
        self.check_gain_exposure_R()
        # The main method to tune the right camera
        self.tune_right_camera()

        # ------ LEFT Camera ------ #
        # Copy and apply right camera parameters to the left camera
        self.copy_parameters()
        # The main method to equlaize the left camera to the right one
        self.tune_left_camera()

        time.sleep(self.sleep_time)

    # Procedural blocks in self.main()

    def check_gain_exposure_R(self):

        gain = self.cap_thread_R.get_one_cam_parm('gain')
        if gain < self.gain_min:
            self.set_cam(isRight=True, name='gain', value=self.gain_min)
        elif gain > self.gain_max:
            self.set_cam(isRight=True, name='gain', value=self.gain_max)

        exposure = self.cap_thread_R.get_one_cam_parm('exposure')
        if exposure < self.exposure_min:
            self.set_cam(isRight=True, name='exposure', value=self.exposure_min)
        elif exposure > self.exposure_max:
            self.set_cam(isRight=True, name='exposure', value=self.exposure_max)

    def tune_right_camera(self):

        gain = self.cap_thread_R.get_one_cam_parm('gain')
        exposure = self.cap_thread_R.get_one_cam_parm('exposure')
        img = self.get_roi(self.cap_thread_R.get_image())
        mean = np.average(img)

        self.emit_info_R(mean)

        diff = self.goal - mean

        # Do nothing if difference is within tolerated range, so return
        if abs(diff) <= self.tolerance:
            # Update the gui to display the correct values
            self.update_gui(isRight=True, name='gain', value=gain)
            self.update_gui(isRight=True, name='exposure', value=exposure)
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
        # Set gain and speed up to move on to the next iteration
        if gain >= gain_min and gain <= gain_max:
            self.set_cam(isRight=True, name='gain', value=gain)
            self.speed_up()
            return

        # ------ GAIN out of range  ------ #
        # ------ Adjusting EXPOSURE ------ #
        # If gain out of range, adjust exposure
        if gain > gain_max:
            exposure = exposure - 1 # exposure brighter
            # Update the gui to display the boundary (max) value
            self.update_gui(isRight=True, name='gain', value=gain_max)
        elif gain < gain_min:
            exposure = exposure + 1 # exposure darker
            # Update the gui to display the boundary (min) value
            self.update_gui(isRight=True, name='gain', value=gain_min)

        # ------ Set EXPOSURE ------ #
        # If the adjusted exposure is within the allowed range
        # Set exposure and speed up to move on to the next iteration
        if exposure >= expo_min and exposure <= expo_max:
            gain = (self.gain_min + self.gain_max) / 2 # Since gain is out of range, set it to the mid value
            self.set_cam(isRight=True, name='gain', value=gain)
            self.set_cam(isRight=True, name='exposure', value=exposure)
            time.sleep(0.1) # Takes a while before the exposure change takes effect
            self.speed_up()
            return

        # ------ EXPOSURE out of range ------ #
        # ------ Do nothing in the end ------ #
        # Nothing to do if the exposure is out of range, so slow down and return
        if exposure > expo_max:
            # Update the gui to display the boundary (max) value
            self.update_gui(isRight=True, name='exposure', value=expo_max)
        elif exposure < expo_min:
            # Update the gui to display the boundary (min) value
            self.update_gui(isRight=True, name='exposure', value=expo_min)

    def copy_parameters(self):
        '''
        Copy the the 'brightness', 'contrast', 'exposure' of the right camera to the left camera.
        '''

        parm_R = self.cap_thread_R.get_camera_parameters()
        parm_L = self.cap_thread_L.get_camera_parameters()

        for name in ['brightness', 'contrast', 'exposure']:
            if parm_R[name] != parm_L[name]:
                self.set_cam(isRight=False, name=name, value=parm_R[name])

    def tune_left_camera(self):
        '''
        Adjust 'gain' of the left camera to make
            the average of the left image equals to
            the average of the right image, i.e. equal brightness.
        '''

        # Get the current gain value of the left camera
        gain_L = self.cap_thread_L.get_one_cam_parm(name='gain')
        imgR = self.get_roi(self.cap_thread_R.get_image())
        imgL = self.get_roi(self.cap_thread_L.get_image())

        mean_R = np.average(imgR)
        mean_L = np.average(imgL)

        self.emit_info_L(mean_L)

        diff = mean_R - mean_L

        if abs(diff) <= self.tolerance:
            # Do nothing if it's within tolerated range, so return
            # Update the gui to display the correct value
            self.update_gui(isRight=False, name='gain', value=gain_L)
            return

        # Adjust gain_L according to the difference of image brightness
        if diff > self.tolerance:
            gain_L += (int(diff * self.learn_rate) + 1)
        elif diff < -self.tolerance:
            gain_L += (int(diff * self.learn_rate) - 1)

        # If gain_L is out of range (0, 127)
        #     then there's nothing to do, so return
        if gain_L < 0:
            # Update the gui to display the boundary (min) value
            self.update_gui(isRight=False, name='gain', value=0)
        elif gain_L > 127:
            # Update the gui to display the boundary (max) value
            self.update_gui(isRight=False, name='gain', value=127)

        # Or if gain_L is within range, i.e. 0 <= gain_L <= 127
        # Set gain_L and speed up
        else:
            self.set_cam(isRight=False, name='gain', value=gain_L)
            self.speed_up()

    # Lower-level methods used in the procedural blocks

    def speed_up(self):
        self.sleep_time = 0.05

    def emit_info_R(self, mean):

        text = 'Tuning camR image mean: {}'.format(mean)

        data = {'line': 4,
                'text': text}

        self.mediator.emit_signal( signal_name = 'set_info_text',
                                   arg = data )

    def emit_info_L(self, mean):

        text = 'Equalizing camL image mean: {}'.format(mean)

        data = {'line': 5,
                'text': text}

        self.mediator.emit_signal( signal_name = 'set_info_text',
                                   arg = data )

    def set_cam(self, isRight, name, value):
        if isRight:
            ret = self.cap_thread_R.set_one_cam_parm(name, value)
        else:
            ret = self.cap_thread_L.set_one_cam_parm(name, value)

        if ret:
            self.update_gui(isRight, name, value)

    def update_gui(self, isRight, name, value):
        if isRight:
            which_cam = self.cap_thread_R.get_which_cam()
        else:
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

    # Overriden methods

    def before_resuming(self):
        self.mediator.emit_signal(signal_name = 'auto_cam_resumed')
        return True

    def after_paused(self):
        self.mediator.emit_signal(signal_name = 'auto_cam_paused')
        return True

    # Public methods

    def set_cap_threads(self, thread_R, thread_L):
        self.cap_thread_R = thread_R
        self.cap_thread_L = thread_L

