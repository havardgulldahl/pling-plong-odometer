# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'pling-plong-odometer.ui'
#
# Created: Sun Oct  9 20:58:26 2016
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

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(872, 679)
        MainWindow.setAcceptDrops(True)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/gfx/note")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        MainWindow.setWindowIcon(icon)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.gridLayout = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.verticalLayout_2 = QtGui.QVBoxLayout()
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.groupBox = QtGui.QGroupBox(self.centralwidget)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.formLayout_2 = QtGui.QFormLayout(self.groupBox)
        self.formLayout_2.setFieldGrowthPolicy(QtGui.QFormLayout.FieldsStayAtSizeHint)
        self.formLayout_2.setObjectName(_fromUtf8("formLayout_2"))
        self.label_8 = QtGui.QLabel(self.groupBox)
        self.label_8.setObjectName(_fromUtf8("label_8"))
        self.formLayout_2.setWidget(0, QtGui.QFormLayout.LabelRole, self.label_8)
        self.prodno = QtGui.QLineEdit(self.groupBox)
        self.prodno.setObjectName(_fromUtf8("prodno"))
        self.formLayout_2.setWidget(0, QtGui.QFormLayout.FieldRole, self.prodno)
        self.prodtitle = QtGui.QLineEdit(self.groupBox)
        self.prodtitle.setObjectName(_fromUtf8("prodtitle"))
        self.formLayout_2.setWidget(2, QtGui.QFormLayout.FieldRole, self.prodtitle)
        self.label_11 = QtGui.QLabel(self.groupBox)
        self.label_11.setObjectName(_fromUtf8("label_11"))
        self.formLayout_2.setWidget(2, QtGui.QFormLayout.LabelRole, self.label_11)
        self.verticalLayout_2.addWidget(self.groupBox)
        self.clips = QtGui.QTreeWidget(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.clips.sizePolicy().hasHeightForWidth())
        self.clips.setSizePolicy(sizePolicy)
        self.clips.setAcceptDrops(True)
        self.clips.setStatusTip(_fromUtf8(""))
        self.clips.setTabKeyNavigation(True)
        self.clips.setDragDropMode(QtGui.QAbstractItemView.DropOnly)
        self.clips.setDefaultDropAction(QtCore.Qt.CopyAction)
        self.clips.setAlternatingRowColors(True)
        self.clips.setUniformRowHeights(True)
        self.clips.setAllColumnsShowFocus(False)
        self.clips.setExpandsOnDoubleClick(False)
        self.clips.setObjectName(_fromUtf8("clips"))
        self.verticalLayout_2.addWidget(self.clips)
        self.errors = QtGui.QGroupBox(self.centralwidget)
        self.errors.setObjectName(_fromUtf8("errors"))
        self.gridLayout_2 = QtGui.QGridLayout(self.errors)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.errorText = QtGui.QLabel(self.errors)
        self.errorText.setText(_fromUtf8(""))
        self.errorText.setObjectName(_fromUtf8("errorText"))
        self.gridLayout_2.addWidget(self.errorText, 0, 0, 1, 1)
        self.verticalLayout_2.addWidget(self.errors)
        self.detailsBox = QtGui.QGroupBox(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.detailsBox.sizePolicy().hasHeightForWidth())
        self.detailsBox.setSizePolicy(sizePolicy)
        self.detailsBox.setObjectName(_fromUtf8("detailsBox"))
        self.gridLayout_3 = QtGui.QGridLayout(self.detailsBox)
        self.gridLayout_3.setObjectName(_fromUtf8("gridLayout_3"))
        self.buttonBox = QtGui.QDialogButtonBox(self.detailsBox)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Close)
        self.buttonBox.setCenterButtons(True)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout_3.addWidget(self.buttonBox, 9, 1, 1, 1)
        self.clipYear = QtGui.QLabel(self.detailsBox)
        self.clipYear.setText(_fromUtf8(""))
        self.clipYear.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.clipYear.setObjectName(_fromUtf8("clipYear"))
        self.gridLayout_3.addWidget(self.clipYear, 8, 1, 1, 1)
        self.label_2 = QtGui.QLabel(self.detailsBox)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout_3.addWidget(self.label_2, 8, 0, 1, 1)
        self.clipLabel = QtGui.QLabel(self.detailsBox)
        self.clipLabel.setText(_fromUtf8(""))
        self.clipLabel.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.clipLabel.setObjectName(_fromUtf8("clipLabel"))
        self.gridLayout_3.addWidget(self.clipLabel, 7, 1, 1, 1)
        self.label_3 = QtGui.QLabel(self.detailsBox)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.gridLayout_3.addWidget(self.label_3, 7, 0, 1, 1)
        self.clipAlbum = QtGui.QLabel(self.detailsBox)
        self.clipAlbum.setText(_fromUtf8(""))
        self.clipAlbum.setObjectName(_fromUtf8("clipAlbum"))
        self.gridLayout_3.addWidget(self.clipAlbum, 6, 1, 1, 1)
        self.label_10 = QtGui.QLabel(self.detailsBox)
        self.label_10.setTextFormat(QtCore.Qt.RichText)
        self.label_10.setObjectName(_fromUtf8("label_10"))
        self.gridLayout_3.addWidget(self.label_10, 6, 0, 1, 1)
        self.clipRecordnumber = QtGui.QLabel(self.detailsBox)
        self.clipRecordnumber.setText(_fromUtf8(""))
        self.clipRecordnumber.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.clipRecordnumber.setObjectName(_fromUtf8("clipRecordnumber"))
        self.gridLayout_3.addWidget(self.clipRecordnumber, 5, 1, 1, 1)
        self.label_5 = QtGui.QLabel(self.detailsBox)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.gridLayout_3.addWidget(self.label_5, 5, 0, 1, 1)
        self.clipCopyright = QtGui.QLabel(self.detailsBox)
        self.clipCopyright.setText(_fromUtf8(""))
        self.clipCopyright.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.clipCopyright.setObjectName(_fromUtf8("clipCopyright"))
        self.gridLayout_3.addWidget(self.clipCopyright, 4, 1, 1, 1)
        self.label_4 = QtGui.QLabel(self.detailsBox)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.gridLayout_3.addWidget(self.label_4, 4, 0, 1, 1)
        self.clipComposer = QtGui.QLabel(self.detailsBox)
        self.clipComposer.setText(_fromUtf8(""))
        self.clipComposer.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.clipComposer.setObjectName(_fromUtf8("clipComposer"))
        self.gridLayout_3.addWidget(self.clipComposer, 3, 1, 1, 1)
        self.label_6 = QtGui.QLabel(self.detailsBox)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.gridLayout_3.addWidget(self.label_6, 3, 0, 1, 1)
        self.clipLyricist = QtGui.QLabel(self.detailsBox)
        self.clipLyricist.setText(_fromUtf8(""))
        self.clipLyricist.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.clipLyricist.setObjectName(_fromUtf8("clipLyricist"))
        self.gridLayout_3.addWidget(self.clipLyricist, 2, 1, 1, 1)
        self.label_9 = QtGui.QLabel(self.detailsBox)
        self.label_9.setObjectName(_fromUtf8("label_9"))
        self.gridLayout_3.addWidget(self.label_9, 2, 0, 1, 1)
        self.clipArtist = QtGui.QLabel(self.detailsBox)
        self.clipArtist.setText(_fromUtf8(""))
        self.clipArtist.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.clipArtist.setObjectName(_fromUtf8("clipArtist"))
        self.gridLayout_3.addWidget(self.clipArtist, 1, 1, 1, 1)
        self.label_7 = QtGui.QLabel(self.detailsBox)
        self.label_7.setObjectName(_fromUtf8("label_7"))
        self.gridLayout_3.addWidget(self.label_7, 1, 0, 1, 1)
        self.clipTitle = QtGui.QLabel(self.detailsBox)
        self.clipTitle.setText(_fromUtf8(""))
        self.clipTitle.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.clipTitle.setObjectName(_fromUtf8("clipTitle"))
        self.gridLayout_3.addWidget(self.clipTitle, 0, 1, 1, 1)
        self.label = QtGui.QLabel(self.detailsBox)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout_3.addWidget(self.label, 0, 0, 1, 1)
        self.verticalLayout_2.addWidget(self.detailsBox)
        self.gridLayout.addLayout(self.verticalLayout_2, 0, 0, 1, 1)
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.loadFileButton = QtGui.QPushButton(self.centralwidget)
        self.loadFileButton.setObjectName(_fromUtf8("loadFileButton"))
        self.verticalLayout.addWidget(self.loadFileButton)
        self.fileInfo = QtGui.QLabel(self.centralwidget)
        self.fileInfo.setText(_fromUtf8(""))
        self.fileInfo.setTextFormat(QtCore.Qt.RichText)
        self.fileInfo.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.fileInfo.setWordWrap(True)
        self.fileInfo.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.fileInfo.setObjectName(_fromUtf8("fileInfo"))
        self.verticalLayout.addWidget(self.fileInfo)
        self.volumeThreshold = QtGui.QDoubleSpinBox(self.centralwidget)
        self.volumeThreshold.setSuffix(_fromUtf8(""))
        self.volumeThreshold.setDecimals(4)
        self.volumeThreshold.setMaximum(4.0)
        self.volumeThreshold.setSingleStep(0.01)
        self.volumeThreshold.setProperty("value", 0.05)
        self.volumeThreshold.setObjectName(_fromUtf8("volumeThreshold"))
        self.verticalLayout.addWidget(self.volumeThreshold)
        self.volumeInfo = QtGui.QLabel(self.centralwidget)
        self.volumeInfo.setText(_fromUtf8(""))
        self.volumeInfo.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.volumeInfo.setObjectName(_fromUtf8("volumeInfo"))
        self.verticalLayout.addWidget(self.volumeInfo)
        self.metadata = QtGui.QLabel(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.metadata.sizePolicy().hasHeightForWidth())
        self.metadata.setSizePolicy(sizePolicy)
        self.metadata.setMinimumSize(QtCore.QSize(100, 0))
        self.metadata.setMaximumSize(QtCore.QSize(150, 16777215))
        self.metadata.setText(_fromUtf8(""))
        self.metadata.setTextFormat(QtCore.Qt.RichText)
        self.metadata.setWordWrap(True)
        self.metadata.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.metadata.setObjectName(_fromUtf8("metadata"))
        self.verticalLayout.addWidget(self.metadata)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.groupBox_2 = QtGui.QGroupBox(self.centralwidget)
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.verticalLayout_3 = QtGui.QVBoxLayout(self.groupBox_2)
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.DMAButton = QtGui.QPushButton(self.groupBox_2)
        self.DMAButton.setEnabled(False)
        self.DMAButton.setObjectName(_fromUtf8("DMAButton"))
        self.verticalLayout_3.addWidget(self.DMAButton)
        self.AUXButton = QtGui.QPushButton(self.groupBox_2)
        self.AUXButton.setEnabled(False)
        self.AUXButton.setObjectName(_fromUtf8("AUXButton"))
        self.verticalLayout_3.addWidget(self.AUXButton)
        self.ApolloButton = QtGui.QPushButton(self.groupBox_2)
        self.ApolloButton.setEnabled(False)
        self.ApolloButton.setObjectName(_fromUtf8("ApolloButton"))
        self.verticalLayout_3.addWidget(self.ApolloButton)
        self.extremeButton = QtGui.QPushButton(self.groupBox_2)
        self.extremeButton.setEnabled(False)
        self.extremeButton.setToolTip(_fromUtf8(""))
        self.extremeButton.setObjectName(_fromUtf8("extremeButton"))
        self.verticalLayout_3.addWidget(self.extremeButton)
        self.UprightButton = QtGui.QPushButton(self.groupBox_2)
        self.UprightButton.setEnabled(False)
        self.UprightButton.setObjectName(_fromUtf8("UprightButton"))
        self.verticalLayout_3.addWidget(self.UprightButton)
        self.UniversalButton = QtGui.QPushButton(self.groupBox_2)
        self.UniversalButton.setEnabled(False)
        self.UniversalButton.setObjectName(_fromUtf8("UniversalButton"))
        self.verticalLayout_3.addWidget(self.UniversalButton)
        self.verticalLayout.addWidget(self.groupBox_2)
        self.creditsButton = QtGui.QPushButton(self.centralwidget)
        self.creditsButton.setEnabled(False)
        self.creditsButton.setObjectName(_fromUtf8("creditsButton"))
        self.verticalLayout.addWidget(self.creditsButton)
        spacerItem1 = QtGui.QSpacerItem(150, 20, QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Minimum)
        self.verticalLayout.addItem(spacerItem1)
        self.errorButton = QtGui.QPushButton(self.centralwidget)
        self.errorButton.setObjectName(_fromUtf8("errorButton"))
        self.verticalLayout.addWidget(self.errorButton)
        self.gridLayout.addLayout(self.verticalLayout, 0, 1, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 872, 22))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menu_About = QtGui.QMenu(self.menubar)
        self.menu_About.setObjectName(_fromUtf8("menu_About"))
        self.menuSettings = QtGui.QMenu(self.menubar)
        self.menuSettings.setObjectName(_fromUtf8("menuSettings"))
        self.menuAdvanced = QtGui.QMenu(self.menubar)
        self.menuAdvanced.setObjectName(_fromUtf8("menuAdvanced"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)
        self.actionAboutOdometer = QtGui.QAction(MainWindow)
        self.actionAboutOdometer.setObjectName(_fromUtf8("actionAboutOdometer"))
        self.actionLicenses = QtGui.QAction(MainWindow)
        self.actionLicenses.setObjectName(_fromUtf8("actionLicenses"))
        self.actionHelp = QtGui.QAction(MainWindow)
        self.actionHelp.setObjectName(_fromUtf8("actionHelp"))
        self.actionCheckForUpdates = QtGui.QAction(MainWindow)
        self.actionCheckForUpdates.setObjectName(_fromUtf8("actionCheckForUpdates"))
        self.actionLogs = QtGui.QAction(MainWindow)
        self.actionLogs.setObjectName(_fromUtf8("actionLogs"))
        self.actionShowPatterns = QtGui.QAction(MainWindow)
        self.actionShowPatterns.setObjectName(_fromUtf8("actionShowPatterns"))
        self.actionLoginOnline = QtGui.QAction(MainWindow)
        self.actionLoginOnline.setObjectName(_fromUtf8("actionLoginOnline"))
        self.actionTimelineOrderReport = QtGui.QAction(MainWindow)
        self.actionTimelineOrderReport.setCheckable(False)
        self.actionTimelineOrderReport.setEnabled(True)
        self.actionTimelineOrderReport.setObjectName(_fromUtf8("actionTimelineOrderReport"))
        self.actionReportError = QtGui.QAction(MainWindow)
        self.actionReportError.setObjectName(_fromUtf8("actionReportError"))
        self.actionAdjustThreshold = QtGui.QAction(MainWindow)
        self.actionAdjustThreshold.setCheckable(True)
        self.actionAdjustThreshold.setObjectName(_fromUtf8("actionAdjustThreshold"))
        self.actionCheckForUpdates_2 = QtGui.QAction(MainWindow)
        self.actionCheckForUpdates_2.setObjectName(_fromUtf8("actionCheckForUpdates_2"))
        self.actionManualLookup = QtGui.QAction(MainWindow)
        self.actionManualLookup.setCheckable(True)
        self.actionManualLookup.setObjectName(_fromUtf8("actionManualLookup"))
        self.menu_About.addAction(self.actionAboutOdometer)
        self.menu_About.addAction(self.actionHelp)
        self.menu_About.addAction(self.actionLicenses)
        self.menu_About.addSeparator()
        self.menu_About.addAction(self.actionCheckForUpdates_2)
        self.menuSettings.addAction(self.actionLoginOnline)
        self.menuSettings.addAction(self.actionShowPatterns)
        self.menuSettings.addAction(self.actionAdjustThreshold)
        self.menuSettings.addAction(self.actionManualLookup)
        self.menuAdvanced.addAction(self.actionTimelineOrderReport)
        self.menuAdvanced.addAction(self.actionLogs)
        self.menuAdvanced.addSeparator()
        self.menuAdvanced.addAction(self.actionReportError)
        self.menubar.addAction(self.menu_About.menuAction())
        self.menubar.addAction(self.menuSettings.menuAction())
        self.menubar.addAction(self.menuAdvanced.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "♫ ♪ Odometer", None))
        self.groupBox.setTitle(_translate("MainWindow", "Project", None))
        self.label_8.setText(_translate("MainWindow", "Production no.", None))
        self.label_11.setText(_translate("MainWindow", "Production title", None))
        self.clips.setToolTip(_translate("MainWindow", "Drop a Final Cut Pro sequence (XML export) anywhere to load it.", None))
        self.clips.setSortingEnabled(True)
        self.clips.headerItem().setText(0, _translate("MainWindow", "♫", None))
        self.clips.headerItem().setToolTip(0, _translate("MainWindow", "Check clips that you want to include in your report", None))
        self.clips.headerItem().setText(1, _translate("MainWindow", "Clip name", None))
        self.clips.headerItem().setText(2, _translate("MainWindow", "Duration", None))
        self.clips.headerItem().setToolTip(2, _translate("MainWindow", "Duration of the clip", None))
        self.clips.headerItem().setText(3, _translate("MainWindow", "Metadata", None))
        self.clips.headerItem().setToolTip(3, _translate("MainWindow", "A summary of metadata", None))
        self.errors.setTitle(_translate("MainWindow", "Errors and warnings", None))
        self.detailsBox.setTitle(_translate("MainWindow", "Details", None))
        self.buttonBox.setStatusTip(_translate("MainWindow", "Close the Details box", None))
        self.label_2.setText(_translate("MainWindow", "<b>Year</b>", None))
        self.label_3.setText(_translate("MainWindow", "<b>Label</b>", None))
        self.label_10.setText(_translate("MainWindow", "<b>Album</b>", None))
        self.label_5.setText(_translate("MainWindow", "<b>Record Number</b>", None))
        self.label_4.setText(_translate("MainWindow", "<b>Copyright Owner</b>", None))
        self.label_6.setText(_translate("MainWindow", "<b>Composer</b>", None))
        self.label_9.setText(_translate("MainWindow", "<b>Lyricist</b>", None))
        self.label_7.setText(_translate("MainWindow", "<b>Artist</b>", None))
        self.label.setText(_translate("MainWindow", "<b>Title</b>", None))
        self.loadFileButton.setStatusTip(_translate("MainWindow", "Locate a Final Cut Pro sequence (XML export) and load it.", None))
        self.loadFileButton.setText(_translate("MainWindow", "&Open file...", None))
        self.volumeThreshold.setPrefix(_translate("MainWindow", "gain > ", None))
        self.groupBox_2.setTitle(_translate("MainWindow", "Create reports", None))
        self.DMAButton.setText(_translate("MainWindow", "&PRF", None))
        self.AUXButton.setToolTip(_translate("MainWindow", "Open a report form for AUX production music", None))
        self.AUXButton.setText(_translate("MainWindow", "AUX", None))
        self.ApolloButton.setText(_translate("MainWindow", "Apollo", None))
        self.extremeButton.setText(_translate("MainWindow", "Extreme", None))
        self.UprightButton.setText(_translate("MainWindow", "Upright", None))
        self.UniversalButton.setText(_translate("MainWindow", "Universal", None))
        self.creditsButton.setToolTip(_translate("MainWindow", "Create a list that is suitable for end credits.", None))
        self.creditsButton.setText(_translate("MainWindow", "Credits", None))
        self.errorButton.setStatusTip(_translate("MainWindow", "Experiencing errors or glitches? Report it!", None))
        self.errorButton.setText(_translate("MainWindow", "Report an error", None))
        self.menu_About.setTitle(_translate("MainWindow", "About", None))
        self.menuSettings.setTitle(_translate("MainWindow", "Settings", None))
        self.menuAdvanced.setTitle(_translate("MainWindow", "Advanced", None))
        self.actionAboutOdometer.setText(_translate("MainWindow", "About ♫ ♪ Odometer", None))
        self.actionLicenses.setText(_translate("MainWindow", "Licenses", None))
        self.actionHelp.setText(_translate("MainWindow", "Help", None))
        self.actionHelp.setToolTip(_translate("MainWindow", "Show a help document", None))
        self.actionCheckForUpdates.setText(_translate("MainWindow", "Check for updates", None))
        self.actionCheckForUpdates.setToolTip(_translate("MainWindow", "Check for updates online", None))
        self.actionLogs.setText(_translate("MainWindow", "Logs", None))
        self.actionLogs.setToolTip(_translate("MainWindow", "Show application logs (helpful if something is wrong)", None))
        self.actionShowPatterns.setText(_translate("MainWindow", "Show recognised file patterns", None))
        self.actionShowPatterns.setToolTip(_translate("MainWindow", "Show recognised file name patterns", None))
        self.actionLoginOnline.setText(_translate("MainWindow", "Log on to online services", None))
        self.actionLoginOnline.setToolTip(_translate("MainWindow", "Log on to services like AUX and Apollo", None))
        self.actionTimelineOrderReport.setText(_translate("MainWindow", "Report by timeline order", None))
        self.actionTimelineOrderReport.setToolTip(_translate("MainWindow", "Create a report of all checked clips, ordered by timeline entry", None))
        self.actionReportError.setText(_translate("MainWindow", "Create an error report", None))
        self.actionAdjustThreshold.setText(_translate("MainWindow", "Adjust threshold manually", None))
        self.actionCheckForUpdates_2.setText(_translate("MainWindow", "Check for updates", None))
        self.actionManualLookup.setText(_translate("MainWindow", "Look up file manually", None))

import odometer_rc