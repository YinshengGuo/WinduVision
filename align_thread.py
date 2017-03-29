import numpy as np
import cv2, time, sys, threading



class AlignThread(threading.Thread):
    '''
    This thread runs concurrently with the VideoThread,
    dynamically checking if the stereo pair of images are aligned.
    '''
    def __init__(self, process_thread, mediator):
        super(AlignThread, self).__init__()

        self.process_thread = process_thread
        self.mediator = mediator

        self.__init__signals()

        self.stopping = False
        self.pausing = True
        self.isPaused = True

        self.toggle() # Turn on alignment

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
            X[0], Y[0] = self.process_thread.detect_offset()

            # Sort the list of offset values
            # Remove the lowest and the highest one (outliers)
            # Average
            x_avg = np.average(np.sort(X)[1:-1])
            y_avg = np.average(np.sort(Y)[1:-1])

            # Set the offset value, which effectly moves the left image
            self.process_thread.set_offset(x_avg, y_avg)

            # If the current offset value differs significantly from the average,
            #     meaning that there is more "active movements",
            # then speed up the loop to get back to a stable condition as soon as possible.
            if abs(Y[0] - y_avg) > 1:
                time.sleep(0.05)
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

    def set_process_thread(self, thread):
        self.process_thread = thread

