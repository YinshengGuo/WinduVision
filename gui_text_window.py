from PyQt4 import QtCore, QtGui, QtOpenGL



class TextWindow(QtGui.QWidget):
    def __init__(self):
        super(TextWindow, self).__init__()

        self.setWindowTitle('Info')
        self.setWindowIcon(QtGui.QIcon('icons/windu_vision.png'))
        self.setGeometry(150, 150, 512, 256)
        self.setFixedSize(512, 256)

        self.font = QtGui.QFont()
        self.font.setFamily('Segoe UI')
        self.font.setBold(False)
        self.font.setPixelSize(14)

        self.textbox = QtGui.QLabel(self)
        self.textbox.setGeometry(0, 0, 512, 256)
        self.textbox.setAlignment(QtCore.Qt.AlignLeft)
        self.textbox.setFont(self.font)

    def setText(self, text):
        self.textbox.setText(text)


