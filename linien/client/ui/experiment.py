from PyQt5 import QtGui, QtWidgets, QtCore
from linien.client.widgets import CustomWidget
#from device_manager import Ui_DeviceManager
from experiment_ui import Ui_Form

class Experiment(QtWidgets.QWidget, CustomWidget, Ui_Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setupUi(args[0])

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setMinimumSize(QtCore.QSize(100, 100))
        self.resize(500, 500)

    """def setupUi(self, parent):
        print('!!!')
        #DeviceManager.setObjectName("DeviceManager")
        #DeviceManager.resize(510, 331)

        #self.centralwidget = QtWidgets.QLabel(DeviceManager)

        #self.centralwidget = Ui_DeviceManager()
        self.centralwidget = Ui_Form()

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setMinimumSize(QtCore.QSize(100, 100))

        self.centralwidget.setupUi(parent)"""

    """def connection_established(self):
        print('!!', self.centralwidget.button)
        #self.centralwidget = Ui_DeviceManager()
        #self.centralwidget.setupUi(parent)
        #self.centralwidget.setText('foo')

        #self.retranslateUi(DeviceManager)
        #self.connectButton.clicked.connect(self.centralwidget.connect)
        #self.addButton.clicked.connect(self.centralwidget.new_device)
        #self.removeButton.clicked.connect(self.centralwidget.remove_device)
        #self.deviceList.currentRowChanged['int'].connect(self.centralwidget.selected_device_changed)
        #QtCore.QMetaObject.connectSlotsByName(DeviceManager)"""


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    DeviceManager = QtWidgets.QMainWindow()
    ui = Experiment()
    ui.setupUi(DeviceManager)
    DeviceManager.show()
    sys.exit(app.exec_())
