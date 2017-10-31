import numpy as np
import cv2, time, sys, threading, json
from constants import *
from abstract_thread import *
from stereo import Stereo as stereo


class ProcessThread(AbstractThread):

    def __init__(self, cap_thread_R, cap_thread_L, mediator):
        super(ProcessThread, self).__init__()

        self.cap_thread_R = cap_thread_R
        self.cap_thread_L = cap_thread_L
        self.mediator = mediator

        self.__init__parms()
        self.set_fps(30.0)

        self.connect_signals(mediator, ['display_image', 'set_info_text'])

    def __init__parms(self):
        # Parameters for image processing
        self.offset_x, self.offset_y = 0, 0

        self.zoom = 1.0

        with open('parameters/gui.json', 'r') as fh:
            gui_parms = json.loads(fh.read())
        w = gui_parms['default_width']
        h = gui_parms['default_height']
        self.set_display_size(w, h)

        self.set_resize_matrix()



        # Parameters for stereo depth map
        self.ndisparities = 32 # Must be divisible by 16
        self.SADWindowSize = 31 # Must be odd, be within 5..255 and be not larger than image width or height



        # Parameters for control and timing
        self.computingDepth = False
        self.t_series = [time.time() for i in range(30)]

    def set_display_size(self, width, height):
        '''
        Define the dimension of self.img_display, which is the terminal image to be displayed in the GUI.
        '''

        self.display_width = width
        self.display_height = height

        # Define the dimensions of:
        #     self.imgR_proc  --- processed R image to be accessed externally
        #     self.imgL_proc  ---           L image
        #     self.img_display --- display image to be emitted to the GUI object
        rows, cols = height, width
        self.imgR_proc   = np.zeros((rows, cols/2, 3), np.uint8)
        self.imgL_proc   = np.zeros((rows, cols/2, 3), np.uint8)
        self.img_display = np.zeros((rows, cols  , 3), np.uint8)

    def set_resize_matrix(self):
        '''
        Define the transformation matrix for the image processing pipeline.
        '''

        img = self.cap_thread_R.get_image()
        img_height, img_width, _ = img.shape

        display_height, display_width = self.display_height, self.display_width

        # The height-to-width ratio
        ratio_img = float(img_height) / img_width
        ratio_display = float(display_height) / (display_width / 2)

        # The base scale factor is the ratio of display size / image size,
        #     which scales the image to the size of the display.
        if ratio_img > ratio_display:
            base_scale = float(display_height) / img_height # Height is the limiting factor
        else:
            base_scale = float(display_width/2) / img_width # Width is the limiting factor

        # The actual scale factor is the product of the base scale factor and the zoom factor.
        scale_x = base_scale * self.zoom
        scale_y = base_scale * self.zoom



        # The translation distance for centering
        #     = half of the difference between
        #         the screen size and the zoomed image size
        #    ( (     display size     ) - (     zoomed image size   ) ) / 2
        tx = ( (display_width / 2) - (img_width  * scale_x) ) / 2
        ty = ( (display_height   ) - (img_height * scale_y) ) / 2



        # Putting everything together into a matrix
        Sx = scale_x
        Sy = scale_y

        Off_x = self.offset_x
        Off_y = self.offset_y

        # For the right image, it's only scaling and centering
        self.resize_matrix_R = np.float32([ [Sx, 0 , tx] ,
                                            [0 , Sy, ty] ])

        # For the left image, in addition to scaling and centering, the offset is also applied.
        self.resize_matrix_L = np.float32([ [Sx, 0 , Sx*Off_x + tx] ,
                                            [0 , Sy, Sy*Off_y + ty] ])

    def main(self):
        '''
        There are three major steps for the image processing pipeline,
        with some additional steps in between.

        ( ) Check image dimensions.
        (1) Eliminate offset of the left image.
        (2) Resize and translate to place each image at the center of both sides of the view.
        ( ) Compute depth map (optional).
        (3) Combine images.
        '''

        # Get the images from self.capture_thread
        self.imgR_0 = self.cap_thread_R.get_image() # The suffix '_0' means raw input image
        self.imgL_0 = self.cap_thread_L.get_image()

        # Quick check on the image dimensions
        # If not matching, skip all following steps
        if not self.imgR_0.shape == self.imgL_0.shape:
            self.mediator.emit_signal( signal_name = 'set_info_text',
                                       arg = 'Image dimensions not identical.' )
            time.sleep(0.1)
            return

        # (1) Eliminate offset of the left image.
        # (2) Resize and translate to place each image at the center of both sides of the view.
        rows, cols = self.display_height, self.display_width / 2 # Output image dimension

        self.imgR_1 = cv2.warpAffine(self.imgR_0, self.resize_matrix_R, (cols, rows))
        self.imgL_1 = cv2.warpAffine(self.imgL_0, self.resize_matrix_L, (cols, rows))

        # Update processed images for external access
        self.imgR_proc[:,:,:] = self.imgR_1[:,:,:]
        self.imgL_proc[:,:,:] = self.imgL_1[:,:,:]

        # Compute stereo depth map (optional)
        if self.computingDepth:
            self.imgL_1 = self.compute_depth()

        # (3) Combine images.
        h, w = self.display_height, self.display_width
        self.img_display[:, 0:(w/2), :] = self.imgL_1
        self.img_display[:, (w/2):w, :] = self.imgR_1

        self.mediator.emit_signal( signal_name = 'display_image',
                                   arg = self.img_display )

        self.emit_fps_info()

    def compute_depth(self):
        imgL = stereo.compute_depth(self.imgR_1, self.imgL_1, self.ndisparities, self.SADWindowSize)
        return imgL

    def emit_fps_info(self):
        '''
        Emits real-time frame-rate info to the gui
        '''

        # Shift time series by one
        self.t_series[1:] = self.t_series[:-1]

        # Get the current time -> First in the series
        self.t_series[0] = time.time()

        # Calculate frame rate
        rate = len(self.t_series) / (self.t_series[0] - self.t_series[-1])

        data = {'line': 3,
                'text': 'Active process thread: {} fps'.format(rate)}

        self.mediator.emit_signal( signal_name = 'set_info_text',
                                   arg = data )

    # Below are public methods for higher-level objects

    def set_offset(self, offset_x, offset_y):

        x_limit, y_limit = 100, 100

        if abs(offset_x) > x_limit or abs(offset_y) > y_limit:
            self.offset_x, self.offset_y = 0, 0

        else:
            self.offset_x, self.offset_y = offset_x, offset_y

        self.set_resize_matrix()

    def detect_offset(self):
        '''
        1) Read right and left images from the cameras.
        2) Use correlation function to calculate the offset.
        '''

        imgR = self.cap_thread_R.get_image()
        imgL = self.cap_thread_L.get_image()

        imgR = cv2.cvtColor(imgR, cv2.COLOR_BGR2GRAY)
        imgL = cv2.cvtColor(imgL, cv2.COLOR_BGR2GRAY)

        if not imgR.shape == imgL.shape:
            return

        # Define ROI of the left image
        row, col = imgL.shape
        a = int(row*0.25)
        b = int(row*0.75)
        c = int(col*0.25)
        d = int(col*0.75)
        roiL = np.float32( imgL[a:b, c:d] )

        mat = cv2.matchTemplate(image  = np.float32(imgR)   ,
                                templ  = roiL               ,
                                method = cv2.TM_CCORR_NORMED)

        # Vertical alignment, should always be done
        y_max = cv2.minMaxLoc(mat)[3][1]
        offset_y = y_max - row / 4

        # Horizontal alignment, for infinitely far objects
        x_max = cv2.minMaxLoc(mat)[3][0]
        offset_x = x_max - col / 4

        return offset_x, offset_y

    def zoom_in(self):
        if self.zoom * 1.01 < 2.0:
            self.zoom = self.zoom * 1.01
            self.set_resize_matrix()

    def zoom_out(self):
        if self.zoom / 1.01 > 0.5:
            self.zoom = self.zoom / 1.01
            self.set_resize_matrix()

    def apply_depth_parameters(self, parameters):
        """
        Args:
            parameters: a dictionary with
                key: str, parameter name
                value: int, parameter value
        """
        for key, value in parameters.items():
            setattr(self, key, value)

    def change_display_size(self, width, height):
        self.pause()

        self.set_display_size(width, height)
        self.set_resize_matrix()

        self.resume()

    def get_processed_images(self):
        return self.imgR_proc, self.imgL_proc

    def get_display_image(self):
        return self.img_display

    def set_cap_threads(self, thread_R, thread_L):
        self.pause()

        self.cap_thread_R = thread_R
        self.cap_thread_L = thread_L

        # The input image dimension could be different after switching camera
        # So reset resize matrix
        self.set_resize_matrix()

        self.resume()

