import cv2, time, sys, threading, os, json
from PyQt4 import QtCore, QtGui, QtOpenGL
from constants import *



class SliderWidget(QtGui.QWidget):
    '''
    This widget wraps a single parameter in the TunerWindow.

    Name, value, min, max, interval are stored in this object.

    Three gui elements are included to display the information of the parameter:
      1) QLabel showing name
      2) QLabel showing value
      3) QSlider
    '''
    def __init__(self, parent, name, min, max, value, interval):
        super(SliderWidget, self).__init__(parent)

        self.name = name
        self.min = min
        self.max = max
        self.value = value
        self.interval = interval

        self.hbox = QtGui.QHBoxLayout()
        self.QLabel_name = QtGui.QLabel(self)
        self.QLabel_value = QtGui.QLabel(self)
        self.QSlider = QtGui.QSlider(QtCore.Qt.Horizontal, self)

        self.setLayout(self.hbox)

        self.hbox.addWidget(self.QLabel_name)
        self.hbox.addWidget(self.QLabel_value)
        self.hbox.addWidget(self.QSlider)

        self.QLabel_name.setText(name)
        self.QLabel_value.setText(str(value))

        self.QSlider.setMinimum(min)
        self.QSlider.setMaximum(max)
        self.QSlider.setValue(value)
        self.QSlider.setSingleStep(interval)
        self.QSlider.setTickInterval(interval)
        self.QSlider.setTickPosition(QtGui.QSlider.TicksBelow)

        self.QSlider.valueChanged.connect(self.setValue)

    def setValue(self, value):

        # Round the value to fit the interval
        value = value - self.min
        value = round( value / float(self.interval) ) * self.interval
        value = int( value + self.min )

        self.value = value
        self.QSlider.setValue(value)
        self.QLabel_value.setText(str(value))



class TunerWindow(QtGui.QWidget):
    '''
    A gui template window for tuning parameters.

    This class does not contain any business logic.
    All it does is to provide an interface to adjust parameters through gui.

    Each parameter is wrapped in a 'block' of SliderWidget object.

    Properties (name, min, max, value, interval)
    of each parameter is stored in the SliderWidget object.
    '''
    def __init__(self):
        super(TunerWindow, self).__init__()

        # self.setMinimumWidth(600)
        # self.setMaximumWidth(600)

        self.main_vbox = QtGui.QVBoxLayout()
        self.setLayout(self.main_vbox)

        self.btn_hbox = QtGui.QHBoxLayout()
        self.main_vbox.addLayout(self.btn_hbox)

        K = [('ok'    ,'OK'    ),
             ('cancel','Cancel'),
             ('apply' ,'Apply' )]

        self.btn = {}

        for key, name in K:
            self.btn[key] = QtGui.QPushButton(name, self)
            self.btn[key].clicked.connect(getattr(self, key))
            self.btn_hbox.addWidget( self.btn[key] )

        self.parameters = []

    def apply_parameter(self):
        '''
        Supposed to be overridden.
        Defines what to do when ok() or apply() are called.
        '''
        pass

    def ok(self):
        self.apply_parameter()
        self.hide()

    def cancel(self):
        self.hide()

    def apply(self):
        self.apply_parameter()

    def add_parameter(self, name, min, max, value, interval):
        '''
        Add a new SliderWidget object holding all information of the new parameter.
        '''
        widget = SliderWidget(parent   = self,
                              name     = name,
                              min      = min,
                              max      = max,
                              value    = value,
                              interval = interval)

        self.parameters.append(widget)

        self.main_vbox.insertWidget(len(self.main_vbox)-1, widget)

    def set_parameter(self, name, value):

        # Iterate over all widgets to search for the widget that has the matched name
        for widget in self.parameters:
            if widget.name == name:
                widget.setValue(value)



class DepthTunerWindow(TunerWindow):
    '''
    Inherits from the TunerWindow class.

    The business logics for the actual depth parameters
    to be tuned is specified in this class.

    This class also manages the transfer of depth parameters
    to the core object.
    '''
    def __init__(self, controller):
        super(DepthTunerWindow, self).__init__()

        self.controller = controller

        self.setWindowIcon(QtGui.QIcon('icons/windu_vision.png'))
        self.setWindowTitle('Stereo Depth Parameters')

        self.setMinimumWidth(600)

        self.add_parameter(name='ndisparities', min=0, max=160, value=32, interval=16)
        self.add_parameter(name='SADWindowSize', min=5, max=105, value=31, interval=2)

    def apply_parameter(self):
        '''
        Transfers parameters to the core object via the controller.
        '''
        parms = {}
        for p in self.parameters:
            parms[p.name] = p.value

        self.controller.call_method( method_name = 'apply_depth_parameters',
                                             arg = parms                   )



class CameraTunerWindow(TunerWindow):
    '''
    Inherits from the TunerWindow class.

    The business logics for the camera imaging parameters
    is specified in this class.

    This class also manages the transfer of camera parameters
    to the core object.
    '''
    def __init__(self, controller, which_cam):
        super(CameraTunerWindow, self).__init__()

        self.controller = controller
        self.which_cam = which_cam

        self.setWindowIcon(QtGui.QIcon('icons/windu_vision.png'))
        self.setMinimumWidth(600)

        if which_cam == CAM_R:
            title = 'Right Camera'
        elif which_cam == CAM_L:
            title = 'Left Camera'
        else:
            title = 'Ambient Camera'

        self.setWindowTitle(title)

        filepath = 'parameters/' + which_cam + '.json'
        with open(filepath, 'r') as fh:
            parms = json.loads(fh.read())

        self.add_parameter(name='brightness'    , min=0   , max=255 , value=parms['brightness']   , interval=5  )
        self.add_parameter(name='contrast'      , min=0   , max=255 , value=parms['contrast']     , interval=5  )
        self.add_parameter(name='saturation'    , min=0   , max=255 , value=parms['saturation']   , interval=5  )
        self.add_parameter(name='gain'          , min=0   , max=127 , value=parms['gain']         , interval=1  )
        self.add_parameter(name='exposure'      , min=-7  , max=-1  , value=parms['exposure']     , interval=1  )
        self.add_parameter(name='white_balance' , min=3000, max=6500, value=parms['white_balance'], interval=100)
        self.add_parameter(name='focus'         , min=0   , max=255 , value=parms['focus']        , interval=5  )

    def apply_parameter(self):
        '''
        Transfers parameters to the core object via the controller.
        '''
        parms = {}
        for p in self.parameters:
            parms[p.name] = p.value

        data = {'which_cam': self.which_cam, 'parameters': parms}

        self.controller.call_method( method_name = 'apply_camera_parameters',
                                             arg = data                     )

    def update_parameter(self):

        filepath = 'parameters/' + self.which_cam + '.json'
        with open(filepath, 'r') as fh:
            parameters = json.loads(fh.read())

        for name, value in parameters.items():
            self.set_parameter(name, value)


