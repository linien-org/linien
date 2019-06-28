import os
import sys
import signal
import threading

from plumbum import colors

# it may seem odd to include '.', but for some reason this is needed for
# standalone windows executable
sys.path += ['../', os.path.join('..', '..'), '.']

import linien
from linien.client.gui import QTApp


def run_application():
    print('Linien spectroscopy lock version ' + (colors.bold | linien.__version__))
    gui = QTApp()

    # catch ctrl-c and shutdown
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    sys.exit(gui.app.exec_())


if __name__ == '__main__':
    run_application()
