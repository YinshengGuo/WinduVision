from PyQt4 import QtCore, QtGui, QtOpenGL



class ProgressBar(QtGui.QProgressBar):
    def __init__(self):
        super(ProgressBar, self).__init__()

        self.setWindowIcon(QtGui.QIcon('icons/windu_vision.png'))
        self.setGeometry(200, 200, 640, 45)
        self.setFixedSize(640, 45)
        self.setTextVisible(True)

    def progress_update(self, text_value):
        if not self.isVisible():
            self.show()

        text, value = text_value
        self.setWindowTitle(text)
        self.setValue(value)

        if value == 100:
            time.sleep(0.5)
            self.hide()

