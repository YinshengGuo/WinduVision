import time, threading, abc



class AbstractThread(threading.Thread):

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __init__(self, pause_at_start=False):
        super(AbstractThread, self).__init__()

        self.stopping = False
        self.isStopped = False
        self.pausing = pause_at_start
        self.isPaused = pause_at_start

        self.dt = 0.1 # Dwelling time for an iteration of empty loops
        self.fps = 0 # Not timing the main loop

        self.signal_names = None
        self.mediator = None

    @abc.abstractmethod
    def main(self):
        time.sleep(self.dt)

    def connect_signals(self, mediator, signal_names):
        '''
        Call the mediator to connect signals to the gui.
        These are the signals to be emitted dynamically during runtime.

        Each signal is defined by a unique str signal name.

        The parameter 'connect' specifies whether connect or disconnect signals.
        '''

        self.signal_names = signal_names
        self.mediator = mediator

        mediator.connect_signals(signal_names)

    def disconnect_signals(self):

        if not self.mediator is None:
            self.mediator.disconnect_signals(self.signal_names)

    def run(self):

        t0 = time.clock()

        while not self.stopping:

            # Pausing the loop (or not)
            if self.pausing:
                self.isPaused = True
                time.sleep(self.dt)
                continue
            else:
                self.isPaused = False

            self.main()

            if self.fps == 0:
                continue

            # Time the loop
            while (time.clock() - t0) < (1./self.fps):
                # Sleeping for < 15 ms is not reliable across different platforms.
                # Windows PCs generally have a minimum sleeping time > ~15 ms...
                #     making this timer exceeding the specified period.
                time.sleep(0.001)

            t0 = time.clock()

        self.disconnect_signals()
        self.isStopped = True

    def toggle(self):
        if self.isPaused:
            self.resume()
        else:
            self.pause()

    def before_resuming(self):
        return True

    def resume(self):
        if self.isPaused:
            ret = self.before_resuming()
            if not ret:
                print 'The method before_resuming() returns False. Not able to resume.'
                return

            self.pausing = False
            # Wait until the main loop is really resumed before completing this method call
            while self.isPaused:
                time.sleep(self.dt)

    def pause(self):
        if not self.isPaused:
            self.pausing = True
            # Wait until the main loop is really paused before completing this method call
            while not self.isPaused:
                time.sleep(self.dt)

            ret = self.after_paused()
            if not ret:
                print 'The method after_paused() returns False. Not properly paused.'

    def after_paused(self):
        return True

    def stop(self):
        '''
        To terminate the thread.
        '''

        # Shut off main loop in self.run()
        self.stopping = True

        # Wait until the run() method reaches the final line before completing this method call
        while not self.isStopped:
            time.sleep(self.dt)

        ret = self.after_stopped()
        if not ret:
            print 'The method after_stopped() returns False. Thread not properly terminated.'

    def after_stopped(self):
        return True

    def set_fps(self, fps):
        if fps > 0:
            self.fps = fps


