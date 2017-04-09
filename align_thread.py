import numpy as np
import cv2, time, sys
from abstract_thread import *



class AlignThread(AbstractThread):
    '''
    This thread runs concurrently with the VideoThread,
    dynamically checking if the stereo pair of images are aligned.
    '''
    def __init__(self, process_thread, mediator):
        super(AlignThread, self).__init__()

        self.process_thread = process_thread
        self.mediator = mediator

        self.connect_signals(mediator = self.mediator,
                             signal_names = ['auto_offset_resumed',
                                             'auto_offset_paused' ,
                                             'set_info_text'      ])

        # Construct a queue of offset values
        self.X = np.zeros((10, ), np.float)
        self.Y = np.zeros((10, ), np.float)

        self.pausing = False
        self.isPaused = False
        self.mediator.emit_signal('auto_offset_resumed')

    def main(self):

        # Shift by one
        self.X[1:] = self.X[:-1]
        self.Y[1:] = self.Y[:-1]

        # Get the current offset value into the queue
        self.X[0], self.Y[0] = self.process_thread.detect_offset()

        # Sort the list of offset values
        # Remove the lowest and the highest one (outliers)
        # Average
        x_avg = np.average(np.sort(self.X)[1:-1])
        y_avg = np.average(np.sort(self.Y)[1:-1])

        self.emit_info(x_avg, y_avg)

        # Set the offset value, which effectly moves the left image
        self.process_thread.set_offset(x_avg, y_avg)

        # If the current offset value differs significantly from the average,
        #     meaning that there is more "active movements",
        # then speed up the loop to get back to a stable condition as soon as possible.
        if abs(self.Y[0] - y_avg) > 1:
            time.sleep(0.05)
        else:
            # Under stable condition, in which the current offset doesn't differ from the average,
            # Check alignment every ~1 second.
            time.sleep(1)

    def emit_info(self, x_off, y_off):

        text = 'Align thread x_offset, y_offset: {}, {}'.format(x_off, y_off)

        data = {'line': 6,
                'text': text}

        self.mediator.emit_signal( signal_name = 'set_info_text',
                                   arg = data )

    def before_resuming(self):
        self.mediator.emit_signal('auto_offset_resumed')
        return True

    def after_paused(self):
        self.process_thread.set_offset(0, 0)
        self.mediator.emit_signal('auto_offset_paused')
        return True

    def set_process_thread(self, thread):
        self.process_thread = thread

    def zero_offset(self):
        self.X = np.zeros((10, ), np.float)
        self.Y = np.zeros((10, ), np.float)

        self.process_thread.set_offset(0, 0)




