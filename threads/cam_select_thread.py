import numpy as np
import cv2, time, sys, threading



class CamSelectThread(threading.Thread):
    def __init__(self, mediator):
        super(CamSelectThread, self).__init__()

        self.mediator = mediator

        self.__init__signals()

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

            cap = cv2.VideoCapture(id)

            if cap.isOpened():
                ret, img = cap.read()

                data = {'id': id, 'img': img}

                cap.release()

                self.mediator.emit_signal( signal_name = 'show_current_cam',
                                                   arg = data)
                while self.isWaiting:
                    time.sleep(0.1)

            else:
                print 'Camera id: {} not available'.format(id)

        self.mediator.emit_signal( signal_name = 'select_cam_done' )

        # Pause a short bit of time before disconnecting the signal
        # Without this pause, often the signal will not be successfully sent
        time.sleep(0.1)

        # Disconnect signals from the gui object when the thread is done
        self.__init__signals(connect=False)


