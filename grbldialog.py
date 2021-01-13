from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import *
import threading
from builtins import bytes

from objectviewer import *
from tools.pathtool import *
import serial
from guifw.gui_elements import *
import os, fnmatch


class SerialPort(object):
    '''auto-detected serial port'''

    def __init__(self, device, description=None, hwid=None):
        self.device = device
        self.description = description
        self.hwid = hwid
        self.port = None

    def open(self, device=None):
        if device is not None:
            self.device = device
        try:
            self.port = serial.Serial(str(self.device), 115200, timeout=0, dsrdtr=False, rtscts=False, xonxoff=False)
            # self.port.setBaudrate(115200)
            # self.port.baudrate=115200
        except:
            print(self.device, "Serial port not found!")
            self.port = None
        try:
            fd = self.port.fileno()
            # set_close_on_exec(fd)
        except Exception:
            fd = None

        print("successfully opened", str(self.device))
        time.sleep(1.0)
        print("serial port ready.", str(self.device))

    def close(self):
        if self.port is not None:
            print("closing open connection")
            self.port.close()
            self.port = None

    def reopen(self, device=None):
        self.close()
        self.open(device)

    def write_raw(self, bmsg):
        if self.port is not None:
            self.port.write(bmsg)

    def write(self, msg):
        if self.port is not None:
            self.port.write(msg.encode('iso-8859-1'))

    def flush(self):
        if self.port is not None:
            self.port.flush()

    def __str__(self):
        ret = self.device
        if self.description is not None:
            ret += " : " + self.description
        if self.hwid is not None:
            ret += " : " + self.hwid
        return ret


def auto_detect_serial_win32(preferred_list=['*']):
    '''try to auto-detect serial ports on win32'''
    try:
        from serial.tools.list_ports_windows import comports
        list = sorted(comports())
    except:
        return []
    ret = []
    others = []
    for port, description, hwid in list:
        matches = False
        p = SerialPort(port, description=description, hwid=hwid)
        for preferred in preferred_list:
            if fnmatch.fnmatch(description, preferred) or fnmatch.fnmatch(hwid, preferred):
                matches = True
        if matches:
            ret.append(p)
        else:
            others.append(p)
    if len(ret) > 0:
        return ret
    # now the rest
    ret.extend(others)
    return ret


def auto_detect_serial_unix(preferred_list=['*']):
    '''try to auto-detect serial ports on unix'''
    import glob
    # glist = glob.glob('/dev/ttyS*') + glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob('/dev/serial/by-id/*')
    glist = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob('/dev/serial/by-id/*') + glob.glob('/dev/tty.usb*') + glob.glob('/dev/tty.wchusb*')
    ret = []
    others = []
    # try preferred ones first
    for d in glist:
        matches = False
        for preferred in preferred_list:
            if fnmatch.fnmatch(d, preferred):
                matches = True
        if matches:
            ret.append(SerialPort(d))
        else:
            others.append(SerialPort(d))
    if len(ret) > 0:
        return ret
    ret.extend(others)
    return ret


def auto_detect_serial(preferred_list=['*']):
    '''try to auto-detect serial port'''
    # see if 
    if os.name == 'nt':
        return auto_detect_serial_win32(preferred_list=preferred_list)
    return auto_detect_serial_unix(preferred_list=preferred_list)


