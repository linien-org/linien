import os
import sys
import threading

sys.path += ['../', '../../']

from linien.client.gui import QTApp


def run_application():
    gui = QTApp()

    sys.exit(gui.app.exec_())


if __name__ == '__main__':
    run_application()
