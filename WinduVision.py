"""
Version: 10.10

Changes:
    More detailed docstring in model.py

    Changed some methods in the WinduCore class to private methods
"""

__version__ = '10.10'

if __name__ == '__main__':
    from model import *
    app = QtGui.QApplication(sys.argv)
    core = WinduCore()
    sys.exit(app.exec_())