class GrblInterface():
    def __init__(self, portname="/dev/ttyUSB0"):
        self.read_timer = QtCore.QTimer()
        self.read_timer.setInterval(2)
        self.read_timer.timeout.connect(self.readSerial)

        self.serial = SerialPort("")
        self.reopenSerial(portname)
        self.receive_buffer = ""
        self.pending = False
        self.jogging = False
        self.update_pending = True

        self.feedrate = 1000
        self.axes = [0.0, 0.0, 0.0]
        self.offsets = [0.0, 0.0, 0.0]
        self.overrides = [100.0, 100.0, 100.0]
        self.current_jog_dir=[0.0, 0.0, 0.0]
        self.jog_scale = [1000, 1000, 1000]
        self.actualFeed = 0.0
        self.status = ""
        self.status_callback = None
        self.last_transmission_timer = 10000

    def reopenSerial(self, device=None):
        # self.read_timer.stop()
        self.read_timer.setInterval(1000)
        self.serial.close()
        self.serial.open(device)
        if self.serial.port is not None:
            self.read_timer.setInterval(2)
            self.read_timer.start()
        else:
            print("Serial connection closed.")

    def readSerial(self):
        if self.serial.port is None:
            self.reopenSerial()
            self.read_timer.setInterval(1000)
            return
        try:
            self.receive_buffer += self.serial.port.read(200).decode('iso-8859-1')
        except serial.SerialException:
            self.reopenSerial()
            return

        lines = self.receive_buffer.split('\n', 1)
        while len(lines) > 1:
            line = lines[0].strip()
            self.receive_buffer = lines[1]
            if len(line) > 0:
                print("received:", line)
                self.parseGRBLStatus(line.strip())
            lines = self.receive_buffer.split('\n', 1)

        # get more updates if not idle, or for a certain time after the last transmission
        # (to capture short movements, to avoid missing the Idle->Jog->Idle transition)
        if (self.status != "Idle" or self.last_transmission_timer < 200) and \
                ((self.last_transmission_timer % 500) == 0 or (
                        not self.update_pending and (self.last_transmission_timer % 50) == 0)):
            self.getUpdate()
        self.last_transmission_timer += 1

        # check if we stopped jogging and machine is still moving - keep sending stop commands
        if not self.jogging and self.status == "Jog" and (self.last_transmission_timer % 20) == 0:
            self.stopJog()

    def parseGRBLStatus(self, line):
        try:
            if line == "ok":
                self.pending = False
            elif len(line) > 5 and line[0:5] == "error":
                self.pending = False
                print("ERROR:", line)
            elif len(line) > 1 and line[0] == '<':
                self.update_pending = False
                parts = line.split(">")[0].split("|")
                self.status = parts[0][1:]
                for i in range(1, len(parts)):
                    part = parts[i]
                    if part[0:5] == "MPos:":
                        self.axes = [float(c) for c in part[5:].split(",")]
                    if part[0:5] == "WPos:":
                        self.axes = [float(c) for c in part[5:].split(",")]

                    if part[0:4] == "WCO:":
                        self.offsets = [float(c) for c in part[4:].split(",")]
                    if part[0:3] == "Ov:":
                        self.overrides = [float(c) for c in part[3:].split(",")]
                    if part[0:3] == "Ov:":
                        self.overrides = [float(c) for c in part[3:].split(",")]
                        print("overrides: ", self.overrides)
                    if part[0:3] == "FS:":
                        self.actualFeed = [float(c) for c in part[3:].split(",")]
        except:
            print("GRBL parse error:", line)
        # print self.status, "mpos:", self.axes, "off:", self.offsets
        if self.status_callback is not None:
            self.status_callback(self)

    def sendGCommand(self, gcode):
        self.serial.write(gcode)
        self.serial.write("\n")
        self.serial.flush()
        print("sent:", gcode)
        self.pending = True
        self.last_transmission_timer = 0

    def sendFeedHold(self):
        self.serial.write("!")
        self.serial.flush()
        print("feed hold")

    def sendResume(self):
        self.serial.write("~")
        self.serial.flush()
        print("resume")

    def sendCancel(self):
        self.serial.write_raw(b'\x18')  # send a Ctrl-X (cancel/abort)
        self.serial.flush()
        print("cancel")

    def startJog(self, command):
        gcode = ""
        if command == "xm":
            self.current_jog_dir[0]=-1 * self.jog_scale[0]
        if command == "xp":
            self.current_jog_dir[0]=1 * self.jog_scale[0]
        if command == "ym":
            self.current_jog_dir[1]=-1 * self.jog_scale[1]
        if command == "yp":
            self.current_jog_dir[1]=1 * self.jog_scale[1]
        if command == "zm":
            self.current_jog_dir[2]=-1 * self.jog_scale[2]
        if command == "zp":
            self.current_jog_dir[2]=1 * self.jog_scale[2]
        if command == "am":
            gcode = "$J=G91A-1000F%i\n?" % (self.feedrate)
        if command == "ap":
            gcode = "$J=G91A1000F%i\n?" % (self.feedrate)
        if command == "bm":
            gcode = "$J=G91B-1000F%i\n?" % (self.feedrate)
        if command == "bp":
            gcode = "$J=G91B1000F%i\n?" % (self.feedrate)
        if command == "cm":
            gcode = "$J=G91C-1000F%i\n?" % (self.feedrate)
        if command == "cp":
            gcode = "$J=G91C1000F%i\n?" % (self.feedrate)


        gcode = "$J=G91X%i Y%i Z%i F%i\n?" % (self.current_jog_dir[0], self.current_jog_dir[1], self.current_jog_dir[2], self.feedrate)

        self.serial.write_raw(b'\x85')
        self.serial.flush()
        self.serial.write(gcode)
        self.sendResume()
        self.serial.flush()
        self.jogging = True
        self.last_transmission_timer = 0
        self.pending = True
        print("sent:", gcode)

    def getUpdate(self):
        self.serial.write("?")
        self.serial.flush()
        self.update_pending = True
        # print "request update..."

    def stopJog(self, command=""):
        print("stop jog")
        if command == "xm" or command == "xp":
            self.current_jog_dir[0]=0
        if command == "ym" or command == "yp":
            self.current_jog_dir[1]=0
        if command == "zm" or command == "zp":
            self.current_jog_dir[2]=0

        self.serial.write_raw(b'\x85')
        self.serial.flush()
        self.pending = False
        self.jogging = False
        self.last_transmission_timer = 0

        #if all(v == 0 for v in self.current_jog_dir):
        #    self.startJog("")

    def setFeedOverride(self, value):
        currentValue = self.overrides[0]
        # self.port.write(b'\x90') #set to programmed rate
        tens = int((value - currentValue) / 10)
        ones = int((value - currentValue)) - 10 * tens
        print(tens, ones)
        while tens > 0:
            self.serial.write_raw(b'\x91')  # increase by 10%
            self.serial.write('\n')  # increase by 10%
            tens -= 1
        while ones > 0:
            self.serial.write_raw(b'\x93')  # increase by 1%
            self.serial.write('\n')
            ones -= 1
        while tens < 0:
            self.serial.write_raw(b'\x92')  # decrease by 10%
            self.serial.write('\n')  # increase by 10%
            tens += 1
        while ones < 0:
            self.serial.write_raw(b'\x94')  # decrease by 1%
            self.serial.write('\n')
            ones += 1
        self.serial.write('?')
        self.serial.flush()
        print("send feed override")


