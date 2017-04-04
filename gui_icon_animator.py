from PyQt4 import QtCore, QtGui, QtOpenGL



class IconAnimator(QtCore.QTimer):

    def __init__(self, QAction, QIcons):

        super(IconAnimator, self).__init__()

        self.QAction = QAction
        self.QIcons = QIcons
        self.i = 0
        self.timeout.connect(self.animate)

    def animate(self):

        self.i += 1
        if self.i == len(self.QIcons):
            self.i = 0

        self.QAction.setIcon(self.QIcons[self.i])


