import time, threading, abc



class AbstractThread(threading.Thread):

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __init__(self):
        super(AbstractThread, self).__init__()

        self.stopping = False
        self.isStopped = False

        # The default initiation state is paused
        # Therefore when the self.start() method is invoked...
        #     the main loop does not go through the self.main() method.
        # The reason of this additional layer of control is to let...
        #     higher-level classes decide whether to do the main() task or not.
        self.pausing = True
        self.isPaused = True

        self.dt = 0.01 # The minimum dwelling time for an iteration of an empty loop
        self.fps = 0 # If == 0, then no timing the main loop

        self.signal_names = None
        self.mediator = None

    @abc.abstractmethod
    def main(self):
        '''
        An abstract method required to be defined in subclasses.
        This is the main task to be done in the thread.
        '''
        pass

    def connect_signals(self, mediator, signal_names):
        '''
        Call the mediator to connect signals to the gui.
        These are the signals to be emitted dynamically during runtime.

        Each signal is defined by a unique str signal name.

        :parameter
            mediator: the mediator object
            signal_names: a list of strings as signal names
        '''

        self.signal_names = signal_names
        self.mediator = mediator

        mediator.connect_signals(signal_names)

    def disconnect_signals(self):

        if not self.mediator is None:
            self.mediator.disconnect_signals(self.signal_names)

    def run(self):

        while not self.stopping:

            # Pausing the loop (or not)
            if self.pausing:
                self.isPaused = True
                time.sleep(self.dt)
                continue
            else:
                self.isPaused = False

            # The very main task the thread is doing which...
            #     must be defined in subclasses.
            self.main()

            # Skip the timing part if self.fps == 0
            if self.fps == 0:
                continue

            # Time the loop
            while (time.clock() - self.t0) < (1./self.fps):
                # Sleeping for < 15 ms is not reliable across different platforms.
                # Windows PCs generally have a minimum sleeping time > ~15 ms...
                #     making this timer exceeding the specified period.
                time.sleep(0.001)
            self.t0 = time.clock()

        self.disconnect_signals()
        self.isStopped = True

    def toggle(self):
        if self.isPaused:
            self.resume()
        else:
            self.pause()

    def before_resuming(self):
        'This method must return True/False'
        return True

    def resume(self):
        if self.isPaused:
            ret = self.before_resuming()
            if not ret:
                print 'The method before_resuming() returns False. Not able to resume.'
                return

            self.t0 = time.clock() # The very first time point before going through self.main()

            self.pausing = False
            # Wait until the main loop is really resumed before completing this method call.
            # Just to make sure it's really resumed to avoid any downstream conflict.
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
        'This method must return True/False'
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
        'This method must return True/False'
        return True

    def set_fps(self, fps):
        if fps > 0:
            self.fps = fps


