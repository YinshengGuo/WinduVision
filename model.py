import numpy as np
import cv2, time, sys, threading, json
from OpenGL import GL

from view import *
from controller import *
from threads import *
from constants import *
from single_camera import *
from stereo import Stereo as stereo



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
        # Pass the gui object into the mediator object...
        #     so the mediator knows where to emit the signal.
        self.mediator = Mediator(self.gui)

        self.view_mode = MICRO

        # Start the video thread, also concurrent threads
        self.start_video_thread()

    def __init__signals(self, connect=True):
        """
        Call the mediator to connect (or disconnect) signals to the gui.
        These are the signals to be emitted dynamically during runtime.

        Each signal is defined by a unique str signal name.

        Args:
            connect: boolean, specifies whether connect or disconnect signals.
        """
        signal_names = ['']

        if connect:
            self.mediator.connect_signals(signal_names)
        else:
            self.mediator.disconnect_signals(signal_names)

    def start_video_thread(self):
        """
        Initialize the following in order:
            3 camera objects
            3 capture threads
            1 process thread
            1 camera tuning thread
            1 align thread
            1 writer thread

        The order of initialization is defined because of dependency between threads.
        """
        # 3 cameras
        self.__init_cams()

        # 3 capture threads
        self.__init_cap_threads(self.view_mode)

        # 1 process thread
        self.__init_proc_thread()

        # 1 camera tuning thread
        self.__init_auto_cam_thread()

        # 1 align thread
        self.__init_align_thread()

        # 1 writer thread
        self.__init_writer_thread()

    def stop_video_thread(self):
        """
        Stop the following in order:
            1 writer thread
            1 align thread
            1 camera tuning thread
            1 process thread
            3 capture threads
            3 camera objects

        The order of stopping is the reverse of start_video_thread()...
            because the least depending ones should be closed at last
        """
        self.writer_thread.stop()
        self.align_thread.stop()
        self.cam_tune_thread.stop()
        self.proc_thread.stop()

        for thread in self.cap_threads.values():
            thread.stop()

        for cam in self.cams.values():
            cam.close()

    def __init_cams(self):
        """Instantiate 3 camera objects"""
        self.cams = {}
        for key in [CAM_R, CAM_L, CAM_E]:
            self.cams[key] = SingleCamera(which_cam = key)

    def __init_cap_threads(self, mode):
        """
        Instantiate and start 3 capture threads.
        Depending on the mode, resume different cap_threads (i.e. start main loop in the .run() method):
            MICRO mode: CAM_R & CAM_L
            AMBIENT mode: CAM_E & CAM_E

        Args:
            mode: glocal constant, MICRO or AMBIENT
        """
        self.cap_threads = {}
        for key in [CAM_R, CAM_L, CAM_E]:
            self.cap_threads[key] = CaptureThread(camera = self.cams[key],
                                                  mediator = self.mediator)
            self.cap_threads[key].start()

        if mode == MICRO:
            self.cap_threads[CAM_R].resume()
            self.cap_threads[CAM_L].resume()
            self.active_cap_thread_R = self.cap_threads[CAM_R]
            self.active_cap_thread_L = self.cap_threads[CAM_L]

        elif mode == AMBIENT:
            self.cap_threads[CAM_E].resume()
            self.active_cap_thread_R = self.cap_threads[CAM_E]
            self.active_cap_thread_L = self.cap_threads[CAM_E]

    def __init_proc_thread(self):
        """
        Instantiate and start 1 image processing thread.
        """
        # Image processing thread takes two images from the two active capturing threads,
        #     for right and left cameras, respectively.
        # Pass in the two active capturing threads
        self.proc_thread = ProcessThread(cap_thread_R = self.active_cap_thread_R,
                                         cap_thread_L = self.active_cap_thread_L,
                                             mediator = self.mediator)

        self.proc_thread.start()
        # Calling resume() puts the proc_thread in actively running status in the main loop
        self.proc_thread.resume()

    def __init_auto_cam_thread(self):
        """
        Instantiate 1 camera tuning thread. Do NOT call resume() to make it active.
        """
        self.cam_tune_thread = CamTuneThread(cap_thread_R = self.active_cap_thread_R,
                                             cap_thread_L = self.active_cap_thread_L,
                                                 mediator = self.mediator)
        self.cam_tune_thread.start()

    def __init_align_thread(self):
        """
        Instantiate 1 image alignment thread. Do NOT call resume() to make it active.
        """
        self.align_thread = AlignThread(process_thread = self.proc_thread,
                                              mediator = self.mediator)
        self.align_thread.start()

    def __init_writer_thread(self):
        """
        Instantiate 1 video writer thread. Do NOT call resume() to make it active.
        """
        self.writer_thread = WriterThread(process_thread = self.proc_thread,
                                                mediator = self.mediator)
        self.writer_thread.start()

    def __set_view_mode(self, mode):
        """
        Set the viewing mode.
        This is called when the user wants to change between the microscope or the ambient view mode.

        Args:
            mode: glocal constant, MICRO or AMBIENT
        """

        # Do nothing if not changing the mode
        if mode == self.view_mode:
            return

        # Configure the active capturing threads
        if mode == MICRO:
            self.cap_threads[CAM_R].resume()
            self.cap_threads[CAM_L].resume()
            self.cap_threads[CAM_E].pause()
            self.active_cap_thread_R = self.cap_threads[CAM_R]
            self.active_cap_thread_L = self.cap_threads[CAM_L]
        elif mode == AMBIENT:
            self.cap_threads[CAM_R].pause()
            self.cap_threads[CAM_L].pause()
            self.cap_threads[CAM_E].resume()
            self.active_cap_thread_R = self.cap_threads[CAM_E]
            self.active_cap_thread_L = self.cap_threads[CAM_E]

        # Update active capturing threads to the image processing thread
        self.proc_thread.set_cap_threads(thread_R = self.active_cap_thread_R,
                                         thread_L = self.active_cap_thread_L)

        # Update active capturing threads to the camera tuning thread
        self.cam_tune_thread.set_cap_threads(thread_R = self.active_cap_thread_R,
                                             thread_L = self.active_cap_thread_L)

        self.view_mode = mode

    def close(self):
        """Should be called upon software termination."""
        self.stop_video_thread()

    # Public methods called by the controller object

    def snapshot(self, fname):
        """
        Save the currently displayed image as fname.

        Args:
            fname: str, a filename or a complete filepath
        """
        img = self.proc_thread.get_display_image()
        cv2.imwrite(fname, img)

    def toggle_recording(self):
        """
        Toggle the recording status of the video writer thread.
        """
        self.writer_thread.toggle()

    def toggle_auto_offset(self):
        """
        Toggle the status of the image alignment thread.
        """
        self.align_thread.toggle()

    def toggle_view_mode(self):
        """
        Toggle the viewing mode according to the current viewing mode.

        If self.view_mode == MICRO then switch to AMBIENT, and vice versa.
        """
        if self.view_mode == MICRO:
            self.__set_view_mode(mode=AMBIENT)
        else:
            self.__set_view_mode(mode=MICRO)

        # Reset the image alignment back to zero
        #     because the viewing mode is changed
        #     and there's no need to carry over the alignment offset
        self.align_thread.zero_offset()

    def toggle_auto_cam(self):
        """
        Toggle the status of the camera tuning thread.
        """
        self.cam_tune_thread.toggle()

    def zoom_in(self):
        """
        Call the proc_thread.zoom_in() method to zoom in (enlarge) the image.
        """
        self.proc_thread.zoom_in()

    def zoom_out(self):
        """
        Call the proc_thread.zoom_out() method to zoom out (shrink) the image.
        """
        self.proc_thread.zoom_out()

    def stereo_reconstruction(self):
        """
        Still a functionality under development. Non-developer users do not have access to it.
        """
        self.proc_thread.pause()
        stereo.reconstruction(self.proc_thread, self.mediator)
        self.proc_thread.resume()

    def apply_depth_parameters(self, parameters):
        """
        Args:
            parameters: a dictionary with
                key: str, parameter name
                value: int, parameter value
        """
        self.proc_thread.apply_depth_parameters(parameters)

    def apply_camera_parameters(self, data):
        """
        Args:
            data: a dictionary
                {
                'which_cam': global constant, one of CAM_R, CAM_L, CAM_E,
                'parameters': dictionary, holding camera parameters
                    {
                    key: str, parameter name
                    value: int, parameter value
                    }
                }
        """
        which_cam = data['which_cam']
        parameters = data['parameters']

        self.cap_threads[which_cam].set_camera_parameters(parameters)

    def toggle_depth_map(self):
        """
        Still a functionality under development. Non-developer users do not have access to it.
        """
        self.proc_thread.computingDepth = not self.proc_thread.computingDepth

    def set_display_size(self, dim):
        """
        Args:
            dim: a tuple of integers (width, height)
        """
        self.proc_thread.change_display_size(width=dim[0], height=dim[1])

    def start_select_cam(self):
        """
        Stop all threads for viewing.
        Move into camera selection state by instantiating a CamSelectThread object.
        After camera selection is done, the self.start_video_thread() method will be called by the gui object
            to get back to the normal viewing state.
        """
        self.stop_video_thread()
        self.cam_select_thread = CamSelectThread(self.mediator)
        self.cam_select_thread.start()

    def save_cam_id(self, data):
        """
        Save the camera id to the json file storing camera parameters.

        Args:
            data: a dictionary
                {
                'id': int, the camera id read by the cv2.VideoCapture() class,
                'which_cam': global constant, one of CAM_R, CAM_L, CAM_E,
                }
        """
        id = data['id']
        which_cam = data['which_cam']

        filepath = 'parameters/' + which_cam + '.json'
        with open(filepath, 'r') as fh:
            parm_vals = json.loads(fh.read())

        parm_vals['id'] = id

        with open(filepath, 'w') as fh:
            json.dump(parm_vals, fh)

    def next_cam(self):
        """
        This method is part of the working flow in the camera selection state...
            when the CamSelectThread() object is active
        """
        self.cam_select_thread.isWaiting = False



if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    core = WinduCore()
    sys.exit(app.exec_())


