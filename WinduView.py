import numpy as np
import cv2, time, sys, threading, os,json
from PyQt4 import QtCore, QtGui, QtOpenGL
from OpenGL import GL
from WinduController import *



class WinduGUI(QtGui.QMainWindow):
    def __init__(self, controller_obj):
        super(WinduGUI, self).__init__()
        self.controller = controller_obj

        self.__init__gui_parameters()

        self.setWindowTitle('Windu Vision')
        self.setWindowIcon(QtGui.QIcon('icons/windu_vision.png'))
        self.setGeometry(100, 100, self.default_width, self.default_height)
        self.setFixedSize(self.default_width, self.default_height)
        self.setMouseTracking(True)

        self.monitor = QtGui.QLabel(self)
        self.monitor.setGeometry(0, 0, self.default_width, self.default_height)
        self.monitor.setAlignment(QtCore.Qt.AlignCenter)

        self.toolbar = QtGui.QToolBar('Tool Bar')
        self.toolbar_dev = QtGui.QToolBar('Developer Tool Bar')

        for t in [self.toolbar, self.toolbar_dev]:
            t.setMovable(True)
            t.setStyleSheet("QToolBar { background:white; }")
            t.setIconSize(QtCore.QSize(30, 45))
            self.addToolBar(QtCore.Qt.LeftToolBarArea, t)

        if not self.isDeveloper:
            self.toolbar_dev.hide()

        self.info_window = TextWindow()
        self.progress_bar = ProgressBar()
        self.gl_window = GLWindow( controller_obj = self.controller )
        self.depth_tuner_window = DepthTunerWindow( controller_obj = self.controller )
        self.camera_tuner_window_R = CameraTunerWindow( controller_obj = self.controller, side='R' )
        self.camera_tuner_window_L = CameraTunerWindow( controller_obj = self.controller, side='L' )

        self.__init__toolbtns()
        self.__init__key_shortcut()

    def __init__gui_parameters(self):
        '''
        Load gui parameters from the /parameters/gui.json file
        '''

        fh = open('parameters/gui.json', 'r')
        gui_parameters = json.loads(fh.read())

        for name, value in gui_parameters.items():
            setattr(self, name, value)

    def __init__toolbtns(self):
        # Each action has a unique key and a name
        # key = icon filename = method name
        # name = text of the action/button

        #    (    keys               ,   names                         , for_developer , connect_to_core )
        K = [('snapshot'             , 'Snapshot'                      ,    False      ,      True       ),
             ('toggle_recording'     , 'Record Video'                  ,    False      ,      True       ),
             ('toggle_auto_offset'   , 'Start Auto-alignment'          ,    False      ,      True       ),
             ('open_info'            , 'Show Real-time Info'           ,    True       ,      False      ),
             ('open_gl_window'       , 'Open 3D Viewer'                ,    True       ,      False      ),
             ('toggle_depth_map'     , 'Show Depth Map'                ,    True       ,      True       ),
             ('open_depth_tuner'     , 'Adjust Stereo Depth Parameters',    True       ,      False      ),
             ('start_select_cam'     , 'Select Cameras'                ,    False      ,      True       ),
             ('open_camera_tuner'    , 'Adjust Camera Parameters'      ,    False      ,      False      ),
             ('equalize_cameras'     , 'Equalize Cameras'              ,    False      ,      True       ),
             ('toggle_fullscreen'    , 'Show Fullscreen'               ,    False      ,      False      )]

        self.actions = {}
        self.toolbtns = {}

        for (key, name, for_developer, connect_to_core) in K:

            # Create icon
            icon = QtGui.QIcon('icons/' + key + '.png')

            # Create action
            self.actions[key] = QtGui.QAction(icon, name, self)

            # Add action to toolbar depending it's for developer or not
            if for_developer:
                self.toolbtns[key] = self.toolbar_dev.addAction(self.actions[key])
            else:
                self.toolbtns[key] = self.toolbar.addAction(self.actions[key])



            if connect_to_core:
                # For actions that needs to be connected to the core object,
                # I defined a standard way of getting a argument-less method from the controller object.
                # Note that the method_name = key.
                method = self.controller.get_method( method_name = key )
                # The get_method() returns None if a particular method is not found in the core object.
                if not method is None:
                    # Connect the action to the method in the controller object
                    self.actions[key].triggered.connect(method)

            else:
                # For actions that needs to be connected to the self gui object
                try:
                    method = getattr(self, key)
                    self.actions[key].triggered.connect(method)
                except Exception as exception_inst:
                    print exception_inst

    def __init__key_shortcut(self):
        QtGui.QShortcut(QtGui.QKeySequence('Ctrl+F'), self, self.toggle_fullscreen)
        QtGui.QShortcut(QtGui.QKeySequence('Shift+Ctrl+D'), self, self.toggle_developer)
        QtGui.QShortcut(QtGui.QKeySequence('Esc'), self, self.esc_key)

        # For key combinations that need to be connected to the core object
        #    ( method_name         , key combination )
        K = [('snapshot'           , 'Ctrl+S'        ),
             ('toggle_recording'   , 'Ctrl+R'        ),
             ('toggle_auto_offset' , 'Ctrl+A'        )]

        for method_name, key_comb in K:
            method = self.controller.get_method(method_name)
            if not method is None:
                QtGui.QShortcut(QtGui.QKeySequence(key_comb), self, method)

    # Methods called by actions of the self GUI object

    def open_info(self):
        if not self.info_window.isVisible():
            self.info_window.show()

    def open_gl_window(self):
        if not self.gl_window.isVisible():
            self.gl_window.show()

    def open_depth_tuner(self):
        self.depth_tuner_window.show()

    def open_camera_tuner(self):
        L, R = self.camera_tuner_window_L, self.camera_tuner_window_R

        L.move(200, 200)
        R.move(300, 300)

        L.update_parameter()
        R.update_parameter()

        L.show()
        R.show()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.toolbar.show()

        else:
            self.showFullScreen()
            self.toolbar.hide()

        w, h = self.width(), self.height()
        self.monitor.setGeometry(0, 0, w, h)

        self.controller.call_method( method_name = 'set_display_size', arg = (w, h))

    def toggle_developer(self):
        if self.isDeveloper:
            self.toolbar_dev.hide()
            self.isDeveloper = False
        else:
            self.toolbar_dev.show()
            self.isDeveloper = True

    def esc_key(self):
        if self.isFullScreen():
            self.showNormal()
            self.toolbar.show()

            w, h = self.width(), self.height()
            self.monitor.setGeometry(0, 0, w, h)

            self.controller.call_method( method_name = 'set_display_size', arg = (w, h))

    # Overriden methods

    def wheelEvent(self, event):
        if event.delta() > 0:
            self.controller.call_method('zoom_in')
        else:
            self.controller.call_method('zoom_out')

    def closeEvent(self, event):
        reply = QtGui.QMessageBox.question(self,
                                           'Windu Vision',
                                           'Are you sure you want to quit Windu Vision?',
                                           QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)

        if reply == QtGui.QMessageBox.Yes:
            self.controller.call_method('close')

            window_list = [self.info_window          ,
                           self.progress_bar         ,
                           self.gl_window            ,
                           self.depth_tuner_window   ,
                           self.camera_tuner_window_R,
                           self.camera_tuner_window_L]

            for win in window_list:
                win.close()

            event.accept()

        else:
            event.ignore()

    def keyPressEvent (self, eventQKeyEvent):
        key = eventQKeyEvent.key()
        if key == QtCore.Qt.Key_Up:
            self.controller.call_method('zoom_in')
        elif key == QtCore.Qt.Key_Down:
            self.controller.call_method('zoom_out')

    # Methods for incoming signals

    def connect_signals(self, thread, signal_name):
        '''
        Called by an external object to connect signals.
        '''

        # The suffix '(PyQt_PyObject)' means the argument to be transferred
        # could be any type of python objects,
        # not limited to Qt objects.
        signal = signal_name + '(PyQt_PyObject)'

        # The method name to be called = the signal name
        try:
            method = getattr(self, signal_name)
            self.connect(thread, QtCore.SIGNAL(signal), method)

        except Exception as exception_inst:
            print "Try to connect PyQt signal '{}'".format(signal_name)
            print str(exception_inst) + '\n'

    def disconnect_signals(self, thread, signal_name):
        '''
        Called by an external object to disconnect signals.
        This does exactly the opposite of self.connect_signals()
        '''

        signal = signal_name + '(PyQt_PyObject)'

        try:
            method = getattr(self, signal_name)
            self.disconnect(thread, QtCore.SIGNAL(signal), method)

        except Exception as exception_inst:
            print "Try to disconnect PyQt signal '{}'".format(signal_name)
            print exception_inst + '\n'

    def progress_update(self, text_value):
        self.progress_bar.progress_update(text_value)

    def display_image(self, image):
        # convert from BGR to RGB for latter QImage
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        height, width, bytesPerComponent = image.shape
        bytesPerLine = bytesPerComponent * width

        # convert cv2 image to QImage
        Q_img = QtGui.QImage(image,
                             width, height, bytesPerLine,
                             QtGui.QImage.Format_RGB888)

        # Convert QImage to QPixmap
        Q_pixmap = QtGui.QPixmap.fromImage(Q_img)

        # Set the QLabel to display the QPixmap
        self.monitor.setPixmap(Q_pixmap)

    def recording_starts(self):
        self.actions['toggle_recording'].setIcon(QtGui.QIcon('icons/stop_recording.png'))
        self.actions['toggle_recording'].setText('Stop')

    def recording_ends(self):
        self.actions['toggle_recording'].setIcon(QtGui.QIcon('icons/toggle_recording.png'))
        self.actions['toggle_recording'].setText('Record Video')

    def auto_offset_resumed(self):
        self.actions['toggle_auto_offset'].setIcon(QtGui.QIcon('icons/pause_auto_offset.png'))
        self.actions['toggle_auto_offset'].setText('Stop Auto-alignment')

    def auto_offset_paused(self):
        self.actions['toggle_auto_offset'].setIcon(QtGui.QIcon('icons/toggle_auto_offset.png'))
        self.actions['toggle_auto_offset'].setText('Start Auto-alignment')

    def set_info_text(self, text):
        self.info_window.setText(text)

    def display_topography(self, vertices):
        self.gl_window.gl_widget.updateObject(vertices)

    def show_current_cam(self, data):

        id = data['id']
        image = data['img']

        rows, cols, _ = image.shape

        widget = QtGui.QWidget()
        widget.setWindowTitle('Windu Vision')
        widget.setWindowIcon(QtGui.QIcon('icons/windu_vision.png'))
        widget.setFixedSize(cols, rows)

        canvas = QtGui.QLabel(widget)
        canvas.setGeometry(0, 0, cols, rows)

        widget.show()

        # convert from BGR to RGB for latter QImage
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        height, width, bytesPerComponent = image.shape
        bytesPerLine = bytesPerComponent * width

        # convert cv2 image to QImage
        Q_img = QtGui.QImage(image,
                             width, height, bytesPerLine,
                             QtGui.QImage.Format_RGB888)

        # Convert QImage to QPixmap
        Q_pixmap = QtGui.QPixmap.fromImage(Q_img)

        # Set the QLabel to display the QPixmap
        canvas.setPixmap(Q_pixmap)

        which_side = self.specify_right_left_cam()

        data = {'id': id, 'which_side': which_side}

        widget.close()

        self.controller.call_method( method_name = 'save_cam_id', arg = data )
        self.controller.call_method( method_name = 'next_cam')

    def specify_right_left_cam(self):

        m = QtGui.QMessageBox()
        m.setWindowIcon(QtGui.QIcon('icons/windu_vision.png'))
        m.setWindowTitle('Windu Vision')
        m.setIcon(QtGui.QMessageBox.Question)
        m.setText('Is this the right or left camera?')
        m.addButton(QtGui.QPushButton('Left'), QtGui.QMessageBox.YesRole)
        m.addButton(QtGui.QPushButton('Right'), QtGui.QMessageBox.NoRole)
        m.addButton(QtGui.QPushButton('None'), QtGui.QMessageBox.RejectRole)

        reply = m.exec_()

        if reply == 0:
            return 'L'
        elif reply == 1:
            return 'R'
        else:
            return None

    def select_cam_done(self):
        self.controller.call_method(method_name = 'start_video_thread')

    def camera_equalized(self, successful):

        if successful:
            text = 'Camera equalized'
        else:
            text = 'Camera not equalized'

        m = QtGui.QMessageBox()
        m.setWindowIcon(QtGui.QIcon('icons/windu_vision.png'))
        m.setWindowTitle('Windu Vision')
        m.setIcon(QtGui.QMessageBox.Information)
        m.setText(text)
        m.addButton(QtGui.QPushButton('OK'), QtGui.QMessageBox.YesRole)

        m.exec_()



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
    def __init__(self, controller_obj):
        super(DepthTunerWindow, self).__init__()

        self.controller = controller_obj

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
    def __init__(self, controller_obj, side):
        super(CameraTunerWindow, self).__init__()

        self.controller = controller_obj
        self.side = side

        self.setWindowIcon(QtGui.QIcon('icons/windu_vision.png'))
        self.setMinimumWidth(600)

        if self.side == 'R':
            self.setWindowTitle('Right Camera Parameters')
        else:
            self.setWindowTitle('Left Camera Parameters')

        with open('parameters/cam.json', 'r') as fh:
            parms = json.loads(fh.read())

        val = parms[self.side]

        self.add_parameter(name='brightness'    , min=0   , max=255 , value=val['brightness']   , interval=5  )
        self.add_parameter(name='contrast'      , min=0   , max=255 , value=val['contrast']     , interval=5  )
        self.add_parameter(name='saturation'    , min=0   , max=255 , value=val['saturation']   , interval=5  )
        self.add_parameter(name='gain'          , min=0   , max=255 , value=val['gain']         , interval=5  )
        self.add_parameter(name='exposure'      , min=-7  , max=-1  , value=val['exposure']     , interval=1  )
        self.add_parameter(name='white_balance' , min=3000, max=6500, value=val['white_balance'], interval=100)
        self.add_parameter(name='focus'         , min=0   , max=255 , value=val['focus']        , interval=5  )

    def apply_parameter(self):
        '''
        Transfers parameters to the core object via the controller.
        '''
        parms = {}
        for p in self.parameters:
            parms[p.name] = p.value

        data = {'side': self.side, 'parameters': parms}

        self.controller.call_method( method_name = 'apply_camera_parameters',
                                             arg = data                     )

    def update_parameter(self):

        with open('parameters/cam.json', 'r') as fh:
            parameters = json.loads(fh.read())

        parms = parameters[self.side]

        for name, value in parms.items():
            self.set_parameter(name, value)



