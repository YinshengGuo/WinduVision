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

        self.__init__signals(connect=True)

        # Start the video thread, also concurrent threads
        self.start_video_thread()

        self.__init__cmd()

    def __init__signals(self, connect=True):
        '''
        Call the mediator to connect signals to the gui.
        These are the signals to be emitted dynamically during runtime.

        Each signal is defined by a unique str signal name.

        The parameter 'connect' specifies whether connect or disconnect signals.
        '''
        signal_names = ['display_topography', 'progress_update']

        if connect:
            self.mediator.connect_signals(signal_names)
        else:
            self.mediator.disconnect_signals(signal_names)

    def __init__cmd(self):
        '''
        Some high-level commands to be executed upon the software is initiated
        '''
        pass

    def start_video_thread(self):
        # Pass the mediator into the video thread,
        # so the video thread can talk to the gui.
        self.video_thread = VideoThread(mediator_obj = self.mediator)
        self.video_thread.start()

        # The self.align_thread is dependent on self.video_thread
        self.align_thread = AlignThread(video_thread_obj = self.video_thread,
                                            mediator_obj = self.mediator)
        self.align_thread.start()

    def stop_video_thread(self):
        # The self.align_thread depends self.video_thread,
        # so close the align_thread first
        self.align_thread.stop()
        self.video_thread.stop()

    def close(self):
        'Should be called upon software termination.'
        self.stop_video_thread()

        # Disconnect signals from the gui object
        self.__init__signals(connect=False)

    # Methods called by the controller object

    def snapshot(self):
        if self.video_thread:
            cv2.imwrite('snapshot.jpg', self.video_thread.imgDisplay)

    def toggle_recording(self):
        if self.video_thread:
            self.video_thread.toggle_recording()

    def toggle_auto_offset(self):
        self.align_thread.toggle()

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

    def apply_camera_parameters(self, data):

        isRightCam = data['isRightCam']
        parameters = data['parameters']

        if self.video_thread:
            self.video_thread.apply_camera_parameters(isRightCam, parameters)

        with open('parameters/cam.json', 'r') as fh:
            saved_parameters = json.loads(fh.read())

        if isRightCam:
            side = 'R'
        else:
            side = 'L'

        for name in parameters.keys():
            saved_parameters[side][name] = parameters[name]

        with open('parameters/cam.json', 'w') as fh:
            json.dump(saved_parameters, fh)

    def toggle_depth_map(self):
        self.video_thread.computingDepth = not self.video_thread.computingDepth

    def set_display_size(self, dim):
        '''
        Args:
            dim: a tuple of (width, height)
        '''
        self.video_thread.set_display_size(width=dim[0], height=dim[1])

    def start_select_cam(self):
        self.stop_video_thread()

        self.cam_select_thread = CamSelectThread(mediator_obj = self.mediator)
        self.cam_select_thread.start()

    def save_cam_id(self, data):

        id = data['id']
        which_side = data['which_side']

        with open('parameters/cam.json', 'r') as fh:
            parm_vals = json.loads(fh.read())

        if which_side == 'R':
            parm_vals['R']['id'] = id
        elif which_side == 'L':
            parm_vals['L']['id'] = id
        else:
            return

        with open('parameters/cam.json', 'w') as fh:
            json.dump(parm_vals, fh)

    def next_cam(self):
        self.cam_select_thread.isWaiting = False



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

        self.__init__signals(connect=True)
        self.__init__parms()

    def __init__signals(self, connect=True):
        '''
        Call the mediator to connect signals to the gui.
        These are the signals to be emitted dynamically during runtime.

        Each signal is defined by a unique str signal name.

        The parameter 'connect' specifies whether connect or disconnect signals.
        '''
        signal_names = ['display_image', 'recording_starts', 'recording_ends', 'set_info_text']

        if connect:
            self.mediator.connect_signals(signal_names)
        else:
            self.mediator.disconnect_signals(signal_names)

    def __init__parms(self):
        # Parameters for image processing
        self.offset_x, self.offset_y = 0, 0
        self.img_height, self.img_width, _ = self.cams.read()[0].shape
        self.zoom = 1.0

        fh = open('parameters/gui.json', 'r')
        gui_parms = json.loads(fh.read())
        self.display_width = gui_parms['default_width']
        self.display_height = gui_parms['default_height']

        self.set_resize_matrix()



        # Parameters for stereo depth map
        self.ndisparities = 32 # Must be divisible by 16
        self.SADWindowSize = 31 # Must be odd, be within 5..255 and be not larger than image width or height



        # Parameters for looping, control and timing
        self.recording = False
        self.stopping = False
        self.pausing = False
        self.isPaused = False
        self.computingDepth = False
        self.t_0 = time.time()
        self.t_1 = time.time()

    def set_resize_matrix(self):
        '''
        Define the transformation matrix for the image processing pipeline.
        Also define the dimension of self.imgDisplay, which is the terminal image to be displayed in the GUI.
        '''


        # The base scale factor is the ratio of display height / image height,
        #     which scales the image to the size of the display.
        # Because height is the limiting dimension, so it's height but not width.
        base_scale = float(self.display_height) / self.img_height

        # The actual scale factor is the product of the base scale factor and the zoom factor.
        scale_x = base_scale * self.zoom
        scale_y = base_scale * self.zoom



        # The translation distance for centering
        #     = half of the difference between
        #         the screen size and the zoomed image size
        #    ( (     display size     ) - (     zoomed image size   ) ) / 2
        tx = ( (self.display_width / 2) - (self.img_width  * scale_x) ) / 2
        ty = ( (self.display_height   ) - (self.img_height * scale_y) ) / 2



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



        # Define self.imgDisplay, which is the image to be emitted to the GUI object.
        self.imgDisplay = np.zeros( (self.display_height, self.display_width, 3), np.uint8 )

    def run(self):
        '''
        There are three major steps for the image processing pipeline,
        with some additional steps in between.

        ( ) Check image dimensions.
        (1) Eliminate offset of the left image.
        (2) Resize and translate to place each image at the center of both sides of the view.
        ( ) Compute depth map (optional).
        (3) Combine images.
        '''
        while not self.stopping:

            # Pausing the loop (or not)
            if self.pausing:
                self.isPaused = True
                time.sleep(0.1)
                continue
            else:
                self.isPaused = False



            # Read the images from the cameras
            self.imgR_0, self.imgL_0 = self.cams.read() # The suffix '_0' means raw input image

            # Quick check on the image dimensions
            # If not matching, skip and continue
            if not self.imgR_0.shape == self.imgL_0.shape:
                self.mediator.emit_signal( signal_name = 'set_info_text',
                                           arg = 'Image dimensions not identical.' )
                time.sleep(0.1)
                continue



            # (1) Eliminate offset of the left image.
            # (2) Resize and translate to place each image at the center of both sides of the view.
            rows, cols = self.display_height, self.display_width / 2 # Output image dimension

            self.imgR_1 = cv2.warpAffine(self.imgR_0, self.resize_matrix_R, (cols, rows))
            self.imgL_1 = cv2.warpAffine(self.imgL_0, self.resize_matrix_L, (cols, rows))



            # Compute stereo depth map (optional)
            if self.computingDepth:
                self.imgL_1 = self.compute_depth(self.imgR_1, self.imgL_1)



            # (3) Combine images.
            h, w = self.display_height, self.display_width
            self.imgDisplay[:, 0:(w/2), :] = self.imgL_1
            self.imgDisplay[:, (w/2):w, :] = self.imgR_1

            self.mediator.emit_signal( signal_name = 'display_image',
                                       arg = self.imgDisplay )

            self.emit_fps_info()



            # Record video
            if self.recording:
                self.writer.write(self.imgDisplay)

        # Close camera hardware when the image-capturing main loop is done.
        self.cams.close()

        # Disconnect signals from the gui object when the thread is done
        self.__init__signals(connect=False)

    def compute_depth(self, imgR, imgL):
        # Convert to gray scale
        imgR_ = cv2.cvtColor(imgR, cv2.COLOR_BGR2GRAY)
        imgL_ = cv2.cvtColor(imgL, cv2.COLOR_BGR2GRAY)

        # Compute stereo disparity
        stereo = cv2.StereoBM(cv2.STEREO_BM_BASIC_PRESET, self.ndisparities, self.SADWindowSize)
        D = stereo.compute(imgL_, imgR_).astype(np.float)
        depth_map = ( D - np.min(D) ) / ( np.max(D) - np.min(D) ) * 255

        for ch in xrange(3):
            imgL[:, :, ch] = depth_map.astype(np.uint8)

        return imgL

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
        self.set_resize_matrix()

        print 'offset_x = {}, offset_y = {} \n'.format(str(self.offset_x), str(self.offset_y))

    def detect_offset(self):
        '''
        1) Read right and left images from the cameras.
        2) Use correlation function to calculate the offset.
        '''

        imgR, imgL = self.cams.read()

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

    def toggle_recording(self):
        if not self.recording:
            # Define the codec, which is platform specific and can be hard to find
            # Set fourcc = -1 so that can select from the available codec
            fourcc = -1
            # Create VideoWriter object at 30fps
            w, h = self.display_width, self.display_height
            self.writer = cv2.VideoWriter( 'Windu Vision.avi', fourcc, 30.0, (w, h) )
            self.recording = True

            # Change the icon of the gui button
            self.mediator.emit_signal('recording_starts')

        else:
            self.recording = False
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
        self.pausing = True
        while not self.isPaused:
            time.sleep(0.1)
        return

    def resume(self):
        self.pausing = False
        while self.isPaused:
            time.sleep(0.1)
        return

    def stop(self):
        'Called to terminate the video thread.'

        # Stop recording
        if self.recording:
            self.recording = False
            self.writer.release()

        # Shut off main loop in self.run()
        self.stopping = True

    def apply_depth_parameters(self, parameters):

        for key, value in parameters.items():
            setattr(self, key, value)

    def apply_camera_parameters(self, isRightCam, parameters):

        if self.cams:
            self.cams.set_parameters(isRightCam, parameters)

    def set_display_size(self, width, height):
        self.pause()

        self.display_width, self.display_height = width, height
        self.set_resize_matrix()

        self.resume()

    def get_raw_images(self):
        imgR, imgL = self.cams.read()
        return imgR, imgL



