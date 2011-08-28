#!/usr/bin/env python

# Copyright (C) 2010  Alex Yatskov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import copy
import pygame
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import QtXml
import ankiqt


class JoyDialogCapture(QtGui.QDialog):
    def __init__(self, parent, action):
        QtGui.QDialog.__init__(self, parent)

        self.setWindowTitle('Button capture')
        self.resize(300, 90)
        self.setResult(-1)

        self.label = QtGui.QLabel(self)
        self.label.setWordWrap(True)
        self.label.setText('Press the gamepad or joystick button you wish to capture for action: %s...' % action)

        self.buttonBox = QtGui.QDialogButtonBox(self)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL('accepted()'), self.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL('rejected()'), self.reject)

        self.verticalLayout = QtGui.QVBoxLayout(self)
        self.verticalLayout.setSizeConstraint(QtGui.QLayout.SetFixedSize)
        self.verticalLayout.addWidget(self.label)
        self.verticalLayout.addWidget(self.buttonBox)


    def onButton(self, value):
        self.done(value)


class JoyDialogOptions(QtGui.QDialog):
    def __init__(self, parent, plugin):
        QtGui.QDialog.__init__(self, parent)
        self.plugin = plugin

        self.setWindowTitle('Gamepad settings')
        self.resize(400, 150)

        self.groupBox = QtGui.QGroupBox(self)
        self.groupBox.setTitle('Actions')

        self.lineEditId = QtGui.QLineEdit(self.groupBox)
        self.lineEditId.setReadOnly(True)

        self.comboBoxActions = QtGui.QComboBox(self.groupBox)
        for button in self.plugin.buttonMgr.buttons:
            self.comboBoxActions.addItem(button.name)
        QtCore.QObject.connect(self.comboBoxActions, QtCore.SIGNAL('currentIndexChanged(const QString&)'), self.onActionChanged)

        self.pushButtonCapture = QtGui.QPushButton(self.groupBox)
        self.pushButtonCapture.setText('Capture...')
        QtCore.QObject.connect(self.pushButtonCapture, QtCore.SIGNAL('clicked()'), self.onCapture)

        self.checkBoxEnable = QtGui.QCheckBox(self.groupBox)
        self.checkBoxEnable.setText('Map to button')
        QtCore.QObject.connect(self.checkBoxEnable, QtCore.SIGNAL('stateChanged(int)'), self.onEnableChanged)

        self.buttonBox = QtGui.QDialogButtonBox(self)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel | QtGui.QDialogButtonBox.Ok)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL('accepted()'), self.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL('rejected()'), self.reject)

        self.gridLayout = QtGui.QGridLayout(self.groupBox)
        self.gridLayout.addWidget(self.comboBoxActions, 0, 0, 1, 3)
        self.gridLayout.addWidget(self.checkBoxEnable, 1, 0, 1, 1)
        self.gridLayout.addWidget(self.lineEditId, 1, 1, 1, 1)
        self.gridLayout.addWidget(self.pushButtonCapture, 1, 2, 1, 1)

        self.verticalLayout = QtGui.QVBoxLayout(self)
        self.verticalLayout.addWidget(self.groupBox)
        self.verticalLayout.addItem(QtGui.QSpacerItem(0, 0, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding))
        self.verticalLayout.addWidget(self.buttonBox)

        self.onActionChanged(self.comboBoxActions.currentText())
        self.onEnableChanged(self.checkBoxEnable.checkState())


    def onCapture(self):
        dialog = JoyDialogCapture(self, self.comboBoxActions.currentText())
        self.plugin.handlers.append(dialog.onButton)
        value = dialog.exec_()
        self.plugin.handlers.remove(dialog.onButton)
        if value >= 0:
            name = self.comboBoxActions.currentText()
            button = self.plugin.buttonMgr.findButtonByName(name)
            button.value = value
            self.onActionChanged(name)


    def onActionChanged(self, name):
        button = self.plugin.buttonMgr.findButtonByName(name)
        self.checkBoxEnable.setChecked(button.enabled)
        self.lineEditId.setText(str(button.value))


    def onEnableChanged(self, state):
        enabled = state == QtCore.Qt.Checked
        self.lineEditId.setEnabled(enabled)
        self.pushButtonCapture.setEnabled(enabled)
        name = self.comboBoxActions.currentText()
        button = self.plugin.buttonMgr.findButtonByName(name)
        button.enabled = enabled


class JoyButtonMap:
    def __init__(self, name, value, enabled, state, callback):
        self.name = name
        self.value = value
        self.enabled = enabled
        self.state = state
        self.callback = callback


