from PyQt4 import QtCore, QtGui, QtOpenGL



class TextWindow(QtGui.QWidget):
    def __init__(self):
        super(TextWindow, self).__init__()

        self.setWindowTitle('Info')
        self.setWindowIcon(QtGui.QIcon('icons/windu_vision.png'))
        self.setGeometry(150, 150, 512, 512)

        self.font = QtGui.QFont()
        self.font.setFamily('Consolas')
        self.font.setBold(False)
        self.font.setPixelSize(14)

        self.vbox = QtGui.QVBoxLayout()
        self.setLayout(self.vbox)
        self.textboxes = []
        for i in xrange(10):
            tb = QtGui.QLabel(self)
            tb.setAlignment(QtCore.Qt.AlignLeft)
            tb.setAlignment(QtCore.Qt.AlignVCenter)
            tb.setFont(self.font)
            self.textboxes.append(tb)
            self.vbox.insertWidget(len(self.vbox), tb)

    def setText(self, line, text):
        self.textboxes[line].setText(text)


