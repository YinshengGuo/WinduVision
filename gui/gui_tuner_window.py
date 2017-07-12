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

        self.QSlider.sliderReleased.connect(self.slider_released)

    def slider_released(self):
        '''
        User invoked action (mouse release event) => Notify the parent object
        '''
        value = self.QSlider.value()
        # Round the value to fit the interval
        value = value - self.min
        value = round( value / float(self.interval) ) * self.interval
        value = int( value + self.min )

        self.value = value
        self.QSlider.setValue(value)
        self.QLabel_value.setText(str(value))

        # Notify the parent that the user changed the value with mouse.
        # Let the parent decide what to do with the gui event.
        self.parent.user_changed_value(self.name, value)

    def set_value(self, value):
        '''
        Set the value of self.QSlider and self.QLabel_value
        Note that this only sets the displayed value without invoking any downstream action
        This method is not invoked by user interaction
        This method is only for displaying value
        '''
        if value >= self.min and value <= self.max:
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

        self.vbox = QtGui.QVBoxLayout()
        self.setLayout(self.vbox)

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
        # Insert the widget to the last row of the V box
        self.vbox.insertWidget(len(self.vbox), widget)

    def add_widget(self, widget):
        '''
        Insert QWidget object to the last row of self.vbox (QVBoxLayout)
        '''
        self.vbox.insertWidget(len(self.vbox), widget)

    def set_parameter(self, name, value):
        '''
        Set the widget slider value
        '''
        # If the name is not present in self.parameters then do nothing
        if self.widgets.get(name, None) is None:
            return
        self.widgets[name].set_value(value)

    def user_changed_value(self, name, value):
        '''
        To be overridden.
        Decides what to do when the child widget slider_released() method is called...
            which is invoked upon user mouse action
        '''
        pass



class CameraTunerWindow(TunerWindow):
    '''
    Inherits from the TunerWindow class.

    The business logics for the camera imaging parameters is specified in this class.

    This class manages the transfer of camera parameters to the core object.
    '''
    def __init__(self, controller, which_cam, paired, parent):
        super(CameraTunerWindow, self).__init__()

        self.controller = controller
        self.which_cam = which_cam
        self.parent = parent

        self.setWindowIcon(QtGui.QIcon('icons/windu_vision.png'))
        self.setMinimumWidth(600)

        title = {CAM_R: 'Right Camera'  ,
                 CAM_L: 'Left Camera'   ,
                 CAM_E: 'Ambient Camera'}
        self.setWindowTitle(title[which_cam])

        self.__init__load_parameters()

        if paired:
            # If this CameraTunerWindow object is paired to another camera, e.g. left and right cameras
            #     then add a check box for toggling the synchronization of the two cameras
            self.sync_box = QtGui.QCheckBox(parent=self)
            self.sync_box.setText('Sync Control')
            self.sync_box.toggled.connect(self.user_changed_sync)
            self.add_widget(self.sync_box)

    def __init__load_parameters(self):
        '''
        Load parameters from the .json file, and set the values of the QSliders
        '''
        filepath = 'parameters/' + self.which_cam + '.json'
        with open(filepath, 'r') as fh:
            P = json.loads(fh.read())

        self.add_parameter(name='brightness'    , min=0   , max=255 , value=P['brightness'   ], interval=5  )
        self.add_parameter(name='contrast'      , min=0   , max=255 , value=P['contrast'     ], interval=5  )
        self.add_parameter(name='saturation'    , min=0   , max=255 , value=P['saturation'   ], interval=5  )
        self.add_parameter(name='gain'          , min=0   , max=127 , value=P['gain'         ], interval=1  )
        self.add_parameter(name='exposure'      , min=-7  , max=-1  , value=P['exposure'     ], interval=1  )
        self.add_parameter(name='white_balance' , min=3000, max=6500, value=P['white_balance'], interval=100)
        self.add_parameter(name='focus'         , min=0   , max=255 , value=P['focus'        ], interval=5  )

        self.isManual = {}
        for name in ['brightness', 'contrast', 'saturation', 'gain', 'exposure', 'white_balance', 'focus']:
            self.isManual[name] = True

    def user_changed_sync(self):
        '''
        User (mouse action) check or uncheck the self.sync_box
        '''
        self.parent.user_changed_sync(self.which_cam, self.sync_box.isChecked())

    def set_sync(self, isChecked):
        '''
        Accessed by external object to set the state of self.sync_box
        '''
        self.sync_box.setChecked(isChecked)

    def user_changed_value(self, name, value):
        '''
        Called by the child widget method slider_released().
        Transfers parameters to the core object via the controller.
        '''
        self.parent.user_changed_value(self.which_cam, name, value)
        self.apply_parameter(name, value)

    def apply_parameter(self, name, value):
        '''
        Apply the camera parameter value to the core object throught the controller
            i.e. configuring the camera hardware
        '''

        # Decides whether or not to apply the parameter to configure the camera hardware
        if not self.isManual[name]:
            return

        data = {'which_cam': self.which_cam,
                'parameters': {name: value}}

        self.controller.call_method( method_name = 'apply_camera_parameters',
                                             arg = data                     )

    def auto_cam_resumed(self):
        '''
        Auto camera tuning mainly works on gain and exposure
        So set these two parameters to isManual = False...
            to prevent user from changing it
        '''
        for name in ['gain', 'exposure']:
            self.isManual[name] = False

    def auto_cam_paused(self):
        '''
        Change gain and exposure back to isManual = True
        '''
        for name in ['gain', 'exposure']:
            self.isManual[name] = True



class CameraTunerWindowSet(object):
    '''
    This class possesses the three CameraTunerWindow: CAM_R, CAM_L, CAM_E

    This class should have the basic methods (interface) that the child CameraTunerWindow has,
        e.g. show(), hide(), close() ...
    '''
    def __init__(self, controller):

        # Instantiate three CameraTunerWindow objects
        # Collect them in a dictionary
        self.windows = {}
        self.windows[CAM_R] = CameraTunerWindow(controller, CAM_R, paired=True , parent=self)
        self.windows[CAM_L] = CameraTunerWindow(controller, CAM_L, paired=True , parent=self)
        self.windows[CAM_E] = CameraTunerWindow(controller, CAM_E, paired=False, parent=self)
        self.isSync = False

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

    def user_changed_value(self, which_cam, name, value):
        if which_cam == CAM_L and self.isSync:
            self.windows[CAM_R].set_parameter(name, value)
            self.windows[CAM_R].apply_parameter(name, value)

        elif which_cam == CAM_R and self.isSync:
            self.windows[CAM_L].set_parameter(name, value)
            self.windows[CAM_L].apply_parameter(name, value)

    def user_changed_sync(self, which_cam, isChecked):
        if which_cam == CAM_L:
            self.windows[CAM_R].set_sync(isChecked)
        if which_cam == CAM_R:
            self.windows[CAM_L].set_sync(isChecked)
        self.isSync = isChecked



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

    def user_changed_value(self):
        '''
        Transfers parameters to the core object via the controller.
        '''
        parms = {}
        for p in self.parameters.values():
            parms[p.name] = p.value

        self.controller.call_method( method_name = 'apply_depth_parameters',
                                             arg = parms                   )



