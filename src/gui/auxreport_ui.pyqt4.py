# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/gui/pling-plong-auxreport.ui'
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

class Ui_PlingPlongAUXDialog(object):
    def setupUi(self, PlingPlongAUXDialog):
        PlingPlongAUXDialog.setObjectName(_fromUtf8("PlingPlongAUXDialog"))
        PlingPlongAUXDialog.setWindowModality(QtCore.Qt.ApplicationModal)
        PlingPlongAUXDialog.resize(737, 556)
        PlingPlongAUXDialog.setSizeGripEnabled(True)
        self.gridLayout = QtGui.QGridLayout(PlingPlongAUXDialog)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.webView = QtWebKit.QWebView(PlingPlongAUXDialog)
        self.webView.setUrl(QtCore.QUrl(_fromUtf8("about:blank")))
        self.webView.setObjectName(_fromUtf8("webView"))
        self.gridLayout.addWidget(self.webView, 0, 0, 3, 1)
        self.buttonBox = QtGui.QDialogButtonBox(PlingPlongAUXDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Vertical)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 0, 1, 1, 1)
        self.progressBar = QtGui.QProgressBar(PlingPlongAUXDialog)
        self.progressBar.setProperty("value", 0)
        self.progressBar.setObjectName(_fromUtf8("progressBar"))
        self.gridLayout.addWidget(self.progressBar, 1, 1, 1, 1)

        self.retranslateUi(PlingPlongAUXDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), PlingPlongAUXDialog.reject)
        QtCore.QObject.connect(self.webView, QtCore.SIGNAL(_fromUtf8("loadProgress(int)")), self.progressBar.setValue)
        QtCore.QMetaObject.connectSlotsByName(PlingPlongAUXDialog)

    def retranslateUi(self, PlingPlongAUXDialog):
        PlingPlongAUXDialog.setWindowTitle(_translate("PlingPlongAUXDialog", "Sonoton (AUX) Report", None))
        PlingPlongAUXDialog.setToolTip(_translate("PlingPlongAUXDialog", "This is an embedded view of the online report form for AUX publishing", None))

from PyQt4 import QtWebKit
