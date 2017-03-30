import numpy as np
import cv2, time, sys, threading, json
from OpenGL import GL

from windu_view import *
from windu_controller import *
from all_threads import *
from constants import *



class WinduCore(object):
    def __init__(self):

        super(WinduCore, self).__init__()

        # Instantiate a controller object.
        # Pass the core object into the controller object, so the controller can call the core.
        self.controller = Controller(core = self)

        # Instantiate a gui object.
        # Pass the controller object into the gui object...
        #     so the gui can call the controller, which in turn calls the core
        self.gui = WinduGUI(controller = self.controller)
        self.gui.show()

        # The mediator is a channel to emit any signal to the gui object.
        # Pass the gui object into the mediator object, so the mediator knows where to emit the signal.
        self.mediator = Mediator(self.gui)

        self.__init__signals(connect=True)

        # Start the video thread, also concurrent threads
        self.start_video_thread()

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

    def start_video_thread(self):

        #------ 3 capture threads for 3 cameras ------#
        self.cap_threads = {}
        for key in [CAM_R, CAM_L, CAM_E]:
            self.cap_threads[key] = CaptureThread(which_cam=key)
            self.cap_threads[key].start()



        #------ 2 process threads for 2 viewing scenarios ------#
        self.proc_threads = {}
        # The microscope-view processing thread takes CAM_R and CAM_L capture threads
        self.proc_threads[MICRO] = ProcessThread(capture_thread_R = self.cap_threads[CAM_R],
                                                 capture_thread_L = self.cap_threads[CAM_L],
                                                         mediator = self.mediator)

        # The ambient-view processing thread takes CAM_E capture thread for both eyes
        self.proc_threads[AMBIENT] = ProcessThread(capture_thread_R = self.cap_threads[CAM_E],
                                                   capture_thread_L = self.cap_threads[CAM_E],
                                                           mediator = self.mediator)
        # Start all processing threads
        for t in self.proc_threads.values():
            t.start()

        # Pause the one that's not active
        self.proc_threads[AMBIENT].pause()
        self.view_mode = MICRO
        self.active_proc_thread = self.proc_threads[MICRO]



        #------ The camera equalizer operates on CAM_R and CAM_L capture threads ------#
        self.cam_equal_thread = CamEqualThread(capture_thread_R = self.cap_threads[CAM_R],
                                               capture_thread_L = self.cap_threads[CAM_L],
                                                       mediator = self.mediator)
        self.cam_equal_thread.start()



        #------ The align_thread operates on the active process thread ------#
        self.align_thread = AlignThread(process_thread = self.active_proc_thread,
                                              mediator = self.mediator)
        self.align_thread.start()



        #------ The writer_thread operates on the active process thread ------#
        self.writer_thread = WriterThread(process_thread = self.active_proc_thread,
                                                mediator = self.mediator)
        self.writer_thread.start()

    def stop_video_thread(self):
        # The order of stopping is the reverse of start_video_thread()...
        #     because the least dependent ones should be closed at last

        self.align_thread.stop()
        self.writer_thread.stop()
        self.cam_equal_thread.stop()

        for k, t in self.proc_threads.items():
            t.stop()

        for k, t in self.cap_threads.items():
            t.stop()

    def close(self):
        'Should be called upon software termination.'
        self.stop_video_thread()

        # Disconnect signals from the gui object
        self.__init__signals(connect=False)

    # Methods called by the controller object

    def snapshot(self, fname):
        img = self.active_proc_thread.get_display_image()
        cv2.imwrite(fname, img)

    def toggle_recording(self):
        self.writer_thread.toggle()

    def toggle_auto_offset(self):
        self.align_thread.toggle()

    def toggle_view_mode(self):
        self.active_proc_thread.pause()

        if self.view_mode == MICRO:
            self.active_proc_thread = self.proc_threads[AMBIENT]
            self.view_mode = AMBIENT
        else:
            self.active_proc_thread = self.proc_threads[MICRO]
            self.view_mode = MICRO

        # Update active_process_thread to...
        #     the align_thread and writer_thread
        self.align_thread.set_process_thread(self.active_proc_thread)
        self.writer_thread.set_process_thread(self.active_proc_thread)

        self.active_proc_thread.resume()

    def zoom_in(self):
        self.active_proc_thread.zoom_in()

    def zoom_out(self):
        self.active_proc_thread.zoom_out()

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

        self.active_proc_thread.pause()

        # Get the raw BGR (not RGB) images from both cameras
        imgR, imgL = self.active_proc_thread.get_processed_images()

        rows, cols, channels = imgL.shape

        # Convert to gray scale to compute stereo disparity
        imgR_gray = cv2.cvtColor(imgR, cv2.COLOR_BGR2GRAY)
        imgL_gray = cv2.cvtColor(imgL, cv2.COLOR_BGR2GRAY)

        # Compute stereo disparity
        ndisparities = self.active_proc_thread.ndisparities # Must be divisible by 16
        SADWindowSize = self.active_proc_thread.SADWindowSize # Must be odd, be within 5..255 and be not larger than image width or height
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

        self.active_proc_thread.resume()

    def apply_depth_parameters(self, parameters):

        self.active_proc_thread.apply_depth_parameters(parameters)

    def apply_camera_parameters(self, data):

        which_cam = data['which_cam']
        parameters = data['parameters']

        self.cap_threads[which_cam].set_camera_parameters(parameters)

    def toggle_depth_map(self):
        self.active_proc_thread.computingDepth = not self.active_proc_thread.computingDepth

    def set_display_size(self, dim):
        '''
        Args:
            dim: a tuple of (width, height)
        '''
        self.active_proc_thread.set_display_size(width=dim[0], height=dim[1])

    def start_select_cam(self):
        self.stop_video_thread()

        self.cam_select_thread = CamSelectThread(self.mediator)
        self.cam_select_thread.start()

    def save_cam_id(self, data):

        id = data['id']
        which_cam = data['which_cam']

        filepath = 'parameters/' + which_cam + '.json'
        with open(filepath, 'r') as fh:
            parm_vals = json.loads(fh.read())

        parm_vals['id'] = id

        with open(filepath, 'w') as fh:
            json.dump(parm_vals, fh)

    def next_cam(self):
        self.cam_select_thread.isWaiting = False

    def equalize_cameras(self):
        '''
        Instantiate a thread object to equalize cameras.
        After the work is done, the thread object is no longer in use.
        '''

        self.cam_equal_thread.resume()



if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    core = WinduCore()
    sys.exit(app.exec_())


