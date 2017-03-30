import numpy as np
import cv2, time, sys, threading, os
from abstract_thread import *



class WriterThread(AbstractThread):

    def __init__(self, process_thread, mediator):
        super(WriterThread, self).__init__(pause_at_start=True)

        self.process_thread = process_thread
        self.mediator = mediator

        self.__init__parameters()

        self.set_fps(30)

        self.connect_signals(mediator = self.mediator,
                             signal_names = ['recording_starts', 'recording_ends'])

        self.writer = None

    def __init__parameters(self):

        self.temp_video_fname = 'temp.avi'

        # Some of the available codecs on native Windows PC: 'DIB ', 'I420', 'IYUV'...
        #     which are all uncompressive codecs
        # The compressive X264 codec needs to be installed seperately before use
        self.fourcc = cv2.cv.CV_FOURCC(*'X264')

        img = self.process_thread.get_display_image()
        self.img_height, self.img_width, _ = img.shape

    def main(self):

        if self.writer:
            img = self.process_thread.get_display_image()
            self.writer.write(img)

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
        return True

    def after_paused(self):

        self.writer.release()
        self.writer = None

        # Signal gui to change the icon of the button...
        #     and let the user to rename the temp file
        self.mediator.emit_signal('recording_ends', arg=self.temp_video_fname)
        return True

    def after_stopped(self):

        if not self.isPaused:
            self.writer.release()
            os.remove(self.temp_video_fname)

        return True

    def set_process_thread(self, thread):
        self.process_thread = thread


