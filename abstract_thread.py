import time, threading



class AbstractThread(threading.Thread):

    def __init__(self, mediator):
        super(AbstractThread, self).__init__()

        # Mediator emits signal to the gui object
        self.mediator = mediator

        self.stopping = False
        self.pausing = False
        self.isPaused = False
        self.dt = 0.01 # Minimum running time for a single iteration of any empty loop

    def __init__signals(self, signal_names, connect=True):
        '''
        Call the mediator to connect signals to the gui.
        These are the signals to be emitted dynamically during runtime.

        Each signal is defined by a unique str signal name.

        The parameter 'connect' specifies whether connect or disconnect signals.
        '''

        if connect:
            self.mediator.connect_signals(signal_names)
        else:
            self.mediator.disconnect_signals(signal_names)

    def run(self):

        while not self.stopping:

            # Pausing the loop (or not)
            if self.pausing:
                self.isPaused = True
                time.sleep(self.dt)
                continue
            else:
                self.isPaused = False

            self.main()

    def main(self):
        time.sleep(self.dt)

    def pause(self):
        self.pausing = True
        # Wait until the main loop is really paused before completing this method call
        while not self.isPaused:
            time.sleep(self.dt)
        return

    def resume(self):
        self.pausing = False
        # Wait until the main loop is really resumed before completing this method call
        while self.isPaused:
            time.sleep(self.dt)
        return

    def stop(self):
        'Called to terminate the video thread.'

        # Shut off main loop in self.run()
        self.stopping = True


