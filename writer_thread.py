import numpy as np
import cv2, time, sys, threading, os



class WriterThread(threading.Thread):

    def __init__(self, process_thread, mediator):
        super(WriterThread, self).__init__()

        self.process_thread = process_thread
        self.mediator = mediator

        self.__init__signals()
        self.__init__parameters()

    def __init__signals(self, connect=True):
        '''
        Call the mediator to connect signals to the gui.
        These are the signals to be emitted dynamically during runtime.

        Each signal is defined by a unique str signal name.

        The parameter 'connect' specifies whether connect or disconnect signals.
        '''
        signal_names = ['recording_starts', 'recording_ends']

        if connect:
            self.mediator.connect_signals(signal_names)
        else:
            self.mediator.disconnect_signals(signal_names)

    def __init__parameters(self):

        self.stopping = False
        self.pausing = True
        self.isPaused = True

        self.fps = 30.0
        self.temp_video_fname = 'temp.avi'

        # Some of the available codecs on native Windows PC: 'DIB ', 'I420', 'IYUV'...
        #     which are all uncompressive codecs
        # The compressive X264 codec needs to be installed seperately before use
        self.fourcc = cv2.cv.CV_FOURCC(*'X264')

        img = self.process_thread.get_display_image()
        self.img_height, self.img_width, _ = img.shape

    def run(self):

        t0 = time.clock()

        while not self.stopping:

            # Pausing the loop (or not)
            if self.pausing:
                self.isPaused = True
                time.sleep(0.1)
                continue
            else:
                self.isPaused = False

            img = self.process_thread.get_display_image()
            self.writer.write(img)

            # Time the loop
            while (time.clock() - t0) < (1./self.fps):
                # Sleeping for < 15 ms is not reliable across different platforms.
                # Windows PCs generally have a minimum sleeping time > ~15 ms...
                #     making this timer exceeding the specified period.
                time.sleep(0.001)

            t0 = time.clock()

        # Disconnect signals from the gui object when the thread is done
        self.__init__signals(connect=False)

    def toggle_recording(self):

        if self.isPaused:
            self.resume()
        else:
            self.pause(save_file=True)

    def pause(self, save_file):

        if self.isPaused:
            return

        self.pausing = True
        # Wait until the main loop is really paused before completing this method call
        while not self.isPaused:
            time.sleep(0.1)

        self.writer.release()

        if save_file:
            # Signal gui to change the icon of the button...
            #     and let the user to rename the temp file
            self.mediator.emit_signal('recording_ends', arg=self.temp_video_fname)
        else:
            os.remove(self.temp_video_fname)

    def resume(self):

        if not self.isPaused:
            return

        # Create VideoWriter object
        self.writer = cv2.VideoWriter(self.temp_video_fname,
                                      self.fourcc,
                                      self.fps,
                                      (self.img_width, self.img_height))

        if not self.writer.isOpened():
            print 'Video writer could not be opened.'
            return

        self.pausing = False
        # Wait until the main loop is really resumed before completing this method call
        while self.isPaused:
            time.sleep(0.1)

        # Change the icon of the gui button
        self.mediator.emit_signal('recording_starts')

    def stop(self):
        '''
        Called to terminate the thread.
        '''

        # Pause without saving the file
        self.pause(save_file=False)

        # Shut off main loop in self.run()
        self.stopping = True

    def set_process_thread(self, thread):
        self.process_thread = thread