class RTButton(QtGui.QPushButton):
    def __init__(self, name="", command="", machine_interface=None, size=50):
        QtGui.QPushButton.__init__(self, name)
        self.machine_interface = machine_interface
        self.setFixedHeight(size)
        self.setFixedWidth(size)
        self.setAutoRepeat(True)
        self.setAutoRepeatDelay(10)
        self.setAutoRepeatInterval(50)
        self.clicked.connect(self.handleClicked)
        self.released.connect(self.handleClicked)
        self._state = 0
        self.command = command
        self.setContentsMargins(0,0,0,0)

    def handleClicked(self):
        if self.isDown():
            if self._state == 0:
                self._state = 1
                print('start', self.command)
                self.machine_interface.startJog(self.command)
            else:
                # self.machine_interface.startJog(self.command)
                # print self.command
                None
        elif self._state == 1:
            self._state = 0
            self.machine_interface.stopJog(self.command)
            print('stop')
        else:
            # self.machine_interface.stopJog()
            print('click')


class AxisDisplayWidget(LabeledTextField):
    def __init__(self, label="", value=None, height=30):
        LabeledTextField.__init__(self, label=label, value=value, formatString="{:4.3f}", editable=True)
        self.setFixedWidth(250)
        self.setFixedHeight(height)
        self.font = QtGui.QFont("Helvetica [Cronyx]", 16);

        self.setFont(self.font)
        self.label.setFixedHeight(30)
        self.text.setFixedHeight(height)
        self.zero_button = QtGui.QPushButton("0")
        self.half_button = QtGui.QPushButton("1/2")
        self.zero_button.pressed.connect(self.zeroButtonPushed)
        self.half_button.pressed.connect(self.halfButtonPushed)
        self.zero_button.setFixedWidth(45)
        self.zero_button.setFixedHeight(height)
        self.half_button.setFixedWidth(45)
        self.half_button.setFixedHeight(height)
        self.layout.addWidget(self.zero_button)
        self.layout.addWidget(self.half_button)
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(0)


    def zeroButtonPushed(self):
        self.text.setText("0.0")
        self.textEditedHandler()

    def halfButtonPushed(self):
        current_pos = float(self.text.text())
        self.text.setText("%f" % (current_pos / 2.0))
        self.textEditedHandler()


