'''
MAVUE v0.1 (beta)
Graphical inspector for MAVLink enabled embedded systems.

Copyright (c) 2009-2014, Felix Schill
All rights reserved.
Refer to the file LICENSE.TXT which should be included in all distributions of this project.
'''


from PyQt5 import Qt, QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import *
import math
import sys
import traceback
from importlib import *

class HorizontalBar(QWidget):
    def __init__(self,  parent=None):
        QWidget.__init__( self, parent=parent)
        self.items=[]
        self.layout=QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(0)


    def add(self,  widget,  signal,  action):
        self.layout.addWidget(widget)
        self.items.append(widget)
        getattr(widget, signal).connect(action)

class CommandButton(QtWidgets.QPushButton):
    def __init__(self, name="", width=None, height=None,  callback=None,  callback_argument=None):
        QtWidgets.QPushButton.__init__(self, name)
        if height is not None:
            self.setFixedHeight(height)
        if width is not None:
            self.setFixedWidth(width)
        self.clicked.connect(self.clickedHandler)
        self.callback=callback
        self.callback_argument=callback_argument
        self.setContentsMargins(0,0,0,0)


    def clickedHandler(self):
        if self.callback is not None:
            self.callback(self.callback_argument)


class PlainComboField(QComboBox):
    def __init__(self, parent=None,  label="", value=None,  choices=None,  onOpenCallback=None):
        QtWidgets.QComboBox.__init__( self, parent=parent)
        self.choices = choices
        self.onOpenCallback = onOpenCallback
        if not value in choices:
            self.choices.append(value)
        for t in choices:
            self.addItem(str(t))
        if value!=None:
            self.setCurrentIndex(list(self.choices).index(value))
        self.combo=self

    def update(self,  parameter):
        if parameter!=None:
            self.combo.setCurrentIndex(self.choices.index(parameter.getValue()))

    def updateValue(self,  value):
        if value!=None:
            self.combo.setCurrentIndex(self.choices.index(value))

    def showPopup(self):
        if self.onOpenCallback!=None:
            self.onOpenCallback()
        QtWidgets.QComboBox.showPopup(self)

    def updateChoices(self,  choices):
        changed=False
        for mc,nc in zip(self.choices,  choices):
            if mc != nc:
                changed=  True
        if not changed:
            return
        self.clear()

        self.choices = choices
        for t in choices:
            self.addItem(t)



