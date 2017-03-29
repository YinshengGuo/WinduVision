import numpy as np
import cv2, time, sys, threading, json
from constants import *



class CaptureThread(threading.Thread):

    def __init__(self, whichCam):
        '''
        whichCam: could be one of the three constants [CAM_R, CAM_L or CAM_E]
        '''
        super(CaptureThread, self).__init__()

        self.whichCam = whichCam

        self.__init__parms()

        # The customized single-camera object is...
        #     a low-level object of the CaptureThread object
        self.cam = SingleCamera(whichCam)
        self.img = self.cam.read()

    def __init__parms(self):
        # Parameters for looping, control and timing
        self.stopping = False
        self.pausing = False
        self.isPaused = False

    def run(self):

        # The main loop of this CaptureThread is NOT timed
        # It runs at the rate determined by a single camera hardware
        while not self.stopping:

            # Pausing the loop (or not)
            if self.pausing:
                self.isPaused = True
                time.sleep(0.1)
                continue
            else:
                self.isPaused = False

            # Read the images from the cameras
            self.img = self.cam.read()
            # print self.whichCam

        # Close camera hardware when the image-capturing main loop is done.
        self.cam.close()

    def pause(self):
        self.pausing = True
        # Wait until the main loop is really paused before completing this method call
        while not self.isPaused:
            time.sleep(0.1)
        return

    def resume(self):
        self.pausing = False
        # Wait until the main loop is really resumed before completing this method call
        while self.isPaused:
            time.sleep(0.1)
        return

    def stop(self):
        'Called to terminate the video thread.'

        # Shut off main loop in self.run()
        self.stopping = True

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



class SingleCamera(object):
    '''
    A customized camera API.

    One cv2.VideoCapture object is instantiated.
    If not successfully instantiated, then the VideoCapture object is None.
    '''

    def __init__(self, whichCam):
        '''
        whichCam: could be one of the three constants [CAM_R, CAM_L or CAM_E]
        '''
        super(SingleCamera, self).__init__()

        self.whichCam = whichCam

        self.__init__parameters()

        self.cap = cv2.VideoCapture(self.parm_vals['id'])

        if not self.cap.isOpened():
            self.cap = None

        self.__init__config()

        self.img_blank = cv2.imread('images/blank_' + self.whichCam + '.tif')

    def __init__parameters(self):

        self.parm_ids = {'width'        : 3   ,
                         'height'       : 4   ,
                         'brightness'   : 10  ,
                         'contrast'     : 11  ,
                         'saturation'   : 12  ,
                         'hue'          : 13  ,
                         'gain'         : 14  ,
                         'exposure'     : 15  ,
                         'white_balance': 17  ,
                         'focus'        : 28  }

        # Load camera parameters from the folder 'parameters/'
        filepath = 'parameters/' + self.whichCam + '.json'
        with open(filepath, 'r') as fh:
            self.parm_vals = json.loads(fh.read())



        # Define other operational parameters
        if self.whichCam == CAM_R:
            self.isCamManual = True
            self.rotation = 3

        elif self.whichCam == CAM_L:
            self.isCamManual = True
            self.rotation = 1

        elif self.whichCam == CAM_E:
            self.isCamManual = False
            self.rotation = 0

    def __init__config(self):

        if not self.isCamManual:
            return

        ids = self.parm_ids # dictionary
        vals = self.parm_vals # dictionary
        names = self.parm_ids.keys() # list

        if not self.cap is None:
            for name in names:
                self.cap.set( ids[name], vals[name] )

    def read(self):
        '''Return the properly rotated image. If cv2_cam is None than return a blank image.'''

        if not self.cap is None:
            _, img = self.cap.read()
            img = np.rot90(img, self.rotation)
        else:
            # Must insert a time delay to emulate camera harware delay
            # Otherwise the program will crash due to full-speed looping
            img = self.img_blank
            time.sleep(0.01)

        return img

    def set_parameters(self, parameters):

        for name, value in parameters.items():
            self.parm_vals[name] = value

        self.__init__config()

        # Load parameters from the .json file
        filepath = 'parameters/' + self.whichCam + '.json'
        with open(filepath, 'r') as fh:
            saved_parameters = json.loads(fh.read())

        # Update parameters
        for name in parameters.keys():
            saved_parameters[name] = parameters[name]

        # Save parameters to the .json file
        with open(filepath, 'w') as fh:
            json.dump(saved_parameters, fh)

    def get_parameters(self):

        return self.parm_vals

    def set_one_parm(self, name, value):
        #                            min   max   increment
        limits = {'brightness'    : (0   , 255 , 1),
                  'contrast'      : (0   , 255 , 1),
                  'saturation'    : (0   , 255 , 1),
                  'gain'          : (0   , 127 , 1),
                  'exposure'      : (-7  , -1  , 1),
                  'white_balance' : (3000, 6500, 1),
                  'focus'         : (0   , 255 , 5)}

        min, max, increment = limits[name]

        conditions = [ value < min            ,
                       value > max            ,
                       value % increment != 0 ]

        if any(conditions):
            return False

        self.parm_vals[name] = value
        self.__init__config()

        # Load parameters from the .json file
        filepath = 'parameters/' + self.whichCam + '.json'
        with open(filepath, 'r') as fh:
            saved_parameters = json.loads(fh.read())

        # Update the parameter
        saved_parameters[name] = value

        # Save parameters to the .json file
        with open(filepath, 'w') as fh:
            json.dump(saved_parameters, fh)

        return True

    def get_one_parm(self, name):

        return self.parm_vals[name]

    def close(self):
        if not self.cap is None:
            self.cap.release()