class AxesWidget(QtGui.QWidget):
    def __init__(self, machine_interface=None,
                 display_axes = ["X", "Y", "Z"],
                 machine_axes=["X", "Y", "Z", "A", "B", "C"],
                 displayHeight=40):
        QtGui.QWidget.__init__(self)
        self.statuslayout = QtGui.QGridLayout()
        self.machine_interface = machine_interface
        self.setLayout(self.statuslayout)

        self.statuslayout.setSpacing(0)
        self.statuslayout.setContentsMargins(0,0,0,0)

        self.font = QtGui.QFont("Helvetica [Cronyx]", 16);
        self.status = QtGui.QLabel("---")
        self.status.setFixedWidth(150)
        self.status.setFixedHeight(25)
        self.status.setFont(self.font)

        self.statuslayout.addWidget(self.status, 0, 0)

        self.actualFeedDisplay = LabeledTextField(label="Feed", value=0.0, formatString="{:4.1f}", editable=False)
        self.actualFeedDisplay.setFixedWidth(200)
        self.statuslayout.addWidget(self.actualFeedDisplay, 1, 0)

        self.machine_axes = machine_axes
        self.axes_names = display_axes
        self.number_of_axes = len(self.axes_names)
        self.wcs_names = ["G53", "G54", "G55", "G56", "G57", "G58", "G59"]
        self.position_fields = [AxisDisplayWidget(label=self.axes_names[i], value=0.0, height = displayHeight) for i in
                                range(0, self.number_of_axes)]
        self.wcs_fields = [
            CommandButton(name=self.wcs_names[i], width=30, height=30, callback=self.changeWCS, callback_argument=i) for
            i in range(0, len(self.wcs_names))]
        self.active_wcs = 1

        self.wcs_widget = QtGui.QWidget()

        wcs_layout = QtGui.QHBoxLayout()
        wcs_layout.setSpacing(0)
        wcs_layout.setContentsMargins(0,0,0,0)
        self.wcs_widget.setLayout(wcs_layout)
        for i in range(0, len(self.wcs_names)):
            wcs_layout.addWidget(self.wcs_fields[i])

        for i in range(0, self.number_of_axes):
            p = self.position_fields[i]
            p.edited_callback = self.axisEdited
            p.edited_callback_argument = i
            self.statuslayout.addWidget(self.position_fields[i], i + 2, 0)
        self.statuslayout.addWidget(self.wcs_widget, self.number_of_axes + 2, 0)

        self.statuslayout.addWidget(QtGui.QLabel(""), 0, 4)

        self.machine_interface.status_callback = self.updateStatus

    def changeWCS(self, wcs_index):
        self.machine_interface.sendGCommand(self.wcs_names[wcs_index] + "\n")
        self.active_wcs = wcs_index

    def axisEdited(self, index):
        new_text = self.position_fields[index].text.text()
        try:
            new_pos = float(new_text)
            print(self.axes_names[index], new_pos)
            self.machine_interface.sendGCommand("G10 P%i L20 %s%f" % (self.active_wcs, self.axes_names[index], new_pos))
            time.sleep(0.1)
            self.machine_interface.getUpdate()
        except:
            print("invalid number")
            self.updateStatus(self.machine_interface)

    def updateStatus(self, machine_interface):
        self.status.setText(machine_interface.status)
        self.actualFeedDisplay.updateValue(machine_interface.actualFeed)

        for i in range(0, self.number_of_axes):
            if self.machine_axes[i] in self.axes_names:
                di = self.axes_names.index(self.machine_axes[i])
                self.position_fields[di].updateValue(machine_interface.axes[i] - machine_interface.offsets[i])


