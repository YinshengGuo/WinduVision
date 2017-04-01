import numpy as np
import cv2, time, sys
from abstract_thread import *



class EmptyThread(AbstractThread):

    def __init__(self, mediator):
        super(EmptyThread, self).__init__()

        self.mediator = mediator

        self.connect_signals(mediator = self.mediator,
                             signal_names = ['signal_1', 'signal_2'])

    def main(self):
        pass

    def before_resuming(self):
        return True

    def after_paused(self):
        return True



