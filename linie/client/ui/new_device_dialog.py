# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'new_device_dialog.ui'
#
# Created by: PyQt5 UI code generator 5.12.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_NewDeviceDialog(object):
    def setupUi(self, NewDeviceDialog):
        NewDeviceDialog.setObjectName("NewDeviceDialog")
        NewDeviceDialog.resize(318, 292)
        self.horizontalLayout = QtWidgets.QHBoxLayout(NewDeviceDialog)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.newDeviceDialogCenter = NewDeviceDialogCenter(NewDeviceDialog)
        self.newDeviceDialogCenter.setObjectName("newDeviceDialogCenter")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.newDeviceDialogCenter)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox_4 = QtWidgets.QGroupBox(self.newDeviceDialogCenter)
        self.groupBox_4.setObjectName("groupBox_4")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.groupBox_4)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.deviceName = QtWidgets.QLineEdit(self.groupBox_4)
        self.deviceName.setObjectName("deviceName")
        self.verticalLayout_5.addWidget(self.deviceName)
        self.verticalLayout.addWidget(self.groupBox_4)
        self.groupBox = QtWidgets.QGroupBox(self.newDeviceDialogCenter)
        self.groupBox.setObjectName("groupBox")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.groupBox)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.host = QtWidgets.QLineEdit(self.groupBox)
        self.host.setObjectName("host")
        self.horizontalLayout_2.addWidget(self.host)
        self.verticalLayout.addWidget(self.groupBox)
        self.groupBox_2 = QtWidgets.QGroupBox(self.newDeviceDialogCenter)
        self.groupBox_2.setObjectName("groupBox_2")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.groupBox_2)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.username = QtWidgets.QLineEdit(self.groupBox_2)
        self.username.setObjectName("username")
        self.verticalLayout_3.addWidget(self.username)
        self.verticalLayout.addWidget(self.groupBox_2)
        self.groupBox_3 = QtWidgets.QGroupBox(self.newDeviceDialogCenter)
        self.groupBox_3.setObjectName("groupBox_3")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.groupBox_3)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.password = QtWidgets.QLineEdit(self.groupBox_3)
        self.password.setObjectName("password")
        self.verticalLayout_4.addWidget(self.password)
        self.verticalLayout.addWidget(self.groupBox_3)
        self.horizontalLayout_3.addLayout(self.verticalLayout)
        self.horizontalLayout.addWidget(self.newDeviceDialogCenter)
        self.buttonBox = QtWidgets.QDialogButtonBox(NewDeviceDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Vertical)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.horizontalLayout.addWidget(self.buttonBox)

        self.retranslateUi(NewDeviceDialog)
        self.buttonBox.accepted.connect(NewDeviceDialog.accept)
        self.buttonBox.rejected.connect(NewDeviceDialog.reject)
        self.buttonBox.accepted.connect(self.newDeviceDialogCenter.add_new_device)
        QtCore.QMetaObject.connectSlotsByName(NewDeviceDialog)

    def retranslateUi(self, NewDeviceDialog):
        _translate = QtCore.QCoreApplication.translate
        NewDeviceDialog.setWindowTitle(_translate("NewDeviceDialog", "Dialog"))
        self.groupBox_4.setTitle(_translate("NewDeviceDialog", "Name"))
        self.groupBox.setTitle(_translate("NewDeviceDialog", "Host"))
        self.host.setText(_translate("NewDeviceDialog", "rp-xxxxxx.local"))
        self.groupBox_2.setTitle(_translate("NewDeviceDialog", "Username"))
        self.username.setText(_translate("NewDeviceDialog", "root"))
        self.groupBox_3.setTitle(_translate("NewDeviceDialog", "Password"))
        self.password.setText(_translate("NewDeviceDialog", "root"))


from new_device_dialog_center import NewDeviceDialogCenter


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    NewDeviceDialog = QtWidgets.QDialog()
    ui = Ui_NewDeviceDialog()
    ui.setupUi(NewDeviceDialog)
    NewDeviceDialog.show()
    sys.exit(app.exec_())