class CursorWidget(QtGui.QWidget):
    def __init__(self,
                 machine_interface=None,
                 buttonsize=50,
                 axes = [["<", "xm", QtCore.Qt.Key_Left,      1, 0],
                         [">", "xp", QtCore.Qt.Key_Right,     1, 2],
                         ["v", "ym", QtCore.Qt.Key_Down,      1, 1],
                         ["^", "yp", QtCore.Qt.Key_Up,        0, 1],
                         ["z-", "zm", QtCore.Qt.Key_PageDown, 1, 3],
                         ["z+", "zp", QtCore.Qt.Key_PageUp,   0, 3]
                  ]):
        QtGui.QWidget.__init__(self)
        cursorlayout = QtGui.QGridLayout()
        cursorWidget = QtGui.QWidget()
        layout = QtGui.QVBoxLayout()

        layout.setSpacing(0)
        layout.setContentsMargins(0,0,0,0)

        cursorlayout.setSpacing(0)
        cursorlayout.setContentsMargins(0,0,0,0)


        cursorWidget.setLayout(cursorlayout)
        self.machine_interface = machine_interface
        self.axes = axes
        self.setLayout(layout)

        self.axis_buttons=[]
        for a in self.axes:
            self.axis_buttons.append(RTButton(a[0], command=a[1], machine_interface=machine_interface, size=buttonsize))
            cursorlayout.addWidget(self.axis_buttons[-1], a[3], a[4])

        self.rapidbutton = QtGui.QPushButton("Rapid")
        self.rapidbutton.setFixedHeight(buttonsize)
        self.rapidbutton.setFixedWidth(buttonsize)
        self.rapidbutton.clicked.connect(self.rapidButtonClicked)
        self.rapidbutton.setCheckable(True)

        cursorlayout.addWidget(self.rapidbutton, 0, 0)

        columns=max([a[4] for a in self.axes])+1
        cursorWidget.setFixedWidth(buttonsize*columns +2)
        cursorWidget.setFixedHeight(buttonsize*2 +2)

        layout.addWidget(cursorWidget)

        self.jogfeed = LabeledNumberField(label="Jogspeed", min=0, max=1000, value=400, step=50, slider=True)
        self.jogfeed.number.valueChanged.connect(self.rapidButtonClicked)
        self.rapidfeed = LabeledNumberField(label="Rapid speed", min=0, max=8000, value=2000, step=50)#, slider=False)
        layout.addWidget(self.rapidfeed)
        layout.addWidget(self.jogfeed)
        #self.setFixedWidth(buttonsize*4 +35)
        self.machine_interface.feedrate = self.jogfeed.number.value()

        QtWidgets.qApp.installEventFilter(self)

    def rapidButtonClicked(self):
        if self.rapidbutton.isChecked():
            self.machine_interface.feedrate = self.rapidfeed.number.value()
            print("rapid on")
        else:
            self.machine_interface.feedrate = self.jogfeed.number.value()
            print("rapid off")

    def eventFilter(self, source, event):
        key_caught = False
        if not self.isVisible():  # ignore events if not visible
            return super(CursorWidget, self).eventFilter(source, event)
        if event.type() == QtCore.QEvent.KeyPress:

            # print('KeyPress: %s [%r]' % (event.key(), source))
            key = event.key()
            mod = int(event.modifiers())

            for a, ab in zip(self.axes, self.axis_buttons):
                if key == a[2]:
                    if not event.isAutoRepeat():
                        ab.setDown(True)
                    key_caught=True

            if key == QtCore.Qt.Key_Shift:
                self.rapidbutton.setChecked(True)
                self.rapidButtonClicked()
                return True

        elif event.type() == QtCore.QEvent.KeyRelease:
            # print('KeyRelease: %s [%r]' % (event.key(), source))
            key = event.key()
            mod = int(event.modifiers())

            for a, ab in zip(self.axes, self.axis_buttons):
                if key == a[2]:
                    if not event.isAutoRepeat():
                        ab.setDown(False)
                        ab.handleClicked()
                    key_caught = True

            if key == QtCore.Qt.Key_Shift:
                self.rapidbutton.setChecked(False)
                self.rapidButtonClicked()
                return True

        # not a filtered key
        if not key_caught:
            return super(CursorWidget, self).eventFilter(source, event)
        else:
            return True




