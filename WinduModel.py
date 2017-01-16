import numpy as np
import cv2, time, sys, threading
from OpenGL import GL
from WinduView import *
from WinduController import *



class WinduCore(object):
    def __init__(self):
        # Instantiate a controller object.
        # Pass the core object into the controller object,
        # so the controller can call the core.
        self.controller = Controller(core_obj = self)

        # Instantiate a gui object.
        # Pass the controller object into the gui object,
        # so the gui can call the controller, which in turn calls the core
        self.gui = WinduGUI(controller_obj = self.controller)
        self.gui.show()

        # The mediator is a channel to emit any signal to the gui object.
        # Pass the gui object into the mediator object,
        # so the mediator knows where to emit the signal.
        self.mediator = Mediator(self.gui)

        self.__init__connect_signals()

        # Start the video thread
        self.start_video_thread()

    def __init__connect_signals(self):
        '''
        Call the mediator to connect signals to the gui.
        These are the signals to be emitted dynamically during runtime.

        Each signal is defined by a unique str signal name.
        '''
        signal_names = ['display_topography', 'progress_update']
        self.mediator.connect_signals(signal_names)

    def start_video_thread(self):
        # Pass the mediator into the video thread,
        # so the video thread can talk to the gui.
        self.video_thread = VideoThread(mediator_obj = self.mediator)
        self.video_thread.start()

    def stop_video_thread(self):
        self.video_thread.stop()

    def close(self):
        'Should be called upon software termination.'
        self.stop_video_thread()

    # Methods called by the controller object

    def snapshot(self):
        if self.video_thread:
            cv2.imwrite('snapshot.jpg', self.video_thread.imgC)

    def toggle_recording(self):
        if self.video_thread:
            self.video_thread.toggle_recording()

    def auto_offset(self):
        '''
        1) Take current right and left images from the video thread.
        2) Use correlation function to calculate the offset.
        3) Set the offset parameters of the video thread object
        '''
        if self.video_thread is None:
            return

        imgR = cv2.cvtColor(self.video_thread.imgR_0, cv2.COLOR_BGR2GRAY)
        imgL = cv2.cvtColor(self.video_thread.imgL_0, cv2.COLOR_BGR2GRAY)

        if not imgR.shape == imgL.shape:
            return

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

        self.video_thread.set_offset(offset_x, offset_y)

    def zoom_in(self):
        if self.video_thread:
            self.video_thread.zoom_in()

    def zoom_out(self):
        if self.video_thread:
            self.video_thread.zoom_out()

    def stereo_reconstruction(self, x_scale=0.01, y_scale=0.01, z_scale=0.002):
        '''
        1) Get dual images from the video thread.
        2) Convert to gray scale.
        3) Adjust image offset by translation.
        4) Compute stereo disparity, i.e. depth map.
        5) Build vertex map, which has 6 channels: X Y Z R G B
        6) Build vertex list. Each point has 9 values: X Y Z R G B Nx Ny Nz
                                                                  (N stands for normal vector)
        '''

        if self.video_thread is None:
            return

        self.video_thread.pause()

        # Get the raw BGR (not RGB) images from both cameras
        imgR = self.video_thread.imgR_0
        imgL = self.video_thread.imgL_0

        rows, cols, _ = imgL.shape

        # Adjust image offset
        offset_x = self.video_thread.offset_x
        offset_y = self.video_thread.offset_y

        M = np.float32([ [1, 0, offset_x] ,
                         [0, 1, offset_y] ])

        imgL = cv2.warpAffine(imgL, M, (cols, rows))

        # Convert to gray scale to compute stereo disparity
        imgR_gray = cv2.cvtColor(imgR, cv2.COLOR_BGR2GRAY)
        imgL_gray = cv2.cvtColor(imgL, cv2.COLOR_BGR2GRAY)

        # Compute stereo disparity
        ndisparities = self.video_thread.ndisparities # Must be divisible by 16
        SADWindowSize = self.video_thread.SADWindowSize # Must be odd, be within 5..255 and be not larger than image width or height
        stereo = cv2.StereoBM(cv2.STEREO_BM_BASIC_PRESET, ndisparities, SADWindowSize)
        disparity = stereo.compute(imgL_gray, imgR_gray)

        # Build vertex map
        # For each point there are 6 channels:
        #   channels 0..2 : X Y Z coordinates
        #   channels 3..5 : R G B color values
        vertex_map = np.zeros( (rows, cols, 6), np.float )

        # Channels 0, 1: X (column) and Y (row) coordinates
        for r in xrange(rows):
            for c in xrange(cols):
                vertex_map[r, c, 0] = (c - cols/2) * x_scale # Centered and scaled
                vertex_map[r, c, 1] = (r - rows/2) * y_scale

        # Channel 2: Z (disparity) cooridnates
        vertex_map[:, :, 2] = disparity * z_scale # Scaled

        # Channels 3, 4, 5: RGB values
        # '::-1' inverts the sequence of BGR (in OpenCV) to RGB
        # OpenGL takes color values between 0 and 1, so divide by 255
        vertex_map[:, :, 3:6] = imgL[:, :, ::-1] / 255.0

        # Start building vertex list
        # Each point has 9 values: X Y Z R G B Nx Ny Nz
        numVertices = (rows - 1) * (cols - 1) * 6
        vertex_list = np.zeros( (numVertices, 9), np.float )

        V_map = vertex_map
        V_list = vertex_list
        i = 0
        percent_past = 0
        for r in xrange(rows-1):

            percent = int( ( (r + 1) / float(rows - 1) ) * 100 )

            # Emit progress signal only when there is an increase in precentage
            if not percent == percent_past:
                percent_past = percent
                self.mediator.emit_signal( signal_name = 'progress_update',
                                           arg = ('Rendering 3D Model', percent) )

            for c in xrange(cols-1):

                # Four point coordinates
                P1 = V_map[r  , c  , 0:3]
                P2 = V_map[r  , c+1, 0:3]
                P3 = V_map[r+1, c  , 0:3]
                P4 = V_map[r+1, c+1, 0:3]

                # Four point colors
                C1 = V_map[r  , c  , 3:6]
                C2 = V_map[r  , c+1, 3:6]
                C3 = V_map[r+1, c  , 3:6]
                C4 = V_map[r+1, c+1, 3:6]

                # First triangle STARTS
                N = np.cross(P2-P1, P4-P1)
                N = N / np.sqrt(np.sum(N**2))

                V_list[i, 0:3] = P1 # Coordinate
                V_list[i, 3:6] = C1 # Color
                V_list[i, 6:9] = N  # Noraml vector
                i = i + 1
                V_list[i, 0:3] = P4
                V_list[i, 3:6] = C4
                V_list[i, 6:9] = N
                i = i + 1
                V_list[i, 0:3] = P2
                V_list[i, 3:6] = C2
                V_list[i, 6:9] = N
                i = i + 1
                # First triangle ENDS

                # Second triangle STARTS
                N = np.cross(P4-P1, P3-P1)
                N = N / np.sqrt(np.sum(N**2))

                V_list[i, 0:3] = P1
                V_list[i, 3:6] = C1
                V_list[i, 6:9] = N
                i = i + 1
                V_list[i, 0:3] = P3
                V_list[i, 3:6] = C3
                V_list[i, 6:9] = N
                i = i + 1
                V_list[i, 0:3] = P4
                V_list[i, 3:6] = C4
                V_list[i, 6:9] = N
                i = i + 1
                # Second triangle ENDS

        self.mediator.emit_signal( signal_name = 'progress_update',
                                   arg = ('Displaying 3D Topography', 0) )

        self.mediator.emit_signal( signal_name = 'display_topography',
                                   arg = vertex_list )

        self.mediator.emit_signal( signal_name = 'progress_update',
                                   arg = ('Displaying 3D Topography', 100) )

        self.video_thread.resume()

    def apply_depth_parameters(self, parameters):

        if self.video_thread:
            self.video_thread.apply_depth_parameters(parameters)

    def apply_camera_parameters(self, parameters):

        if self.video_thread:
            self.video_thread.apply_camera_parameters(parameters)

    def toggle_depth_map(self):
        self.video_thread.isComputingDepth = not self.video_thread.isComputingDepth



