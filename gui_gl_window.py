from PyQt4 import QtCore, QtGui, QtOpenGL



class GLWindow(QtGui.QMainWindow):
    def __init__(self, controller):
        super(GLWindow, self).__init__()
        self.controller = controller

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

        self.glect = None

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
        if not self.glect is None:
            GL.glCallList(self.glect)

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
        self.glect = self.makeObject(vertices)

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