class GCodeWidget(QtGui.QWidget):
    def __init__(self, machine_interface=None, path_dialog=None, editor=None):
        QtGui.QWidget.__init__(self)
        self.path_dialog = path_dialog
        self.machine_interface = machine_interface

        self.current_gcode = []
        self.current_line_number = 0

        buttonlayout = QtGui.QHBoxLayout()
        self.buttonwidget = QtGui.QWidget()
        self.buttonwidget.setLayout(buttonlayout)
        self.layout = QtGui.QVBoxLayout()
        self.layout.setSpacing(0)

        self.editor=editor

        self.setLayout(self.layout)

        self.startButton = QtGui.QPushButton("Start")
        self.startButton.setToolTip("F5")
        self.startButton.setFixedWidth(60)
        self.startButton.setFixedHeight(30)
        self.startButton.pressed.connect(self.startPushed)
        self.stopButton = QtGui.QPushButton("Stop")
        self.stopButton.setToolTip("ESC")
        self.stopButton.setFixedWidth(60)
        self.stopButton.setFixedHeight(30)
        self.stopButton.pressed.connect(self.stopPushed)
        self.pauseButton = QtGui.QPushButton("Hold")
        self.pauseButton.setToolTip("H")
        self.pauseButton.setFixedWidth(60)
        self.pauseButton.setFixedHeight(30)
        self.pauseButton.clicked.connect(self.pausePushed)
        self.pauseButton.setCheckable(True)
        self.stepButton = QtGui.QPushButton("Step")
        self.stepButton.setFixedWidth(60)
        self.stepButton.setFixedHeight(30)
        self.stepButton.clicked.connect(self.sendGCode)
        buttonlayout.addWidget(self.startButton)
        buttonlayout.addWidget(self.stopButton)
        buttonlayout.addWidget(self.pauseButton)
        buttonlayout.addWidget(self.stepButton)
        buttonlayout.addStretch()
        buttonlayout.setSpacing(0)

        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0,0,0,0)

        self.layout.addWidget(self.buttonwidget)
        self.feedrate_override = LabeledNumberField(label="Feedrate override", min=0, max=200, value=100, step=1.0,
                                                    slider=True)
        self.feedrate_override.number.valueChanged.connect(self.feedrateOverrideHandler)
        self.feedrate_override.setFixedWidth(200)
        self.layout.addWidget(self.feedrate_override)

        self.manual_enter = QtGui.QLineEdit(parent=self)
        self.manual_enter.returnPressed.connect(self.manualGCodeHandler)
        self.layout.addWidget(self.manual_enter)

        self.send_timer = QtCore.QTimer()
        self.send_timer.setInterval(1)
        self.send_timer.timeout.connect(self.sendGCode)
        QtWidgets.qApp.installEventFilter(self)

    def feedrateOverrideHandler(self):
        feedrate_override = self.feedrate_override.number.value()
        self.machine_interface.setFeedOverride(feedrate_override)

    def manualGCodeHandler(self):
        command = str(self.manual_enter.text())
        print("sending:", command)
        self.machine_interface.sendGCommand(command)
        self.manual_enter.clear()

    def sendGCode(self):
        if self.machine_interface.pending:
            #None
            return
        if self.current_line_number < len(self.current_gcode):
            self.machine_interface.sendGCommand(self.current_gcode[self.current_line_number])
            if self.editor is not None:
                self.editor.highlightLine(self.current_line_number, refresh = True)
            self.current_line_number += 1
        else:
            self.send_timer.stop()

    def startPushed(self):
        if self.editor is not None:
            self.current_gcode = self.editor.getText()

        elif self.path_dialog is not None and self.path_dialog.pathtab.selectedTool is not None:
            gcode = self.path_dialog.pathtab.selectedTool.getCompletePath()
            self.current_gcode = gcode.toText().split("\n")

        if len(self.current_gcode)>0:
            self.current_line_number = 0
            if not self.pauseButton.isChecked():
                self.send_timer.start()

    def stopPushed(self):
        self.machine_interface.sendFeedHold()
        time.sleep(0.5)
        self.machine_interface.sendCancel()
        self.pauseButton.setChecked(False)
        self.send_timer.stop()

    def pausePushed(self):
        if self.pauseButton.isChecked():
            self.machine_interface.sendFeedHold()
            self.send_timer.stop()
            print("pause")
        else:
            self.machine_interface.sendResume()
            self.send_timer.start()
            print("unpause")

    def eventFilter(self, source, event):
        key_caught = False
        if not self.isVisible():  # ignore events if not visible
            return super(GCodeWidget, self).eventFilter(source, event)
        if event.type() == QtCore.QEvent.KeyPress:
            key = event.key()
            mod = int(event.modifiers())
            if not event.isAutoRepeat():
                if key == QtCore.Qt.Key_H:
                    self.pauseButton.setChecked(not self.pauseButton.isChecked())
                    self.pausePushed()
                    key_caught=True
                if key == QtCore.Qt.Key_Escape:
                    self.stopPushed()
                    key_caught=True
                if key == QtCore.Qt.Key_F5:
                    self.startPushed()
                    key_caught=True
                if key == QtCore.Qt.Key_F7:
                    self.sendGCode()
                    key_caught=True

        if event.type() == QtCore.QEvent.KeyRelease:
            key = event.key()
            mod = int(event.modifiers())
            if not event.isAutoRepeat():
                #if key == QtCore.Qt.Key_Space:
                    #self.pauseButton.setChecked(False)
               None
        if not key_caught:
            return super(GCodeWidget, self).eventFilter(source, event)
        else:
            return True


