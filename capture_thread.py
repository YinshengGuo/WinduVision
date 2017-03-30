import numpy as np
import cv2, time, sys, threading, json
from constants import *
from abstract_thread import *



class CaptureThread(AbstractThread):

    def __init__(self, which_cam):
        '''
        which_cam: could be one of the three constants [CAM_R, CAM_L or CAM_E]
        '''
        super(CaptureThread, self).__init__()

        self.which_cam = which_cam

        # The customized single-camera object is...
        #     a low-level object of the CaptureThread object
        self.cam = SingleCamera(which_cam)
        self.img = self.cam.read()

    def main(self):

        # Read the images from the cameras
        self.img = self.cam.read()

    def after_stopped(self):
        # Close camera hardware when the image-capturing main loop is done.
        self.cam.close()
        return True

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

    def __init__(self, which_cam):
        '''
        which_cam: could be one of the three constants [CAM_R, CAM_L or CAM_E]
        '''
        super(SingleCamera, self).__init__()

        self.which_cam = which_cam

        self.__init__parameters()

        self.cap = cv2.VideoCapture(self.parm_vals['id'])

        if not self.cap.isOpened():
            self.cap = None

        self.__init__config()

        self.img_blank = cv2.imread('images/blank_' + self.which_cam + '.tif')

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
        filepath = 'parameters/' + self.which_cam + '.json'
        with open(filepath, 'r') as fh:
            self.parm_vals = json.loads(fh.read())



        # Define other operational parameters
        if self.which_cam == CAM_R:
            self.rotation = 3

        elif self.which_cam == CAM_L:
            self.rotation = 1

        elif self.which_cam == CAM_E:
            self.rotation = 0

    def __init__config(self):

        ids = self.parm_ids # dictionary
        vals = self.parm_vals # dictionary
        names = self.parm_ids.keys() # list

        if not self.cap is None:
            for name in names:
                self.cap.set( ids[name], vals[name] )

    def read(self):
        '''Return the properly rotated image. If cv2_cam is None than return a blank image.'''

        if not self.cap is None:
            try:
                ret, img = self.cap.read()
                img = np.rot90(img, self.rotation)
            except:
                img = self.img_blank
                time.sleep(0.01)

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
        filepath = 'parameters/' + self.which_cam + '.json'
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
        #                             min   max   increment
        require = {'brightness'    : (0   , 255 , 1),
                   'contrast'      : (0   , 255 , 1),
                   'saturation'    : (0   , 255 , 1),
                   'gain'          : (0   , 127 , 1),
                   'exposure'      : (-7  , -1  , 1),
                   'white_balance' : (3000, 6500, 1),
                   'focus'         : (0   , 255 , 5)}

        min, max, increment = require[name]

        conditions = [ value < min            ,
                       value > max            ,
                       value % increment != 0 ]

        if any(conditions):
            return False

        self.parm_vals[name] = value
        self.__init__config()

        # Load parameters from the .json file
        filepath = 'parameters/' + self.which_cam + '.json'
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



