import numpy as np
import cv2, time, sys, threading, os, json
from abstract_thread import *



class WriterThread(AbstractThread):

    def __init__(self, process_thread, mediator):
        super(WriterThread, self).__init__()

        self.process_thread = process_thread
        self.mediator = mediator

        self.__init__parameters()

        self.set_fps(self.fps)

        self.connect_signals(mediator = self.mediator,
                             signal_names = ['recording_starts',
                                             'recording_ends'  ,
                                             'set_time_label'  ])

        self.writer = None

    def __init__parameters(self):

        self.temp_video_fname = 'temp.avi'

        # Some of the available codecs on native Windows PC: 'DIB ', 'I420', 'IYUV'...
        #     which are all uncompressive codecs
        # The compressive X264 codec needs to be installed seperately before use
        self.fourcc = cv2.cv.CV_FOURCC(*'X264')

        with open('parameters/video_writer.json') as fh:
            p = json.loads(fh.read())

        for name, value in p.items():
            setattr(self, name, value)
            print name, getattr(self, name)

    def main(self):

        if self.writer:
            # Get the processed image from the process thread
            img = self.process_thread.get_display_image()

            # If the image does not match the pre-defined video dimension...
            #     resize it to the correct video dimension
            h, w, _ = img.shape
            H, W = self.img_height, self.img_width
            if h != H or w != W:

                Sx = self.img_width / float(w) # scale_x
                Sy = self.img_height / float(h) # scale_y

                # the transformatio matrix
                mat = np.float32([ [Sx, 0 , 0] ,
                                   [0 , Sy, 0] ])

                img = cv2.warpAffine(img, mat, (W, H))

            self.writer.write(img)
            self.emit_time_label()

    def emit_time_label(self):
        S = int( time.clock() - self.recording_start_time )

        H = S / 3600
        S = S - H * 3600
        M = S / 60
        S = S - M * 60

        H = str(H)
        M = '%02d' % M
        S = '%02d' % S

        text = '{}:{}:{}'.format(H, M, S)
        self.mediator.emit_signal('set_time_label', text)

    def before_resuming(self):

        # Create VideoWriter object
        self.writer = cv2.VideoWriter(self.temp_video_fname,
                                      self.fourcc,
                                      self.fps,
                                      (self.img_width, self.img_height))

        if not self.writer.isOpened():
            self.writer = None
            print 'Video writer could not be opened.'
            return False

        # Change the icon of the gui button
        self.mediator.emit_signal('recording_starts')

        self.recording_start_time = time.clock()

        return True

    def after_paused(self):

        self.writer.release()
        self.writer = None

        # Signal gui to change the icon of the button...
        #     and let the user to rename the temp file
        self.mediator.emit_signal('recording_ends', arg=self.temp_video_fname)
        self.mediator.emit_signal('set_time_label', '')
        return True

    def after_stopped(self):

        if not self.isPaused:
            self.writer.release()
            os.remove(self.temp_video_fname)

        return True

    def set_process_thread(self, thread):
        self.process_thread = thread