class JoyButtonMapManager:
    def __init__(self):
        mainWin = ankiqt.mw.mainWin
        self.buttons = [
            JoyButtonMap('Answer 1',            -1, False, "showAnswer",    lambda: self.clickButton(mainWin.easeButton1)),
            JoyButtonMap('Answer 2',            -1, False, "showAnswer",    lambda: self.clickButton(mainWin.easeButton2)),
            JoyButtonMap('Answer 3',            -1, False, "showAnswer",    lambda: self.clickButton(mainWin.easeButton3)),
            JoyButtonMap('Answer 4',            -1, False, "showAnswer",    lambda: self.clickButton(mainWin.easeButton4)),
            JoyButtonMap('Answer Default',      -1, False, "showAnswer",    lambda: self.clickButton([mainWin.easeButton1, mainWin.easeButton2, mainWin.easeButton3, mainWin.easeButton4][ankiqt.mw.defaultEaseButton() - 1])),
            JoyButtonMap('Answer Incorrect',    -1, False, "showAnswer",    lambda: self.clickButton(mainWin.easeButton1)),
            JoyButtonMap('Bury Card',           -1, False, None,            lambda: self.triggerAction(mainWin.actionBuryFact)),
            JoyButtonMap('Mark Card',           -1, False, None,            lambda: self.triggerAction(mainWin.actionMarkCard)),
            JoyButtonMap('Repeat Audio',        -1, False, None,            lambda: self.triggerAction(mainWin.actionRepeatAudio)),
            JoyButtonMap('Show Answer',         -1, False, "showQuestion",  lambda: self.clickButton(mainWin.showAnswerButton)),
            JoyButtonMap('Suspend Card',        -1, False, None,            lambda: self.triggerAction(mainWin.actionSuspendCard)),
            JoyButtonMap('Undo',                -1, False, None,            lambda: self.triggerAction(mainWin.actionUndo))
        ]


    def findButtonByName(self, name):
        for button in self.buttons:
            if button.name == name:
                return button


    def findButtonsByValue(self, value):
        return [button for button in self.buttons if button.value == value]


    def handleButton(self, value):
        buttons = self.findButtonsByValue(value)
        for button in buttons:
            if button.enabled and (button.state == None or button.state == ankiqt.mw.state):
                button.callback()


    def clickButton(self, button):
        if button.isEnabled():
            button.animateClick()


    def triggerAction(self, action):
        if action.isEnabled():
            action.trigger()


    def loadSettings(self):
        try:
            fileXml = open(self.getFilename(), 'r')
            textXml = fileXml.read()
            fileXml.close()
        except IOError:
            return False

        document = QtXml.QDomDocument()
        if not document.setContent(textXml):
            return False

        root = document.documentElement()
        if root.tagName() != 'settings':
            return False

        buttonElements = root.elementsByTagName('button')
        if buttonElements != None:
            for i in xrange(0, len(buttonElements)):
                buttonElement = buttonElements.at(i).toElement()
                button = self.findButtonByName(buttonElement.attribute('name'))
                if button != None:
                    button.value = int(buttonElement.attribute('value'))
                    button.enabled = buttonElement.attribute('enabled') == 'True'

        return True


    def saveSettings(self):
        document = QtXml.QDomDocument()

        rootElement = document.createElement('settings')
        document.appendChild(rootElement)

        for button in self.buttons:
            buttonElement = document.createElement('button')
            buttonElement.setAttribute('name', button.name)
            buttonElement.setAttribute('value', str(button.value))
            buttonElement.setAttribute('enabled', str(button.enabled))
            rootElement.appendChild(buttonElement)

        textXml = document.toString(4)

        try:
            fileXml = open(self.getFilename(), 'w')
            fileXml.write(textXml)
            fileXml.close()
        except IOError:
            return False
        else:
            return True


    def getFilename(self):
        return os.path.splitext(__file__)[0] + '.xml'


class JoyPlugin:
    def __init__(self):
        pygame.init()

        self.handlers = []
        self.joysticks = []
        for i in xrange(pygame.joystick.get_count()):
            joystick = pygame.joystick.Joystick(i)
            joystick.init()
            self.joysticks.append(joystick)

        self.buttonMgr = JoyButtonMapManager()
        self.buttonMgr.loadSettings()

        action = QtGui.QAction(ankiqt.mw)
        action.setText('&Joypad Options...')
        QtCore.QObject.connect(action, QtCore.SIGNAL('triggered()'), self.onOptions)
        ankiqt.mw.mainWin.menu_Settings.insertAction(ankiqt.mw.mainWin.actionStudyOptions, action)

        self.timer = QtCore.QTimer()
        QtCore.QObject.connect(self.timer, QtCore.SIGNAL('timeout()'), self.onTimer)
        self.timer.start(50)


    def onTimer(self):
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                self.onButton(event.button)


    def onOptions(self):
        dialog = JoyDialogOptions(ankiqt.mw, self)
        buttonMgrOld = copy.deepcopy(self.buttonMgr)
        if dialog.exec_() == QtGui.QDialog.Accepted:
            self.buttonMgr.saveSettings()
        else:
            self.buttonMgr = buttonMgrOld


    def onButton(self, value):
        if len(self.handlers) > 0:
            for handler in self.handlers:
                handler(value)
        else:
            self.buttonMgr.handleButton(value)


plugin = JoyPlugin()
