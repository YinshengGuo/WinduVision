import numpy as np
import cv2, time, sys, threading
from abstract_thread import *



class CamEqualThread(AbstractThread):
    '''
    This thread is associated with (and dependent on) the CaptureThread object.

    It accesses and analyzes images from the CaptureThread object,
        and adjusts camera parameters via the CaptureThread object.
    '''
    def __init__(self, capture_thread_R, capture_thread_L, mediator):

        super(CamEqualThread, self).__init__(pause_at_start=True)

        # Mediator emits signal to the gui object
        self.mediator = mediator

        self.capture_thread_R = capture_thread_R
        self.capture_thread_L = capture_thread_L

        self.connect_signals(mediator = self.mediator,
                             signal_names = ['camera_equalized'])

    def main(self):

        # --- Section of camera tuning --- #
        result1 = self.tune_right_camera(iter=20)



        # --- Section of camera equalization --- #
        self.copy_parameters()

        result2 = self.tune_left_camera(iter=20)



        # --- Showing results to GUI --- #
        results = result1 + '\n' + result2 + '\n'

        self.mediator.emit_signal(signal_name = 'camera_equalized',
                                          arg = results           )

        self.pausing = True

    def tune_right_camera(self, iter):
        '''
        Tune the right camera: exposure and gain
        '''

        goal = 128 # goal of image lighting



        # Set brightness, contrast, gain to default before tuning exposure
        default = {'brightness'   : 100 ,
                   'contrast'     : 50  ,
                   'gain'         : 64  }

        for name, value in default.items():
            self.capture_thread_R.set_one_cam_parm(name=name, value=value)

        # Try exposure values from -2 to -5
        min_diff = 255
        for exp in xrange(-2, -6, -1):

            self.capture_thread_R.set_one_cam_parm(name='exposure', value=exp)
            time.sleep(0.5) # Wait for the camera configuration to take effect. Setting exposure takes longer time.

            imgR = self.capture_thread_R.get_image()
            imgR = self.get_roi(imgR)

            diff = goal - np.average(imgR)

            # Get the exposure which gives the min difference
            if abs(diff) < min_diff:
                min_diff = abs(diff)
                exposure = exp

        self.capture_thread_R.set_one_cam_parm(name='exposure', value=exposure)
        time.sleep(0.5) # Wait for the camera configuration to take effect. Setting exposure takes longer time.



        # Tune gain value until the intensity difference <= 1
        gain = default['gain']
        for i in xrange(iter):

            imgR = self.capture_thread_R.get_image()
            imgR = self.get_roi(imgR)

            diff = goal - np.average(imgR)

            # Dynamically adjust gain according to the difference
            if diff > 1:
                gain += (int(diff/2) + 1)
            elif diff < -1:
                gain += (int(diff/2) - 1)
            else:
                break # Condition satisfied, break the loop

            ret = self.capture_thread_R.set_one_cam_parm(name='gain', value=gain)
            time.sleep(0.1) # Wait for the camera configuration to take effect.

            # If not able to set the camera, meaning that the parameter is out of bound,
            #     break the loop
            if not ret:
                break



        # Return tuning result summary
        result = 'Tune camR: exposure={}, gain={}, iter={}, diff={}'.format(str(exposure), str(gain), str(i), str(diff))
        return result

    def copy_parameters(self):
        '''
        Copy the right camera parameters to the left camera.
        '''

        parm_R = self.capture_thread_R.get_camera_parameters()

        camL_id = self.capture_thread_L.get_one_cam_parm(name='id')
        parm_R['id'] = camL_id # except the id of the left cam

        self.capture_thread_L.set_camera_parameters(parm_R)

    def tune_left_camera(self, iter):
        '''
        Adjust 'gain' of the left camera until
            the average of the left image equals to the average of the right image, i.e. equal brightness.
        '''

        for i in xrange(iter):

            # Get the current gain value of the left camera
            gain = self.capture_thread_L.get_one_cam_parm(name='gain')

            imgR = self.capture_thread_R.get_image()
            imgL = self.capture_thread_L.get_image()

            bright_R = np.average(self.get_roi(imgR))
            bright_L = np.average(self.get_roi(imgL))

            diff = bright_R - bright_L

            # Dynamically adjust gain according to the difference
            if diff > 1:
                gain += (int(diff/2) + 1)
            elif diff < -1:
                gain += (int(diff/2) - 1)
            else:
                break # Condition satisfied, break the loop

            ret = self.capture_thread_L.set_one_cam_parm(name='gain', value=gain)
            time.sleep(0.1) # Wait for the camera configuration to take effect.

            # If not able to set the camera, meaning that the parameter is out of bound,
            #     break the loop
            if not ret:
                break

        result = 'Tune camL: gain={}, iter={}, diff={}'.format(str(gain), str(i), str(diff))

        return result

    def get_roi(self, img):

        rows, cols, channels = img.shape

        A = rows * 1 / 4
        B = rows * 3 / 4
        C = cols * 1 / 4
        D = cols * 3 / 4

        return img[A:B, C:D, :]


