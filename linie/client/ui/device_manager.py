# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'device_manager.ui'
#
# Created by: PyQt5 UI code generator 5.12.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_DeviceManager(object):
    def setupUi(self, DeviceManager):
        DeviceManager.setObjectName("DeviceManager")
        DeviceManager.resize(510, 331)
        self.centralwidget = DeviceManagerCenter(DeviceManager)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setMinimumSize(QtCore.QSize(510, 280))
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.deviceList = QtWidgets.QListWidget(self.centralwidget)
        self.deviceList.setObjectName("deviceList")
        self.horizontalLayout_2.addWidget(self.deviceList)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.connectButton = QtWidgets.QPushButton(self.centralwidget)
        self.connectButton.setEnabled(False)
        self.connectButton.setObjectName("connectButton")
        self.verticalLayout.addWidget(self.connectButton)
        self.addButton = QtWidgets.QPushButton(self.centralwidget)
        self.addButton.setObjectName("addButton")
        self.verticalLayout.addWidget(self.addButton)
        self.removeButton = QtWidgets.QPushButton(self.centralwidget)
        self.removeButton.setEnabled(False)
        self.removeButton.setObjectName("removeButton")
        self.verticalLayout.addWidget(self.removeButton)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.horizontalLayout_2.addLayout(self.verticalLayout)
        self.horizontalLayout.addLayout(self.horizontalLayout_2)
        self.menubar = QtWidgets.QMenuBar(DeviceManager)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 510, 27))
        self.menubar.setObjectName("menubar")
        DeviceManager.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(DeviceManager)
        self.statusbar.setObjectName("statusbar")
        DeviceManager.setStatusBar(self.statusbar)

        self.retranslateUi(DeviceManager)
        self.connectButton.clicked.connect(self.centralwidget.connect)
        self.addButton.clicked.connect(self.centralwidget.new_device)
        self.removeButton.clicked.connect(self.centralwidget.remove_device)
        self.deviceList.currentRowChanged['int'].connect(self.centralwidget.selected_device_changed)
        QtCore.QMetaObject.connectSlotsByName(DeviceManager)

    def retranslateUi(self, DeviceManager):
        _translate = QtCore.QCoreApplication.translate
        DeviceManager.setWindowTitle(_translate("DeviceManager", "MainWindow"))
        self.connectButton.setText(_translate("DeviceManager", "Connect"))
        self.addButton.setText(_translate("DeviceManager", "New device"))
        self.removeButton.setText(_translate("DeviceManager", "Remove device"))


from device_manager_center import DeviceManagerCenter


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    DeviceManager = QtWidgets.QMainWindow()
    ui = Ui_DeviceManager()
    ui.setupUi(DeviceManager)
    DeviceManager.show()
    sys.exit(app.exec_())
