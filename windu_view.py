import numpy as np
import cv2, time, sys, threading, os, json
from PyQt4 import QtCore, QtGui
from windu_gui import *
from windu_controller import *
from windu_constants import *



class WinduGUI(QtGui.QMainWindow):
    def __init__(self, controller):
        super(WinduGUI, self).__init__()
        self.controller = controller

        self.__init__parameters()

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
        self.gl_window = GLWindow( controller = self.controller )
        self.depth_tuner_window = DepthTunerWindow( controller = self.controller )
        self.camera_tuner_window_R = CameraTunerWindow( controller=self.controller, which_cam=CAM_R )
        self.camera_tuner_window_L = CameraTunerWindow( controller=self.controller, which_cam=CAM_L )
        self.camera_tuner_window_E = CameraTunerWindow( controller=self.controller, which_cam=CAM_E )

        self.__init__toolbtns()
        self.__init__key_shortcut()

    def __init__parameters(self):
        '''
        Load gui parameters from the /parameters/gui.json file
        '''

        with open('parameters/gui.json', 'r') as fh:
            gui_parameters = json.loads(fh.read())

        for name, value in gui_parameters.items():
            setattr(self, name, value)

        self.isDeveloper = False

    def __init__toolbtns(self):
        # Each action has a unique key and a name
        # key = icon filename = method name
        # name = text of the action/button

        #    (    keys               ,   names                         , for_developer , connect_to_core )
        K = [('snapshot'             , 'Snapshot (Ctrl+S)'             ,    False      ,      False      ),
             ('toggle_recording'     , 'Record Video (Ctrl+R)'         ,    False      ,      True       ),
             ('toggle_auto_offset'   , 'Start Auto-alignment'          ,    True       ,      True       ),
             ('open_info'            , 'Show Real-time Info'           ,    True       ,      False      ),
             ('open_gl_window'       , 'Open 3D Viewer'                ,    True       ,      False      ),
             ('toggle_depth_map'     , 'Show Depth Map'                ,    True       ,      True       ),
             ('open_depth_tuner'     , 'Adjust Stereo Depth Parameters',    True       ,      False      ),
             ('start_select_cam'     , 'Select Cameras'                ,    False      ,      True       ),
             ('open_camera_tuner'    , 'Adjust Camera Parameters'      ,    False      ,      False      ),
             ('toggle_auto_cam'      , 'Camera Auto Mode'              ,    False      ,      True       ),
             ('toggle_fullscreen'    , 'Show Fullscreen (Ctrl+F)'      ,    False      ,      False      ),
             ('toggle_view_mode'     , 'Switch View Mode (Ctrl+V)'     ,    False      ,      True       )]

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
        # For key combinations that need to be connected to the self gui object
        #    ( method_name         , key combination )
        K = [('toggle_fullscreen'  , 'Ctrl+F'        ),
             ('snapshot'           , 'Ctrl+S'        ),
             ('toggle_developer'   , 'Shift+Ctrl+D'  ),
             ('esc_key'            , 'Esc'           )]

        for method_name, key_comb in K:
            method = getattr(self, method_name)
            QtGui.QShortcut(QtGui.QKeySequence(key_comb), self, method)



        # For key combinations that need to be connected to the core object
        #    ( method_name         , key combination )
        K = [('toggle_recording'   , 'Ctrl+R'        ),
             ('toggle_view_mode'   , 'Ctrl+V'        )]

        for method_name, key_comb in K:
            method = self.controller.get_method(method_name)
            if not method is None:
                QtGui.QShortcut(QtGui.QKeySequence(key_comb), self, method)

    # Methods called by actions of the self GUI object

    def snapshot(self):

        i = 1
        while os.path.exists('stereo_image_%03d.jpg' % i):
            i += 1

        fname = QtGui.QFileDialog.getSaveFileName(parent    = self,
                                                  directory = 'stereo_image_%03d.jpg' % i,
                                                  caption   = 'Save stereo image',
                                                  filter    = 'JPEG File Interchange Format (*.jpg)')
        if fname != '':
            fname = str(fname)
            if not fname.endswith('.jpg'):
                fname = fname + '.jpg'
            self.controller.call_method(method_name = 'snapshot',
                                        arg         = fname     )

    def open_info(self):
        if not self.info_window.isVisible():
            self.info_window.show()

    def open_gl_window(self):
        if not self.gl_window.isVisible():
            self.gl_window.show()

    def open_depth_tuner(self):
        self.depth_tuner_window.show()

    def open_camera_tuner(self):
        L = self.camera_tuner_window_L
        R = self.camera_tuner_window_R
        E = self.camera_tuner_window_E

        L.move(200, 200)
        R.move(400, 200)
        E.move(600, 200)

        for window in [L, R, E]:
            window.update_parameter()
            window.show()

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
                           self.camera_tuner_window_L,
                           self.camera_tuner_window_E]

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

        # Set icons for animation in a list
        icons = []
        for i in xrange(1, 3):
            fpath = 'icons/stop_recording_{}.png'.format(i)
            icons.append( QtGui.QIcon(fpath) )

        action = self.actions['toggle_recording']

        self.recording_animator = IconAnimator(QAction = action, # the QAction in which the icon is animated
                                                QIcons = icons)  # a list of QIcons to be animated
        self.recording_animator.start(500)

        self.actions['toggle_recording'].setText('Stop (Ctrl+R)')

    def recording_ends(self, temp_filename):
        self.recording_animator.stop()
        self.actions['toggle_recording'].setIcon(QtGui.QIcon('icons/toggle_recording.png'))
        self.actions['toggle_recording'].setText('Record Video')

        i = 1
        while os.path.exists('stereo_video_%03d.avi' % i):
            i += 1

        fname = QtGui.QFileDialog.getSaveFileName(parent    = self,
                                                  directory = 'stereo_video_%03d.avi' % i,
                                                  caption   = 'Save stereo video',
                                                  filter    = 'Audio Video Interleaved (*.avi)')
        if fname != '':
            fname = str(fname)
            if not fname.endswith('.avi'):
                fname = fname + '.avi'
            os.rename(temp_filename, fname)

        else:
            os.remove(temp_filename)

    def auto_offset_resumed(self):
        self.actions['toggle_auto_offset'].setIcon(QtGui.QIcon('icons/pause_auto_offset.png'))
        self.actions['toggle_auto_offset'].setText('Stop Auto-alignment')

    def auto_offset_paused(self):
        self.actions['toggle_auto_offset'].setIcon(QtGui.QIcon('icons/toggle_auto_offset.png'))
        self.actions['toggle_auto_offset'].setText('Start Auto-alignment')

    def auto_cam_resumed(self):

        # Set icons for animation in a list
        icons = []
        for i in xrange(1, 5):
            fpath = 'icons/auto_cam_resumed_{}.png'.format(i)
            icons.append( QtGui.QIcon(fpath) )

        action = self.actions['toggle_auto_cam']

        self.auto_cam_animator = IconAnimator(QAction = action, # the QAction in which the icon is animated
                                               QIcons = icons)  # a list of QIcons to be animated
        self.auto_cam_animator.start(500)

        self.actions['toggle_auto_cam'].setText('Stop Camera Auto Mode')

    def auto_cam_paused(self):
        self.auto_cam_animator.stop()
        self.actions['toggle_auto_cam'].setIcon(QtGui.QIcon('icons/toggle_auto_cam.png'))
        self.actions['toggle_auto_cam'].setText('Camera Auto Mode')

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

        which_cam = self.specify_which_cam()

        widget.close()

        if not which_cam is None:
            data = {'id': id, 'which_cam': which_cam}
            self.controller.call_method( method_name = 'save_cam_id', arg = data )

        self.controller.call_method( method_name = 'next_cam')

    def specify_which_cam(self):

        m = QtGui.QMessageBox()
        m.setWindowIcon(QtGui.QIcon('icons/windu_vision.png'))
        m.setWindowTitle('Windu Vision')
        m.setIcon(QtGui.QMessageBox.Question)
        m.setText('Is this the right or left camera?')
        m.addButton(QtGui.QPushButton('Left'), QtGui.QMessageBox.YesRole)
        m.addButton(QtGui.QPushButton('Right'), QtGui.QMessageBox.YesRole)
        m.addButton(QtGui.QPushButton('Ambient'), QtGui.QMessageBox.YesRole)
        m.addButton(QtGui.QPushButton('None'), QtGui.QMessageBox.YesRole)

        reply = m.exec_()

        if reply == 0: return CAM_L
        elif reply == 1: return CAM_R
        elif reply == 2: return CAM_E
        else: return None

    def select_cam_done(self):
        self.controller.call_method(method_name = 'start_video_thread')



if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)

    gui = WinduGUI( controller = MockController() )
    gui.show()

    sys.exit(app.exec_())