class VideoThread(threading.Thread):
    '''
    This object operates the dynamic image acquisition from dual USB cameras.
    '''
    def __init__(self, mediator_obj):
        super(VideoThread, self).__init__()

        # The customized dual-camera object is
        # a low-level object of the video thread object
        self.cams = DualCamera()

        # Mediator emits signal to the gui object
        self.mediator = mediator_obj

        self.__init__connect_signals()
        self.__init__parms()

    def __init__connect_signals(self):
        '''
        Call the mediator to connect signals to the gui.
        These are the signals to be emitted dynamically during runtime.

        Each signal is defined by a unique str signal name.
        '''
        signal_names = ['display_image', 'recording_starts', 'recording_ends', 'set_info_text']
        self.mediator.connect_signals(signal_names)

    def __init__parms(self):
        # Parameters for image processing
        self.offset_x, self.offset_y = 0, 0
        self.set_offset_matrix()
        self.img_height, self.img_width, _ = self.cams.read()[0].shape
        self.zoom = 1.0
        self.screen_width, self.screen_height = 1136, 640
        self.imgC = np.zeros( (self.screen_height, self.screen_width, 3), np.uint8 )
        self.set_resize_matrix()

        # Parameters for stereo depth map
        self.ndisparities = 32 # Must be divisible by 16
        self.SADWindowSize = 31 # Must be odd, be within 5..255 and be not larger than image width or height

        # Parameters for administrative logic
        self.isRecording = False
        self.isStop = False
        self.isPause = False
        self.isComputingDepth = False
        self.t_0 = time.time()
        self.t_1 = time.time()

    def set_offset_matrix(self):
        '''
        Define the matrix for step (1) in the image processing pipeline.
        '''
        self.offset_matrix = np.float32([ [1, 0, self.offset_x] ,
                                          [0, 1, self.offset_y] ])

    def set_resize_matrix(self):
        '''
        Define the matrix for step (2) in the image processing pipeline.
        '''

        # The scale factors
        scale_x = self.zoom
        scale_y = self.zoom

        # The translation distance
        #     = half of the difference between
        #         the screen size and the zoomed image size

        #    ( (     screen size     ) - (     zoomed image size     ) ) / 2
        tx = ( (self.screen_width / 2) - (self.img_width  * self.zoom) ) / 2
        ty = ( (self.screen_height   ) - (self.img_height * self.zoom) ) / 2

        self.resize_matrix = np.float32([ [scale_x, 0      , tx] ,
                                          [0      , scale_y, ty] ])

    def run(self):
        '''
        There are three major steps for the image processing pipeline,
        with some additional steps in between.

        ( ) Check image dimensions.
        (1) Eliminate offset of the raw input image.
        ( ) Compute depth map (optional).
        (2) Resize and translate to place each image at the center of both sides of the view.
        (3) Combine images.
        '''
        while not self.isStop:

            if self.isPause:
                time.sleep(0.1)
                continue

            self.imgR_0, self.imgL_0 = self.cams.read() # The suffix '_0' means raw input image

            if not self.imgR_0.shape == self.imgL_0.shape:
                self.mediator.emit_signal( signal_name = 'set_info_text',
                                           arg = 'Image dimensions not identical.' )
                time.sleep(0.1)
                continue

            # (1)
            # Eliminate offset of the raw input image.
            # That is, translate the left to match the right
            if self.offset_x != 0 or self.offset_y != 0:

                rows, cols, _ = self.imgL_0.shape # Output image dimension

                self.imgR_1 = np.copy(self.imgR_0)
                self.imgL_1 = cv2.warpAffine(self.imgL_0, self.offset_matrix, (cols, rows))

            else:
                self.imgR_1 = np.copy(self.imgR_0)
                self.imgL_1 = np.copy(self.imgL_0)

            # Compute stereo depth map (optional)
            if self.isComputingDepth:
                # Convert to gray scale
                self.imgR_gray = cv2.cvtColor(self.imgR_1, cv2.COLOR_BGR2GRAY)
                self.imgL_gray = cv2.cvtColor(self.imgL_1, cv2.COLOR_BGR2GRAY)

                # Compute stereo disparity
                stereo = cv2.StereoBM(cv2.STEREO_BM_BASIC_PRESET, self.ndisparities, self.SADWindowSize)
                D = stereo.compute(self.imgL_gray, self.imgR_gray).astype(np.float)
                depth_map = ( D - np.min(D) ) / ( np.max(D) - np.min(D) ) * 255

                for color in xrange(3):
                    self.imgL_1[:, :, color] = depth_map.astype(np.uint8)

            # (2)
            # Resize and translate to place each image at the center of both sides of the view.
            rows, cols = self.screen_height, self.screen_width / 2 # Output image dimension

            self.imgR_2 = cv2.warpAffine(self.imgR_1, self.resize_matrix, (cols, rows))
            self.imgL_2 = cv2.warpAffine(self.imgL_1, self.resize_matrix, (cols, rows))

            # (3)
            # Combine images.
            h, w = self.screen_height, self.screen_width
            self.imgC[:, 0:(w/2), :] = self.imgL_2
            self.imgC[:, (w/2):w, :] = self.imgR_2

            if self.isRecording:
                self.writer.write(self.imgC)

            self.mediator.emit_signal( signal_name = 'display_image',
                                       arg = self.imgC )
            self.emit_fps_info()

        # Close camera hardware when the image-capturing main loop is done.
        self.cams.close()

    def emit_fps_info(self):
        '''
        Emits real-time frame-rate info to the gui
        '''

        # Calculate frame rate
        self.t_1, self.t_0 = time.time(), self.t_1
        rate = int( 1 / (self.t_1 - self.t_0))

        text = 'Frame rate = {} fps'.format(rate)

        self.mediator.emit_signal( signal_name = 'set_info_text',
                                   arg = text )

    # Methods commanded by the high-level core object.

    def set_offset(self, offset_x, offset_y):
        self.offset_x, self.offset_y = offset_x, offset_y
        self.set_offset_matrix()

        print 'offset_x = ' + str(self.offset_x) + '\n' \
              'offset_y = ' + str(self.offset_y)

    def toggle_recording(self):
        if not self.isRecording:
            # Define the codec, which is platform specific and can be hard to find
            # Set fourcc = -1 so that can select from the available codec
            fourcc = -1
            # Create VideoWriter object at 30fps
            w, h = self.screen_width, self.screen_height
            self.writer = cv2.VideoWriter( 'Windu Vision.avi', fourcc, 30.0, (w, h) )
            self.isRecording = True

            # Change the icon of the gui button
            self.mediator.emit_signal('recording_starts')

        else:
            self.isRecording = False
            self.writer.release()

            # Change the icon of the gui button
            self.mediator.emit_signal('recording_ends')

    def zoom_in(self):
        if self.zoom * 1.01 < 2.0:
            self.zoom = self.zoom * 1.01
            self.set_resize_matrix()

    def zoom_out(self):
        if self.zoom / 1.01 > 0.5:
            self.zoom = self.zoom / 1.01
            self.set_resize_matrix()

    def pause(self):
        self.isPause = True

    def resume(self):
        self.isPause = False

    def stop(self):
        'Called to terminate the video thread.'

        # Stop recording
        if self.isRecording:
            self.isRecording = False
            self.writer.release()

        # Shut off main loop in self.run()
        self.isStop = True

    def apply_depth_parameters(self, parameters):

        for key, value in parameters.items():
            setattr(self, key, value)

    def apply_camera_parameters(self, parameters):

        if self.cams:
            self.cams.apply_camera_parameters(parameters)



