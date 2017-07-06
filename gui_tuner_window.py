import cv2, time, sys, threading, os, json
from PyQt4 import QtCore, QtGui, QtOpenGL
from root_constants import *



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

        self.parent = parent
        self.name = name
        self.min = min
        self.max = max
        self.value = value
        self.interval = interval

        self.QLabel_name = QtGui.QLabel(self) # QLabel showing name
        self.QLabel_value = QtGui.QLabel(self) # QLabel showing value
        self.QSlider = QtGui.QSlider(QtCore.Qt.Horizontal, self) # QSlider

        # Create and set H box layout
        self.hbox = QtGui.QHBoxLayout()
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

        # Notify the parent.
        # Let the parent decide what to do with the value changed.
        self.parent.apply_parameter(self.name, value)



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

        self.main_vbox = QtGui.QVBoxLayout()
        self.setLayout(self.main_vbox)

        self.widgets = {} # a dictionary of widgets, indexed by the name of each parameter

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

        # Add the widget to the dictionary
        self.widgets[name] = widget
        # Add the widget to the V box
        self.main_vbox.insertWidget(len(self.main_vbox), widget)

    def set_parameter(self, name, value):
        '''
        Set the widget slider value
        '''
        # If the name is not present in self.parameters then do nothing
        if self.widgets.get(name, None) is None:
            return
        self.widgets[name].setValue(value)

    def apply_parameter(self, name, value):
        '''
        To be overridden.
        Decides what to do when the child widget method setValue() is called.
        '''
        pass



class CameraTunerWindow(TunerWindow):
    '''
    Inherits from the TunerWindow class.

    The business logics for the camera imaging parameters is specified in this class.

    This class also manages the transfer of camera parameters to the core object.
    '''
    def __init__(self, controller, which_cam):
        super(CameraTunerWindow, self).__init__()

        self.controller = controller
        self.which_cam = which_cam

        self.setWindowIcon(QtGui.QIcon('icons/windu_vision.png'))
        self.setMinimumWidth(600)

        title = {CAM_R: 'Right Camera'  ,
                 CAM_L: 'Left Camera'   ,
                 CAM_E: 'Ambient Camera'}

        self.setWindowTitle(title[which_cam])

        self.add_parameter(name='brightness'    , min=0   , max=255 , value=0   , interval=5  )
        self.add_parameter(name='contrast'      , min=0   , max=255 , value=0   , interval=5  )
        self.add_parameter(name='saturation'    , min=0   , max=255 , value=0   , interval=5  )
        self.add_parameter(name='gain'          , min=0   , max=127 , value=0   , interval=1  )
        self.add_parameter(name='exposure'      , min=-7  , max=-1  , value=-7  , interval=1  )
        self.add_parameter(name='white_balance' , min=3000, max=6500, value=3000, interval=100)
        self.add_parameter(name='focus'         , min=0   , max=255 , value=0   , interval=5  )

        # self.isApplying is a boolean that decides whether or not...
        #   to apply the parameter to the camera hardware
        self.isApplying = False
        # When initiating GUI, i.e. executing self.__init__load_parameters()...
        #   the core object is not ready to configure the camera hardware yet...
        #   therefore do NOT apply parameters to the camera hardware
        self.__init__load_parameters()
        # When initiation is done, the core object is ready...
        #   so the parameter can be applied to configure the camera hardware
        self.isApplying = True

    def __init__load_parameters(self):
        '''
        Load parameters from the .json file, and set the values of the QSliders
        '''
        filepath = 'parameters/' + self.which_cam + '.json'
        with open(filepath, 'r') as fh:
            parameters = json.loads(fh.read())

        for name, value in parameters.items():
            self.set_parameter(name, value)

    def apply_parameter(self, name, value):
        '''
        Called by the child widget method applyValue().
        Transfers parameters to the core object via the controller.
        '''

        # Decides whether or not to apply the parameter to configure the camera hardware
        if not self.isApplying:
            return

        data = {'which_cam': self.which_cam,
                'parameters': {name: value}}

        self.controller.call_method( method_name = 'apply_camera_parameters',
                                             arg = data                     )

    def auto_cam_resumed(self):
        # When camera is in auto mode,
        #   we only want the GUI sliders to DISPLAY the parameter but NOT configuring cameras
        #   so do NOT apply parameters to the camera hardware
        self.isApplying = False

    def auto_cam_paused(self):
        self.isApplying = True



class CameraTunerWindowSet(object):
    '''
    This class encapsulates the three CameraTunerWindow: CAM_R, CAM_L, CAM_E

    This class should have the basic methods (interface) that the CameraTunerWindow has...
      for external method calling
    '''
    def __init__(self, controller):
        self.windows = {}
        # Instantiate three CameraTunerWindow objects
        # Collect them in a dictionary
        for cam in [CAM_R, CAM_L, CAM_E]:
            self.windows[cam] = CameraTunerWindow(controller=controller, which_cam=cam)

    def show(self):
        for i, win in enumerate(self.windows.values()):
            win.move(200+200*i, 200)
            win.show()

    def hide(self):
        for win in self.windows.values():
            win.hide()

    def close(self):
        for win in self.windows.values():
            win.close()

    def set_parameter(self, which_cam, name, value):
        self.windows[which_cam].set_parameter(name, value)

    def auto_cam_resumed(self):
        for win in self.windows.values():
            win.auto_cam_resumed()

    def auto_cam_paused(self):
        for win in self.windows.values():
            win.auto_cam_paused()



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
        for p in self.parameters.values():
            parms[p.name] = p.value

        self.controller.call_method( method_name = 'apply_depth_parameters',
                                             arg = parms                   )



