from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.Qsci import *
import gcode

class QsciGcodeLexer(QsciLexerCPP):

    def keywords(self, index):
        keywords = QsciLexerCPP.keywords(self, index) or ''
        # primary keywords
        if index == 1:
            return 'G' + 'M' + "F"
        # secondary keywords
        if index == 2:
            return "X"+"Y"+"Z"+"I"+"J"
        # doc comment keywords
        if index == 3:
            return keywords
        # global classes
        if index == 4:
            return keywords
        return keywords

class GcodeEditorWidget(QWidget):
    def __init__(self, object_viewer=None):
        QWidget.__init__(self)
        self.lexers={"ngc":QsciGcodeLexer()}
        self.suffixToLexer={"ngc":"ngc"}

        self.object_viewer = object_viewer

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.label = QLabel()
        self.editor = QsciScintilla()
        self.configureEditor(self.editor)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.editor)

        self.editor.selectionChanged.connect(self.onSelectionChanged)
        self.editor.textChanged.connect(self.onTextChanged)
        self.pathTool = None
        self.editingFlag = False

    def setObjectViewer(self, object_viewer):
        self.object_viewer = object_viewer

    def setPathTool(self, path):
        self.pathTool = path

    def onSelectionChanged(self):
        selection = self.editor.getSelection()
        if self.object_viewer is not None:
            self.object_viewer.setSelection(selection[0], selection[2])

    def onTextChanged(self):
        self.editingFlag=True
        if self.pathTool is not None:
            print ("..")
            self.pathTool.updatePath( gcode.parse_gcode(self.getText()))
        self.editingFlag=False

    def configureEditor(self, editor):
        self.__lexer = self.lexers["ngc"]
        editor.setLexer(self.__lexer)
        editor.setMarginType(1, QsciScintilla.TextMargin)
        editor.setMarginType(0, QsciScintilla.SymbolMargin)
        editor.setMarginMarkerMask(1, 0b1111)
        editor.setMarginMarkerMask(0, 0b1111)
        editor.setMarginsForegroundColor(QColor("#ffFF8888"))
        editor.setUtf8(True)  # Set encoding to UTF-8
        #editor.indicatorDefine(QsciScintilla.FullBoxIndicator, 0)
        editor.indicatorDefine(QsciScintilla.BoxIndicator, 0)
        editor.setAnnotationDisplay(QsciScintilla.AnnotationStandard)

    def highlightLine(self, line_number, refresh = False):
        if self.editingFlag: # don't update text if a path tool is set, and we're in editing mode
            return
        marginTextStyle = QsciStyle()
        marginTextStyle.setPaper(QColor("#ffFF8888"))
        self.editor.blockSignals(True)
        self.editor.setCursorPosition(line_number, 0)
        self.editor.setSelection(line_number, 0, line_number+1, 0)
        self.editor.blockSignals(False)
        if refresh and self.object_viewer is not None:
            self.object_viewer.setSelection(0, line_number)

    def getText(self):
        return [l for l in self.editor.text().splitlines()]

    def updateText(self, text,  label="", fileSuffix="ngc"):
        if self.editingFlag: # don't update text if user is currently editing, to avoid propagation loops
            return
        # turn off signals to prevent event loops
        self.editor.blockSignals(True)
        if fileSuffix in self.suffixToLexer.keys():
            self.__lexer = self.lexers[self.suffixToLexer[fileSuffix]]
            self.editor.setLexer(self.__lexer)
            #label+="     ("+self.suffixToLexer[fileSuffix]+")"
        marginTextStyle= QsciStyle()
        marginTextStyle.setPaper(QColor("#ffFF8888"))
        self.editor.setText("")
        self.label.setText(label)
        skipped_lines = 0
        annotation=None
        for linenumber, l in enumerate(text):
            idx=linenumber-skipped_lines
            if l is None:
                #editor.append("\n")
                if annotation is None:
                    annotation="<"
                else:
                    annotation+="\n<"
                skipped_lines+=1
                self.editor.setMarginText(idx, "~", marginTextStyle)
            else:
                if annotation is not None:
                    self.editor.annotate(idx-1, annotation, 0)
                    annotation=None
                if '\0' in l or '\1' in l:
                    self.editor.append(l.replace('\0+', '').replace('\0-', '').replace('\m', '').replace('\0^', '').replace('\1', ''))
                    self.editor.markerAdd(idx, QsciScintilla.Circle)
                    self.editor.setMarginText(idx, l[1], marginTextStyle)
                    self.editor.fillIndicatorRange(idx, l.find('\0'), idx, l.rfind("\1"), 0)
                else:
                    self.editor.append(l)

        self.editor.blockSignals(False)