class DualCamera(object):
    '''
    A customized camera API.

    Two cv2.VideoCapture objects are instantiated.
    If not successfully instantiated, then the VideoCapture object is None.
    '''
    def __init__(self):

        self.__init__parameters()

        self.camR = cv2.VideoCapture(self.parm_vals['R']['id'])
        self.camL = cv2.VideoCapture(self.parm_vals['L']['id'])

        if not self.camR.isOpened():
            self.camR = None

        if not self.camL.isOpened():
            self.camL = None

        self.__init__config()

        self.imgR_blank = cv2.imread('images/blankR.tif')
        self.imgL_blank = cv2.imread('images/blankL.tif')

    def __init__parameters(self):
        '''
        Load camera parameters from the /parameters/cam.json file
        '''

        with open('parameters/cam.json', 'r') as fh:
            self.parm_vals = json.loads(fh.read())
            # data structure of self.parm_vals:
            # {'R': {dictionary of parameters}, 'L': {dictionary of parameters}}

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

    def __init__config(self):

        ids = self.parm_ids # dictionary
        vals = self.parm_vals # dictionary
        names = self.parm_ids.keys() # list

        if not self.camR is None:
            for name in names:
                self.camR.set( ids[name], vals['R'][name] )

        if not self.camL is None:
            for name in names:
                self.camL.set( ids[name], vals['L'][name] )

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

    def set_parameters(self, isRightCam, parameters):

        if isRightCam:
            side = 'R'
        else:
            side = 'L'

        for name, value in parameters.items():
            self.parm_vals[side][name] = value

        self.__init__config()

    def close(self):
        cams = [self.camR, self. camL]
        for cam in cams:
            if not cam is None:
                cam.release()



