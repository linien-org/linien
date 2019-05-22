import os
import sys
import threading

#os.environ["KIVY_NO_CONSOLELOG"] = "1"

sys.path += ['../', '../../']

from spectrolock.client.gui import QTApp
from connection import Connection, FakeConnection

def run_connection(gui):
    #conn = Connection('rp-f0685a.local', 'root', 'zeilinger')
    #conn = Connection('rp-f06746.local', 'root', 'zeilinger')
    conn = FakeConnection('rp-f06503.local', 'root', 'zeilinger')
    gui.connected(conn.parameters, conn.control)

def run_application():
    gui = QTApp()

    t = threading.Thread(target=run_connection, args=(gui,))
    t.daemon = True
    t.start()

    sys.exit(gui.app.exec_())



if __name__ == '__main__':
    run_application()
