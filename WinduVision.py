'''
This is version 6.1.

Major modifications compared to 6.0:

    Auto offset is executed upon inititating the software,
    which includes both vertical and horizontal offsets.

    There is a concurrent thread 'align_thread' running with the video_thread.
    The align_thread executes ONLY the vertical alignment every ~1 second.
    The horizontal offset should NOT be changed frequently to avoid visual discomfort.

'''

if __name__ == '__main__':
    from WinduModel import *
    app = QtGui.QApplication(sys.argv)
    core = WinduCore()
    sys.exit(app.exec_())