class AlignThread(threading.Thread):
    '''
    This thread runs concurrently with the VideoThread,
    dynamically checking if the stereo pair of images are aligned.
    '''
    def __init__(self, video_thread_obj, mediator_obj):
        super(AlignThread, self).__init__()

        self.video_thread = video_thread_obj
        self.mediator = mediator_obj

        self.__init__signals()

        self.stopping = False
        self.pausing = True
        self.isPaused = True

    def __init__signals(self, connect=True):
        '''
        Call the mediator to connect signals to the gui.
        These are the signals to be emitted dynamically during runtime.

        Each signal is defined by a unique str signal name.

        The parameter 'connect' specifies whether connect or disconnect signals.
        '''
        signal_names = ['auto_offset_resumed', 'auto_offset_paused']

        if connect:
            self.mediator.connect_signals(signal_names)
        else:
            self.mediator.disconnect_signals(signal_names)

    def run(self):

        # Construct a queue of offset values
        X = np.zeros((10, ), np.float)
        Y = np.zeros((10, ), np.float)

        while not self.stopping:

            # Pausing the loop (or not)
            if self.pausing:
                self.isPaused = True
                time.sleep(0.1)
                continue
            else:
                self.isPaused = False

            # Shift by one
            X[1:] = X[:-1]
            Y[1:] = Y[:-1]

            # Get the current offset value into the queue
            X[0], Y[0] = self.video_thread.detect_offset()

            # Sort the list of offset values
            # Remove the lowest and the highest one (outliers)
            # Average
            x_avg = np.average(np.sort(X)[1:-1])
            y_avg = np.average(np.sort(Y)[1:-1])

            # Set the offset value, which effectly moves the left image
            self.video_thread.set_offset(x_avg, y_avg)

            # If the current offset value differs significantly from the average,
            #     meaning that there is more "active movements",
            # then speed up the loop to get back to a stable condition as soon as possible.
            if abs(Y[0] - y_avg) > 1:
                time.sleep(0.01)
            else:
                # Under stable condition, in which the current offset doesn't differ from the average,
                # Check alignment every ~1 second.
                time.sleep(1)



        # Disconnect signals from the gui object when the thread is done
        self.__init__signals(connect=False)

    def toggle(self):

        if self.pausing: # If it's paused, resume
            self.pausing = False
            self.mediator.emit_signal(signal_name = 'auto_offset_resumed')

        else: # If it's not paused, pause
            self.pausing = True
            self.mediator.emit_signal(signal_name = 'auto_offset_paused')

    def stop(self):
        '''
        Called to terminate the thread.
        '''

        # Shut off main loop in self.run()
        self.stopping = True