class GLWindow(QtGui.QMainWindow):
    def __init__(self, controller_obj):
        super(GLWindow, self).__init__()
        self.controller = controller_obj

        self.setWindowTitle('3D Topography')
        self.setWindowIcon(QtGui.QIcon('icons/windu_vision.png'))
        self.setGeometry(150, 150, 960, 640)

        self.gl_widget = GLWidget( parent_window = self )
        self.gl_widget.setGeometry(0, 0, 960, 640)

        self.toolbar = QtGui.QToolBar('Tool Bar')
        self.toolbar.setMovable(True)
        self.toolbar.setStyleSheet("QToolBar { background:white; }")
        self.toolbar.setIconSize(QtCore.QSize(30, 45))
        self.addToolBar(QtCore.Qt.LeftToolBarArea, self.toolbar)

        self.__init__toolbtns()

    def __init__toolbtns(self):
        # Each action has a unique key and a name
        # key = icon filename = method name
        # name = text of the action/button

        #    (    keys               ,        names               )
        K = [('stereo_reconstruction', 'Reconstruct 3D Topography'),
             ('reset_view'           , 'Reset View'               )]

        self.actions = {}
        self.toolbtns = {}

        # Create actions and tool buttons
        for key, name in K:
            icon = QtGui.QIcon('icons/' + key + '.png')
            self.actions[key] = QtGui.QAction(icon, name, self)
            self.toolbtns[key] = self.toolbar.addAction(self.actions[key])

        # For actions that needs to be connected to the core object,
        K = ['stereo_reconstruction']

        # In this loop I defined a standard way of
        # connecting each action to a method in the core object via the controller object.
        for key in K:
            # Get a argument-less method from the controller object.
            # Note that the method_name = key.
            method = self.controller.get_method( method_name = key )
            # The get_method() returns None
            # if a particular method is not found in the core object.
            if not method is None:
                # Connect the action to the method in the controller object
                self.actions[key].triggered.connect(method)

        # For actions that needs to be connected to the self gui object,
        keys = ['reset_view']
        for key in keys:
            try:
                method = getattr(self, key)
                self.actions[key].triggered.connect(method)
            except Exception as exception_inst:
                print exception_inst

    def reset_view(self):
        self.gl_widget.reset_view()



