import numpy as np
import cv2, time, sys, threading, json
from constants import *



class SingleCamera(object):
    '''
    A customized camera API that directly operates one physical camera through cv2.VideoCapture().
    '''

    def __init__(self, which_cam):
        '''
        key: camera key among the constants (CAM_R, CAM_L or CAM_E)
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
            ret, img = self.cap.read()
            if ret:
                return np.rot90(img, self.rotation)

        time.sleep(0.01)
        # Must insert a time delay to emulate camera harware delay
        # Otherwise the program will crash due to full-speed looping
        return self.img_blank

    def set_parameters(self, parameters):

        for name, value in parameters.items():
            self.parm_vals[name] = value

        self.__init__config()

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

        if any(conditions) or self.cap is None:
            return False

        # Update parameter values in this object
        self.parm_vals[name] = value

        # Finally, set the hardware
        self.cap.set(self.parm_ids[name], value)

        return True

    def get_one_parm(self, name):
        return self.parm_vals[name]

    def get_which_cam(self):
        return self.which_cam

    def save_parameters(self):
        filepath = 'parameters/' + self.which_cam + '.json'
        with open(filepath, 'w') as fh:
            json.dump(self.parm_vals, fh)

    def close(self):
        self.save_parameters()
        if not self.cap is None:
            self.cap.release()



# class CameraParameters(object):
#     def __init__(self, which_cam):
#         self.which_cam = which_cam
#         # Load camera parameters from the folder 'parameters/'
#         filepath = 'parameters/' + self.which_cam + '.json'
#         with open(filepath, 'r') as fh:
#             self.parm_vals = json.loads(fh.read())
#
#     def get_vals(self):
#         return self.parm_vals
#
#     def set_vals(self, parameters):
#         for name in parameters.keys():
#             self.parm_vals[name] = parameters[name]
#
#     def write(self):
#         # Save parameters to the .json file
#         filepath = 'parameters/' + self.which_cam + '.json'
#         with open(filepath, 'w') as fh:
#             json.dump(self.parm_vals, fh)