class CamSelectThread(threading.Thread):
    def __init__(self, mediator_obj):
        super(CamSelectThread, self).__init__()

        self.mediator = mediator_obj

        self.__init__parameters()

        self.__init__signals()

    def __init__parameters(self):
        self.current_id = 0
        self.isDone = False

    def __init__signals(self, connect=True):
        '''
        Call the mediator to connect signals to the gui.
        These are the signals to be emitted dynamically during runtime.

        Each signal is defined by a unique str signal name.

        The parameter 'connect' specifies whether connect or disconnect signals.
        '''
        signal_names = ['show_current_cam', 'select_cam_done']

        if connect:
            self.mediator.connect_signals(signal_names)
        else:
            self.mediator.disconnect_signals(signal_names)

    def run(self):
        for id in range(10):

            self.isWaiting = True

            self.cam = cv2.VideoCapture(id)

            if self.cam.isOpened():
                _, img = self.cam.read()

                data = {'id': id, 'img': img}

                self.mediator.emit_signal( signal_name = 'show_current_cam',
                                                   arg = data)
                while self.isWaiting:
                    time.sleep(0.1)

            else:
                print 'Camera id: {} not available'.format(id)

            self.cam.release()

        self.mediator.emit_signal( signal_name = 'select_cam_done' )

        # Disconnect signals from the gui object when the thread is done
        self.__init__signals(connect=False)



if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    core = WinduCore()
    sys.exit(app.exec_())