class GrblDialog(QtGui.QWidget):
    def __init__(self, path_dialog=None, editor=None, layout="vertical", machine="mill", device = None):
        QtGui.QWidget.__init__(self)
        self.path_dialog = path_dialog
        self.machine_interface = GrblInterface(portname=device)
        self.serialPorts = []
        self.serialSelect = PlainComboField(parent=self, label='Serial port',
                                            choices=[s.device for s in self.serialPorts],
                                            value=self.machine_interface.serial.device,
                                            onOpenCallback=self.rescanForSerials)

        self.rescanForSerials()
        self.reopenSerial(0)
        self.serialSelect.currentIndexChanged.connect(self.reopenSerial)
        self.serialSelect.highlighted.connect(self.rescanForSerials)
        self.serialSelect.setFixedWidth(100)

        axes = [["<", "xm", QtCore.Qt.Key_Left, 1, 0],
                [">", "xp", QtCore.Qt.Key_Right, 1, 2],
                ["v", "ym", QtCore.Qt.Key_Down, 1, 1],
                ["^", "yp", QtCore.Qt.Key_Up, 0, 1],
                ["z-", "zm", QtCore.Qt.Key_PageDown, 1, 3],
                ["z+", "zp", QtCore.Qt.Key_PageUp, 0, 3]]
        display_axes = ["X", "Y", "Z"]

        if machine == "mill":
            axes = [["<", "xm", QtCore.Qt.Key_Left, 1, 0],
                    [">", "xp", QtCore.Qt.Key_Right, 1, 2],
                    ["v", "ym", QtCore.Qt.Key_Down, 1, 1],
                    ["^", "yp", QtCore.Qt.Key_Up, 0, 1],
                    ["z-", "zm", QtCore.Qt.Key_PageDown, 1, 3],
                    ["z+", "zp", QtCore.Qt.Key_PageUp, 0, 3]]

        if machine == "lathe":
            axes = [["<", "zm", QtCore.Qt.Key_Left, 1, 0],
                    [">", "zp", QtCore.Qt.Key_Right, 1, 2],
                    ["v", "xp", QtCore.Qt.Key_Down, 1, 1],
                    ["^", "xm", QtCore.Qt.Key_Up, 0, 1],]
            display_axes = ["X", "Y", "Z"]
            self.machine_interface.jog_scale[0] = 2000 # scale X axis twice as big in lathe mode (diameter mode, to get 45 degree movement)

        if layout == "vertical":
            mlayout = QtGui.QVBoxLayout()
            self.setLayout(mlayout)
            mlayout.setSpacing(0)
            mlayout.setContentsMargins(0, 0, 0, 0)

            mlayout.setSpacing(0)
            self.status = AxesWidget(machine_interface=self.machine_interface, display_axes=display_axes,
                                     displayHeight=45)
            self.cursors = CursorWidget(machine_interface=self.machine_interface, buttonsize=50, axes=axes)
            self.gcode = GCodeWidget(machine_interface=self.machine_interface, path_dialog=self.path_dialog,
                                     editor=editor)

            mlayout.addWidget(self.status)
            mlayout.addWidget(self.cursors)
            mlayout.addWidget(self.gcode)
            mlayout.addStretch(0)
            mlayout.addWidget(self.serialSelect)
            # mlayout.addWidget(self.connectButton)

        if layout == "horizontal":
            mlayout = QtGui.QHBoxLayout()
            mlayout.setSpacing(0)
            mlayout.setContentsMargins(0, 0, 0, 0)
            self.setLayout(mlayout)
            self.cursors = CursorWidget(machine_interface=self.machine_interface)
            self.status = AxesWidget(machine_interface=self.machine_interface)
            self.gcode = GCodeWidget(machine_interface=self.machine_interface, path_dialog=self.path_dialog)
            mlayout.addWidget(self.cursors)
            mlayout.addWidget(self.gcode)
            mlayout.addWidget(self.status)
            #mlayout.addStretch(0)

    def rescanForSerials(self):
        self.serialPorts = auto_detect_serial()
        print("found serial ports: ", [s.device for s in self.serialPorts])
        self.serialSelect.updateChoices([s.device for s in self.serialPorts])

    def reopenSerial(self, index):
        if index>=0 and index<len(self.serialPorts):
            device=self.serialPorts[index]
            print (device)
            self.machine_interface.reopenSerial(device)
        else:
            print("No valid serial port found. ", self.serialPorts, index)

if __name__ == '__main__':
    import sys
    app = QtGui.QApplication([])
    device = "/dev/ttyUSB0"
    if len(sys.argv)>1:
       device = sys.argv[1]
    grbldialog = GrblDialog(layout="horizontal", device = device)
    grbldialog.show()
    ## Start the Qt event loop
    app.exec_()