class GLWidget(QtOpenGL.QGLWidget):
    def __init__(self, parent_window):
        super(GLWidget, self).__init__(parent_window)

        # Dynamic display parameters
        self.xRot = 0
        self.yRot = 0
        self.zRot = 0
        self.xMove = 0.0
        self.yMove = 0.0
        self.zoom = 10.0
        self.lastPos = QtCore.QPoint()

    # initializeGL(), resizeGL(), paintGL() are the three
    # built-in methods of QtOpenGL.QGLWidget class

    def initializeGL(self):
        GL.glClearColor(1.0, 1.0, 1.0, 1.0)
        GL.glShadeModel(GL.GL_SMOOTH)
        GL.glEnable(GL.GL_DEPTH_TEST)

        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, (0.0, 0.0, 0.0, 1.0))
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, (0.2, 0.2, 0.2, 1.0))
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, (1.0, 1.0, 1.0, 1.0))
        # GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, (0.0, 0.0, 0.0, 1.0))
        GL.glEnable(GL.GL_LIGHTING)
        GL.glEnable(GL.GL_LIGHT0)

        GL.glColorMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT_AND_DIFFUSE)
        GL.glEnable(GL.GL_COLOR_MATERIAL)

        self.gl_object = None

    def resizeGL(self, width, height):
        GL.glViewport(0, 0, 960, 640)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glOrtho(-self.zoom*960/640, +self.zoom*960/640, +self.zoom, -self.zoom, 1.0, 200.0)
        GL.glMatrixMode(GL.GL_MODELVIEW)

    def paintGL(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glLoadIdentity()
        GL.glTranslated(self.xMove, self.yMove, -100.0)
        GL.glRotated(self.xRot / 16.0, 1.0, 0.0, 0.0)
        GL.glRotated(self.yRot / 16.0, 0.0, 1.0, 0.0)
        GL.glRotated(self.zRot / 16.0, 0.0, 0.0, 1.0)
        if not self.gl_object is None:
            GL.glCallList(self.gl_object)

    # Mouse events

    def mousePressEvent(self, event):
        self.lastPos = QtCore.QPoint(event.pos())

    def mouseMoveEvent(self, event):
        dx = event.x() - self.lastPos.x()
        dy = event.y() - self.lastPos.y()
        if event.buttons() & QtCore.Qt.LeftButton:
            self.setXRotation(self.xRot - 4 * dy)
            self.setZRotation(self.zRot - 4 * dx)
        elif event.buttons() & QtCore.Qt.RightButton:
            self.xMove = self.xMove + dx*self.zoom/200.0
            self.yMove = self.yMove + dy*self.zoom/200.0
            self.updateGL()
        self.lastPos = QtCore.QPoint(event.pos())

    def wheelEvent(self, event):
        if self.zoom - event.delta()/600.0 > 0:
            self.zoom = self.zoom - event.delta()/600.0
            GL.glMatrixMode(GL.GL_PROJECTION)
            GL.glLoadIdentity()
            GL.glOrtho(-self.zoom*960/640, +self.zoom*960/640, +self.zoom, -self.zoom, 1.0, 200.0)
            GL.glMatrixMode(GL.GL_MODELVIEW)
            self.updateGL()

    def makeObject(self, vertex_list):
        genList = GL.glGenLists(1)
        GL.glNewList(genList, GL.GL_COMPILE)

        GL.glBegin(GL.GL_TRIANGLES)

        for i in xrange(vertex_list.shape[0]):
            V = vertex_list[i, :]
            if i % 3 == 0:
                GL.glNormal3f(V[6], V[7], V[8])
            GL.glVertex3f(V[0], V[1], V[2])
            GL.glColor3f(V[3], V[4], V[5])

        GL.glEnd()

        GL.glEndList()
        return genList

    def updateObject(self, vertices):
        self.gl_object = self.makeObject(vertices)

    def setXRotation(self, angle):
        angle = self.normalizeAngle(angle)
        if angle != self.xRot:
            self.xRot = angle
            self.updateGL()

    def setZRotation(self, angle):
        angle = self.normalizeAngle(angle)
        if angle != self.zRot:
            self.zRot = angle
            self.updateGL()

    def normalizeAngle(self, angle):
        while angle < 0:
            angle += 360 * 16
        while angle > 360 * 16:
            angle -= 360 * 16
        return angle

    def reset_view(self):
        self.xRot = 0
        self.yRot = 0
        self.zRot = 0
        self.xMove = 0.0
        self.yMove = 0.0
        self.zoom = 10.0

        # Call methods in self.resizeGL()
        GL.glViewport(0, 0, 960, 640)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glOrtho(-self.zoom*960/640, +self.zoom*960/640, +self.zoom, -self.zoom, 1.0, 200.0)
        GL.glMatrixMode(GL.GL_MODELVIEW)

        # Call self.paintGL()
        self.updateGL()



if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)

    gui = WinduGUI( controller_obj = MockController() )
    gui.show()

    sys.exit(app.exec_())