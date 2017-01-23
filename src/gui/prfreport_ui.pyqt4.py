# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/gui/pling-plong-prfreport.ui'
#
# Created: Fri Sep  2 00:02:39 2016
#      by: PyQt4 UI code generator 4.11.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_PlingPlongPRFDialog(object):
    def setupUi(self, PlingPlongPRFDialog):
        PlingPlongPRFDialog.setObjectName(_fromUtf8("PlingPlongPRFDialog"))
        PlingPlongPRFDialog.setWindowModality(QtCore.Qt.ApplicationModal)
        PlingPlongPRFDialog.resize(725, 591)
        PlingPlongPRFDialog.setSizeGripEnabled(True)
        self.gridLayout = QtGui.QGridLayout(PlingPlongPRFDialog)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.textBrowser = QtGui.QTextBrowser(PlingPlongPRFDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.textBrowser.sizePolicy().hasHeightForWidth())
        self.textBrowser.setSizePolicy(sizePolicy)
        self.textBrowser.setTabChangesFocus(True)
        self.textBrowser.setUndoRedoEnabled(True)
        self.textBrowser.setReadOnly(False)
        self.textBrowser.setObjectName(_fromUtf8("textBrowser"))
        self.horizontalLayout.addWidget(self.textBrowser)
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.buttonBox = QtGui.QDialogButtonBox(PlingPlongPRFDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Vertical)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Close|QtGui.QDialogButtonBox.Save)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout.addWidget(self.buttonBox)
        self.progressBar = QtGui.QProgressBar(PlingPlongPRFDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.progressBar.sizePolicy().hasHeightForWidth())
        self.progressBar.setSizePolicy(sizePolicy)
        self.progressBar.setProperty("value", 0)
        self.progressBar.setObjectName(_fromUtf8("progressBar"))
        self.verticalLayout.addWidget(self.progressBar)
        self.horizontalLayout.addLayout(self.verticalLayout)
        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.retranslateUi(PlingPlongPRFDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), PlingPlongPRFDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(PlingPlongPRFDialog)

    def retranslateUi(self, PlingPlongPRFDialog):
        PlingPlongPRFDialog.setWindowTitle(_translate("PlingPlongPRFDialog", "PRF Report", None))
        PlingPlongPRFDialog.setToolTip(_translate("PlingPlongPRFDialog", "Report all music to PRF", None))