class DualCamera(object):
    '''
    A customized camera API.

    Two cv2.VideoCapture objects are instantiated.
    If not successfully instantiated, then the VideoCapture object is None.
    '''
    def __init__(self):
        self.camR_id = 1
        self.camL_id = 2

        self.camR = cv2.VideoCapture(self.camR_id)
        self.camL = cv2.VideoCapture(self.camL_id)

        if not self.camR.isOpened():
            self.camR = None

        if not self.camL.isOpened():
            self.camL = None

        self.__init__parameters()
        self.__init__config()

        self.imgR_blank = cv2.imread('images/blankR.tif')
        self.imgL_blank = cv2.imread('images/blankL.tif')

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

        self.parm_vals = {'width'        : 640 ,
                          'height'       : 480 ,
                          'brightness'   : 150 ,
                          'contrast'     : 64  ,
                          'saturation'   : 80  ,
                          'hue'          : 13  ,
                          'gain'         : 50  ,
                          'exposure'     : -3  ,
                          'white_balance': 4000,
                          'focus'        : 0   }

    def __init__config(self):

        for cam in (self.camR, self.camL):
            if not cam is None:
                for key in self.parm_ids:
                    cam.set( self.parm_ids[key], self.parm_vals[key] )

    def read(self):
        '''Return the properly rotated image. If cv2_cam is None than return a blank image.'''

        if not self.camR is None:
            _, self.imgR = self.camR.read()
            self.imgR = np.rot90(self.imgR, 3) # Rotates 90 right
        else:
            # Must insert a time delay to emulate camera harware delay
            # Otherwise the program will crash due to full-speed looping
            time.sleep(0.01)
            self.imgR = self.imgR_blank

        if not self.camL is None:
            _, self.imgL = self.camL.read()
            self.imgL = np.rot90(self.imgL, 1) # Rotates 90 right
        else:
            time.sleep(0.01)
            self.imgL = self.imgL_blank

        return (self.imgR, self.imgL)

    def apply_camera_parameters(self, parameters):

        for key, value in parameters.items():
            self.parm_vals[key] = value

        self.__init__config()

    def close(self):
        cams = [self.camR, self. camL]
        for cam in cams:
            if not cam is None:
                cam.release()



class CmdThread(threading.Thread):
    def __init__(self, core_obj):
        super(CmdThread, self).__init__()
        self.core = core_obj

    def run(self):
        while True:
            pass
            # Methods in the core object can be directly called
            # method_name = raw_input('Execute method in the core object: ')
            # if method_name == 'quit':
            #     print '\nCommand input quit.'
            #     break
            # try:
            #     method = getattr(self.core, method_name)
            #     method()
            # except Exception as exception_inst:
            #     print exception_inst

            # self.core.video_thread.ndisparities = int(raw_input('ndisparities: '))
            # self.core.video_thread.SADWindowSize = int(raw_input('SADWindowSize: '))



if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    core = WinduCore()

    cmd_thread = CmdThread(core_obj = core)
    # cmd_thread.start()

    sys.exit(app.exec_())


