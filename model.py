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
        # Pass the gui object into the mediator object, so the mediator knows where to emit the signal.
        self.mediator = Mediator(self.gui)

        self.view_mode = MICRO

        # Start the video thread, also concurrent threads
        self.start_video_thread()

    def __init__signals(self, connect=True):
        '''
        Call the mediator to connect signals to the gui.
        These are the signals to be emitted dynamically during runtime.

        Each signal is defined by a unique str signal name.

        The parameter 'connect' specifies whether connect or disconnect signals.
        '''
        signal_names = ['']

        if connect:
            self.mediator.connect_signals(signal_names)
        else:
            self.mediator.disconnect_signals(signal_names)

    def start_video_thread(self):

        # 3 cameras
        self.init_cams()

        # 3 capture threads
        self.init_cap_threads(self.view_mode)

        # 2 process threads
        self.init_proc_thread()

        # 1 camera tuning and 1 camera equalizing thread
        self.init_auto_cam_threads()

        # 1 align thread
        self.init_align_thread()

        # 1 writer thread
        self.init_writer_thread()

    def stop_video_thread(self):
        # The order of stopping is the reverse of start_video_thread()...
        #     because the least dependent ones should be closed at last

        self.align_thread.stop()
        self.writer_thread.stop()
        self.cam_tune_thread.stop()
        self.cam_equal_thread.stop()
        self.proc_thread.stop()

        for thread in self.cap_threads.values():
            thread.stop()

        for cam in self.cams.values():
            cam.close()

    def init_cams(self):
        'Instantiate 3 camera objects'
        self.cams = {}
        for key in [CAM_R, CAM_L, CAM_E]:
            self.cams[key] = SingleCamera(which_cam = key)

    def init_cap_threads(self, mode):
        '''
        Instantiate and start 3 capture threads.
        Depending on the mode, resume different cap_threads (i.e. start main loop in the .run() method):
            MICRO mode: CAM_R & CAM_L
            AMBIENT mode: CAM_E & CAM_E

        :parameter
            mode: MICRO or AMBIENT
        '''
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

    def init_proc_thread(self):
        self.proc_thread = ProcessThread(cap_thread_R = self.active_cap_thread_R,
                                         cap_thread_L = self.active_cap_thread_L,
                                             mediator = self.mediator)

        self.proc_thread.start()
        self.proc_thread.resume() # proc_thread starts actively working the main loop by default

    def init_auto_cam_threads(self):
        self.cam_tune_thread = CamTuneThread(cap_thread = self.active_cap_thread_R,
                                               mediator = self.mediator)
        self.cam_tune_thread.start()

        self.cam_equal_thread = CamEqualThread(cap_thread_R = self.active_cap_thread_R,
                                               cap_thread_L = self.active_cap_thread_L,
                                                   mediator = self.mediator)
        self.cam_equal_thread.start()

    def init_align_thread(self):
        self.align_thread = AlignThread(process_thread = self.proc_thread,
                                              mediator = self.mediator)
        self.align_thread.start()
        # self.align_thread.resume()

    def init_writer_thread(self):
        self.writer_thread = WriterThread(process_thread = self.proc_thread,
                                                mediator = self.mediator)
        self.writer_thread.start()

    def set_view_mode(self, mode):

        # Do nothing if not changing the mode
        if mode == self.view_mode:
            return

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

        # Re-initialize the proc_thread
        self.proc_thread.set_cap_threads(thread_R = self.active_cap_thread_R,
                                         thread_L = self.active_cap_thread_L)

        # Update active capture threads to...
        #     the camera tuning and equalizing threads
        self.cam_tune_thread.set_cap_thread(self.active_cap_thread_R)
        self.cam_equal_thread.set_cap_threads(thread_R = self.active_cap_thread_R,
                                              thread_L = self.active_cap_thread_L)

        self.view_mode = mode

    def close(self):
        'Should be called upon software termination.'
        self.stop_video_thread()

    # Methods called by the controller object

    def snapshot(self, fname):
        img = self.proc_thread.get_display_image()
        cv2.imwrite(fname, img)

    def toggle_recording(self):
        self.writer_thread.toggle()

    def toggle_auto_offset(self):
        self.align_thread.toggle()

    def toggle_view_mode(self):
        if self.view_mode == MICRO:
            self.set_view_mode(mode=AMBIENT)
        else:
            self.set_view_mode(mode=MICRO)

        self.align_thread.zero_offset()

    def toggle_auto_cam(self):
        self.cam_tune_thread.toggle()
        self.cam_equal_thread.toggle()

    def zoom_in(self):
        self.proc_thread.zoom_in()

    def zoom_out(self):
        self.proc_thread.zoom_out()

    def stereo_reconstruction(self):
        self.proc_thread.pause()
        stereo.reconstruction(self.proc_thread, self.mediator)
        self.proc_thread.resume()

    def apply_depth_parameters(self, parameters):

        self.proc_thread.apply_depth_parameters(parameters)

    def apply_camera_parameters(self, data):

        which_cam = data['which_cam']
        parameters = data['parameters']

        self.cap_threads[which_cam].set_camera_parameters(parameters)

    def toggle_depth_map(self):
        self.proc_thread.computingDepth = not self.proc_thread.computingDepth

    def set_display_size(self, dim):
        '''
        Args:
            dim: a tuple of (width, height)
        '''
        self.proc_thread.change_display_size(width=dim[0], height=dim[1])

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



if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    core = WinduCore()
    sys.exit(app.exec_())