class LabeledComboField(QWidget):
    def __init__(self, parent=None,  label="", value=None,  choices=None):
        QWidget.__init__( self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.label=QtWidgets.QLabel(label)
        self.layout.addWidget(self.label)
        self.combo=QtWidgets.QComboBox(parent=self)
        self.choices = choices
        self.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(0)
        for t in choices:
            self.combo.addItem(t)
        if value!=None and value in choices:
            self.combo.setCurrentIndex(choices.index(value))
        self.layout.addWidget(self.combo)

    def update(self,  parameter):
        if parameter!=None:
            self.combo.setCurrentIndex(self.choices.index(parameter.getValueString()))

    def updateValue(self,  value):
        if value!=None:
            self.combo.setCurrentIndex(self.choices.index(value))

    def updateChoices(self, choices):
        changed = False
        for mc, nc in zip(self.choices, choices):
            if mc != nc:
                changed = True
        if not changed:
            return

        self.choices = choices
        self.combo.clear()

        for t in choices:
            self.combo.addItem(t)

class LabeledTextField(QWidget):
    def __init__(self, parent=None, editable=True,  label="", value=None,  formatString="{:s}"):
        QWidget.__init__( self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.formatString=formatString
        self.editable=editable
        self.label=QtWidgets.QLabel(label)
        self.layout.addWidget(self.label)
        self.text=QtWidgets.QLineEdit(parent=self)
        self.text.setReadOnly(not self.editable)
        self.text.returnPressed.connect(self.textEditedHandler)
        self.edited_callback=None
        self.edited_callback_argument=self

        self.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(0)
        if value!=None:
            self.text.setText(formatString.format(value))
        self.layout.addWidget(self.text)

    def update(self,  parameter):
        if parameter!=None:
            self.updateValue(parameter.getValue())

    def updateValue(self,  value=None):
        if value!=None:
            # check if value is a multi-value object:
            if isinstance(value, (list,  frozenset,  tuple,  set,  bytearray)):
                self.text.setText(''.join(self.formatString.format(x) for x in value))
            else:
                self.text.setText(self.formatString.format(value))

    def textEditedHandler(self):
        if self.edited_callback is not None:
            self.edited_callback(self.edited_callback_argument)


class LabeledProgressField(QWidget):
    def __init__(self, parent=None,  label="", value=None, min=None,  max=None,  step=1.0):
        QWidget.__init__( self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.label=QtWidgets.QLabel(label)
        self.layout.addWidget(self.label)
        self.progress=QtWidgets.QProgressBar(parent=self)
        self.updateValue(value=value,  min=min,  max=max)
        self.layout.addWidget(self.progress)

    def update(self,  parameter):
        if parameter!=None:
            self.updateValue(parameter.getValue(),  parameter.min,  parameter.max)

    def updateValue(self,  value,  min,  max):
        self.progress.setMinimum(min)
        self.progress.setMaximum(max)
        self.progress.setValue(value)

class LabeledFileField(QWidget):
    def __init__(self, parent=None, editable=True,  label="", value=None, type="open",  fileSelectionPattern="All files (*.*)"):
        QWidget.__init__( self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.type = type
        self.setLayout(self.layout)
        self.fileSelectionPattern=fileSelectionPattern
        self.editable=editable
        self.label=QtWidgets.QLabel(label)
        self.layout.addWidget(self.label)
        self.text=QtWidgets.QLineEdit(parent=self)
        self.text.setReadOnly(not self.editable)
        if value!=None:
            self.text.setText(formatString.format(value))
        self.layout.addWidget(self.text)

        self.fileDialogButton=QtWidgets.QPushButton("Select...")
        self.fileDialogButton.clicked.connect(self.showDialog)
        self.layout.addWidget(self.fileDialogButton)

    def update(self,  parameter):
        if parameter!=None:
            self.updateValue(parameter.getValue())

    def updateValue(self,  value):
        if value!=None:
            self.text.setText(value)

    def showDialog(self):
        filename = None
        if self.type == "open":
            filename=QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', '',  self.fileSelectionPattern)
        if self.type == "save":
            filename=QtWidgets.QFileDialog.getSaveFileName(self, 'Save file', '',  self.fileSelectionPattern)

        print (filename)
        if filename!=None and len(filename[0])>0:
            self.updateValue(filename[0])

class LabeledNumberField(QWidget):
    def __init__(self, parent=None,  label="", min=None,  max=None,  value=0,  step=1.0,  slider=False):
        QWidget.__init__( self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.label=QtWidgets.QLabel(label)
        self.layout.addWidget(self.label)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        decimals = round(math.log(1.0 / step) / math.log(10))
        self.number = QtWidgets.QDoubleSpinBox(parent=self, decimals=decimals)
        if min != None:
            self.number.setMinimum(min)
        else:
            self.number.setMinimum(-10000000)
        if max!=None:
            self.number.setMaximum(max)
        else:
            self.number.setMaximum(10000000)
        self.number.setSingleStep(step);
        self.number.setValue(value)
        self.layout.addWidget(self.number)
        self.number.valueChanged.connect(self.spinboxChanged)
        if slider:
            self.sliderLayout = QtWidgets.QVBoxLayout()
            self.sliderLayout.setSpacing(0)
            self.sliderLayout.setContentsMargins(0, 0, 0, 0)
            self.sliderWidget = QtWidgets.QWidget()
            self.slider = QtWidgets.QSlider(orientation=QtCore.Qt.Horizontal)
            if min != None:
                self.slider.setMinimum(min)
            if max != None:
                self.slider.setMaximum(max)
            self.slider.setValue(value)
            self.slider.valueChanged.connect(self.sliderChanged)
            labelednumber_widget = QtWidgets.QWidget()
            labelednumber_widget.setLayout(self.layout)
            self.sliderLayout.addWidget(labelednumber_widget)
            self.sliderLayout.addWidget(self.slider)
            self.setLayout(self.sliderLayout)
            labelednumber_widget.setContentsMargins(0, 0, 0, 0)

        else:
            self.slider = None
            self.setLayout(self.layout)

    def sliderChanged(self):
        self.updateValue(self.slider.value())

    def spinboxChanged(self):
        if self.slider is not None:
            self.slider.setValue(self.number.value())

    def update(self, parameter):
        if parameter != None:
            self.updateValue(parameter.getValue())

    def updateValue(self,  value):
        self.number.setValue(value)
        if self.slider is not None:
            self.slider.setValue(value)


def parameterWidgetFactory(object, parent = None):
    w = None

    if object.__class__.__name__ == "TextParameter":
        w = LabeledTextField(parent=parent, label=object.name, editable=object.editable, formatString=object.formatString)

        w.updateValue(object.value)
        if object.editable:
            w.text.textChanged.connect(object.updateValueOnly)
            w.text.editingFinished.connect(object.commitValue)

    if object.__class__.__name__ == "FileParameter":
        w = LabeledFileField(parent=parent, label=object.name, editable=object.editable, type = object.type, fileSelectionPattern=object.fileSelectionPattern)
        w.updateValue(object.value)
        if object.editable:
            w.text.textChanged.connect(object.updateValue)

    if object.__class__.__name__ == "NumericalParameter":
        w = LabeledNumberField(parent=parent, label=object.name, min=object.min, max=object.max, value=object.getValue(), step=object.step)

        if object.editable:
            w.number.valueChanged.connect(object.updateValueOnly)

    if object.__class__.__name__ == "ProgressParameter":
        w = LabeledProgressField(parent=parent, label=object.name, min=object.min, max=object.max, value=object.getValue())

    if object.__class__.__name__ == "ChoiceParameter":
        w = LabeledComboField(parent=parent, label=object.name, value=object.getValueString(),
                              choices=object.getChoiceStrings())
        if object.editable:
            w.combo.currentIndexChanged.connect(
                object.updateValueByIndex)

    if object.__class__.__name__ == "ActionParameter":
        w = QtWidgets.QPushButton(object.name)
        w.clicked.connect(object.callback)
    object.viewRefresh = w.update
    return w

class ToolPropertyWidget(QWidget):
    def updateParameter(self,  object=None,  newValue=None):
        object.updateValue(newValue)


    def __init__(self, parent,  tool):
        QWidget.__init__( self, parent=parent)

        self.scroll = QtGui.QScrollArea(self)

        self.scroll.setWidgetResizable(True)
        self.outer_layout = QtGui.QVBoxLayout(self)
        self.outer_layout.addWidget(self.scroll)

        self.scroll.setVerticalScrollBarPolicy(Qt.Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.Qt.ScrollBarAsNeeded)

        self.scrollcontent=QtGui.QWidget(self.scroll)
        self.layout = QtGui.QVBoxLayout(self.scrollcontent)
        self.scrollcontent.setLayout(self.layout)
        self.scroll.setWidget(self.scrollcontent)


        self.parameters=dict()
        self.addToolWidgets(self.layout,  tool.parameters)
        self.layout.addStretch()



    def addToolWidgets(self,  layout,  widgetlist):

        # get editable parameters
        for object in widgetlist:
            p=object

            w = None
            if isinstance(object, (list)):
                horizontal_widget = QWidget()
                horizontal_layout = QtWidgets.QHBoxLayout()
                horizontal_widget.setLayout(horizontal_layout)
                self.addToolWidgets(horizontal_layout, object)
                layout.addWidget(horizontal_widget)
            else:
                w = parameterWidgetFactory(object, parent = self)
                self.parameters[p] = w
                layout.addWidget(w)
                object.viewRefresh = self.update

            if w is not None:
                self.parameters[p] = w

        #layout.setMargin(0);
        layout.setSpacing(0);
        #layout.addStretch()

    def update(self, parameter=None):
        # get editable parameters
        for object in self.parameters.keys():
            w=self.parameters[object]

            w.setDisabled(not object.active)
            if object.__class__.__name__=="TextParameter":
                w.updateValue(object.value)

            if object.__class__.__name__=="FileParameter":
                w.updateValue(object.value)

            if object.__class__.__name__=="ProgressParameter":
                w.updateValue(value=object.value,  min=object.min,  max=object.max)

            if object.__class__.__name__=="NumericalParameter":
                w.updateValue(object.value)

            if object.__class__.__name__=="ChoiceParameter":
                w.updateChoices(object.getChoiceStrings())
                w.updateValue(object.getValueString())

            if object.__class__.__name__=="ActionParameter":
                None

class ItemListModel(QtCore.QAbstractListModel):
    def __init__(self, itemlist, parent=None, *args):

        QtCore.QAbstractListModel.__init__(self, parent, *args)
        self.listdata = itemlist

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.listdata)

    def data(self, index, role):
        if not (index.isValid()  and index.row()<len(self.listdata)):
            return None
        if self.listdata[index.row()] is None:
            return QtCore.QVariant()
        if role == QtCore.Qt.DisplayRole:
            return self.listdata[index.row()].name.value
        if role == QtCore.Qt.CheckStateRole:
            if len(self.listdata)>0 and self.listdata[index.row()].selected:
                return QtCore.Qt.Checked
            else:
                return QtCore.Qt.Unchecked
        return QtCore.QVariant()

    def isChecked(self,  index):
        if len(self.listdata)>0 and self.listdata[index].selected:
            return True
        else:
            return False

    def setData(self, index, value, role):
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                eindex=-1
                for i in range(0,  len(self.listdata)):
                    if self.listdata[i] is not None and self.listdata[i].name.value==str(value):
                        eindex=i
                if eindex>=0:
                    self.listdata[index.row()] = self.listdata[eindex]
            if role == QtCore.Qt.CheckStateRole:
                if index.row()<len(self.listdata):
                    self.listdata[index.row()].selected=(not self.listdata[index.row()].selected)
                    self.dataChanged.emit(index, index)
                    return True
        return False

    def addItem(self,  newItem):
        self.beginInsertRows(QtCore.QModelIndex(),  self.rowCount(),
                             self.rowCount()+1)
        self.listdata.append(newItem)
        self.endInsertRows()
        return self.index(self.rowCount()-1)


    def removeRows(self,  row,  count,  parent):
        self.beginRemoveRows(QtCore.QModelIndex(),  self.rowCount(),  self.rowCount()+1)
        for i in reversed(range(row,  row+count)):
            if i<len(self.listdata):
                del self.listdata[i]
        self.endRemoveRows()
        return True

    def insertRows(self, row, count, parent=QtCore.QModelIndex()):
        if parent.isValid(): return False

        beginRow=max(0,row)
        endRow=min(row+count-1,len(self.listdata))

        self.beginInsertRows(parent, beginRow, endRow)

        for i in xrange(beginRow, endRow+1): self.listdata.insert(i,None)

        self.endInsertRows()
        return True

    def flags(self, index):
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | \
               QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsDragEnabled

        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled | \
               QtCore.Qt.ItemIsDropEnabled | QtCore.Qt.ItemIsEnabled

    def supportedDragActions(self):
        return QtCore.Qt.MoveAction

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

class ListWidget(QWidget):
    def __init__(self, parent=None,  title="",  itemlist=[],  itemclass=None,  on_select_cb=None, addItems=True,  removeItems=True,   **creationArgs):
        QWidget.__init__( self, parent=parent)
        self.creationArgs=creationArgs
        self.on_select_cb=on_select_cb
        ## Create a grid layout to manage the widgets size and position
        self.layout = QtWidgets.QGridLayout()
        self.setLayout(self.layout)
        self.listmodel=ItemListModel(itemlist)
        self.itemclass=itemclass
        self.listw = QtWidgets.QListView()
        self.listw.setModel(self.listmodel)
        self.listw.setDragDropMode(self.listw.InternalMove)
        self.listw.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.listw.setDragDropOverwriteMode(False)
        self.listw.setDragEnabled(True);
        self.listw.setAcceptDrops(True);
        self.listw.setDropIndicatorShown(True);
        self.listw.clicked.connect(self.respondToSelect)
        self.layout.addWidget(QtWidgets.QLabel(title), 0, 0)   # button goes in upper-left
        self.layout.addWidget(self.listw, 1, 0)  # list widget goes in bottom-left
        self.propertyWidget = None

        if addItems or removeItems:
            buttonwidget=QWidget()
            buttonLayout=QtWidgets.QHBoxLayout()
            buttonwidget.setLayout(buttonLayout)

            if addItems:
                if isinstance(itemclass,  dict):
                    self.widgetSelect = PlainComboField(parent=self,  value = list(itemclass.keys())[0],
                                                                                   label='Widgets',  choices=itemclass.keys())
                    buttonLayout.addWidget(self.widgetSelect)
                self.addBtn = QtWidgets.QPushButton('+')
                self.addBtn.setFixedWidth(30)
                buttonLayout.addWidget(self.addBtn)
                self.addBtn.clicked.connect(self.addItem)
            if removeItems:
                self.removeBtn = QtWidgets.QPushButton('-')
                self.removeBtn.setFixedWidth(30)
                buttonLayout.addWidget(self.removeBtn)
                self.removeBtn.clicked.connect(self.removeItem)

            self.layout.addWidget(buttonwidget, 2, 0)   # button goes in upper-left


        if len(itemlist)>0:
            self.selectedTool=itemlist[0]
        else:
            self.selectedTool=None

        if self.selectedTool!=None:
            self.propertyWidget=ToolPropertyWidget(parent=self, tool=self.selectedTool)
            self.layout.addWidget(self.propertyWidget, 0, 1,  3,  1)

    def respondToSelect(self,  index):
        s_index=self.listw.currentIndex()
        self.selectedTool=self.listmodel.listdata[s_index.row()]
        if self.selectedTool!=None:
            if self.propertyWidget is not None:
                self.layout.removeWidget(self.propertyWidget)
                self.propertyWidget.close()
            self.propertyWidget=ToolPropertyWidget(parent=self, tool=self.selectedTool)
            self.layout.addWidget(self.propertyWidget, 0, 1,  3,  1)
            if self.on_select_cb!=None:
                self.on_select_cb(self.selectedTool)

    def getCheckedItems(self):
        checkedItems = []
        for index in range(self.listw.model().rowCount()):
            if self.listw.model().isChecked(index):
                checkedItems.append(self.listmodel.listdata[index])
        return checkedItems

    def getItems(self):
        return [i for i in self.listmodel.listdata]


    def addItem(self,  dummy=None, addExistingItems=True,  **creationArgs):
        if isinstance(self.itemclass,  dict):
            index = self.widgetSelect.currentIndex()
            itemToCreate = list(self.itemclass.values())[index]
        else:
            itemToCreate = self.itemclass

        print("reloading module ", itemToCreate.__module__)
        reload(sys.modules[itemToCreate.__module__])
        itemToCreate = getattr(sys.modules[itemToCreate.__module__], itemToCreate.__name__)

        try:
            if len(creationArgs)==0:
                newItem=itemToCreate(**self.creationArgs)
            else:
                newItem=itemToCreate(**creationArgs)

            newName=newItem.name.value
            nameExists=False
            foundItem=None
            for item in self.listmodel.listdata:
                if item is not None and item.name.value==newName:
                    nameExists=True
                    foundItem=item
                    print ("found" , newName, addExistingItems)
                    break

            if not nameExists or (nameExists and addExistingItems):
                counter=1
                while newName in [i.name.value for i in self.listmodel.listdata]:
                    newName="%s - %i"%(newItem.name.value,  counter)
                    counter+=1
                newItem.name.updateValue(newName)
                # add to list model
                addedItem=self.listmodel.addItem(newItem)
                self.listw.setCurrentIndex(addedItem)
                self.respondToSelect(addedItem)
                print (newName)
                return newItem
            else:
                return foundItem
        except Exception as e:
            print(e)
            traceback.print_exc()
        return None

    def findItem(self,  name):
        for item in self.listmodel.listdata:
            if name==item.name.value:
                return item
        return None

    def removeItem(self):
        if self.propertyWidget is not None:
            self.layout.removeWidget(self.propertyWidget)
            self.propertyWidget.close()

        itemindex=self.listw.selectedIndexes()
        if len(itemindex)==0:
            return
        self.listmodel.removeRows(itemindex[0].row(),  1,  itemindex[0])


