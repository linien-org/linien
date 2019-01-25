import os
import sys
import threading

#os.environ["KIVY_NO_CONSOLELOG"] = "1"

sys.path += ['../', '../../']

from gui import PIDApp
from connection import Connection, FakeConnection

def run_connection(gui):
    conn = Connection('rp-f0685a.local', 'root', 'zeilinger')
    #conn = FakeConnection('rp-f0685a.local', 'root', 'zeilinger')
    gui.connected(conn.parameters, conn.control)

def run_application():
    gui = PIDApp()

    t = threading.Thread(target=run_connection, args=(gui,))
    t.daemon = True
    t.start()

    gui.run()


if __name__ == '__main__':
    run_application()
