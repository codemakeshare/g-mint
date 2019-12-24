def findBrackets( aString, startBracket="<", endBracket=">" ):
   if startBracket in aString:
      match = aString.split(startBracket,1)[1]
      open = 1
      for index in xrange(len(match)):
        if match[index:index + len(endBracket)] == endBracket:
            open = open - 1
        elif match[index:index+len(startBracket)] == startBracket:
            open = open + 1
        if open==0:
            #return found string and rest string
            return match[:index], match[index+len(endBracket):]


def findBlock( aString, description="" ):
    signature = "<"+description+">"
    startBracket="<"
    endBracket="</>"
    if signature in aString:
        match = aString.split(signature,1)[1]
        open = 1
        for index in xrange(len(match)):
            if match[index:index + len(endBracket)] == endBracket:
                open = open - 1
            elif match[index:index+len(startBracket)] == startBracket:
                open = open + 1
            if open==0:
                return match[:index]

def getNextBlock( aString):
    startBracket="<"
    endBracket="</>"
    block, rest = findBrackets(aString, startBracket="<", endBracket="</>")
    block="<"+block
    description, contents = findBrackets(block, startBracket="<", endBracket=">")

    return description, contents

class ItemWithParameters:
    def __init__(self, name="-",  parameters=[]):
        self.name=TextParameter(parent=self, name="Name", value=name)
        self.selected=False
        self.parameters=parameters

    def getName(self):
        return self.name

    def serialize(self):
        output='<Item class="%s" name="%s">\n'%(self.__class__.__name__, self.name.getValue())
        for p in self.parameters:
            output+=p.serialize()+"\n"
        output+="</>"
        return output

    def deserialize(self, setstring):
        checkedString=findBlock(setstring, description='Item class="%s" name="%s"'%(self.__class__.__name__, self.name.getValue()))
        if checkedString is not None:
            for p in self.parameters:
                p.deserialize(checkedString)
        else:
            print("invalid setstring")

class EditableParameter:

    def __init__(self,  parent=None,  name="",  editable=True,   callback=None,  viewRefresh=None,  active=True):
        self.name=name
        self.parent=parent
        self.value=None
        self.selected=False
        self.editable=editable
        self.callback=callback
        self.viewRefresh = viewRefresh
        self.active=active

    def updateValueOnly(self,  value):
        #print "new value",  value
        self.value=value
        if self.callback!=None:
            self.callback(self)

    def updateValue(self,  value):
        #print "new value",  value
        self.value=value
        if self.callback!=None:
            self.callback(self)

    def commitValue(self):
        if self.callback != None:
            self.callback(self)

        if self.viewRefresh!=None:
            self.viewRefresh(self)

    def updateValueByString(self,  value):
        self.updateValue(value)

    def setActive(self,  active):
        self.active=active
        if self.viewRefresh!=None:
            self.viewRefresh(self)

    def getValue(self):
        return self.value

    def serialize(self):
        return '<param name="%s">%s</>'%(self.name, str(self.getValue()))

    def deserialize(self, setstring):
        valueString = findBrackets(setstring, startBracket='<param name="%s">'%self.name, endBracket="</>")
        print("updating ", self.name, "with", valueString)
        self.updateValueByString(valueString)


class TextParameter(EditableParameter):
    def __init__(self,  value="", formatString="{:s}",     **kwargs):
        self.formatString=formatString
        EditableParameter.__init__(self,  **kwargs)
        self.value=value


class FileParameter(EditableParameter):
    def __init__(self,  value="",  fileSelectionPattern="All files (*.*)",     **kwargs):
        EditableParameter.__init__(self,  **kwargs)
        self.value=value
        self.fileSelectionPattern=fileSelectionPattern


class NumericalParameter(EditableParameter):
    def __init__(self,  value=0,  min=None,  max=None,  step=0,  enforceRange=False,  enforceStep=False,  **kwargs):
        EditableParameter.__init__(self,  **kwargs)
        self.value=value
        self.min=min
        self.max=max
        self.step=step
        self.enforceRange=enforceRange
        self.enforceStep=enforceStep

    def updateValueByString(self,  value):
        self.updateValue(float(value))

    def updateValueQT(self,  value):
        #print "new value",  value
        self.value=value
        if self.enforceRange:
            self.value=min(max,  max(min,  self.value))
        if self.enforceStep:
            self.value=float(int(self.value/self.step)*self.step)
        if self.callback!=None:
            self.callback(self)

    def updateValue(self,  value):
        #print "new value",  value
        self.value=value
        if self.enforceRange:
            self.value=min(self.max,  max(self.min,  self.value))
        if self.enforceStep:
            self.value=float(int(self.value/self.step)*self.step)
        if self.callback!=None:
            self.callback(self)
        if self.viewRefresh!=None:
            self.viewRefresh(self)

class ProgressParameter(EditableParameter):
    def __init__(self,  value=0,  min=None,  max=None,  step=0,  **kwargs):
        EditableParameter.__init__(self,  **kwargs)
        self.value=value
        self.min=min
        self.max=max
        self.step=step

    def updateValue(self,  value,  min,  max):
        #print "new value",  value
        self.value=value
        self.min=min
        self.max=max

    def updateValueByString(self,  value):
        self.updateValue(float(value))

class Choice:
    def __init__(self, name="", value=None):
        self.name=name
        self. value=value

class ChoiceParameter(EditableParameter):
    def __init__(self,  value=None, choices=None, **kwargs):
        EditableParameter.__init__(self, **kwargs)
        self.value = value
        self.choices = choices

    def getChoiceStrings(self):
        cs = []
        for c in self.choices:
            if "name" in dir(c) and "value" in dir(c.name):
                cs.append(c.name.value)
            elif "name" in dir(c) and "value" in dir(c):
                cs.append(c.name)
            elif c.__class__.__name__ == "str":
                cs.append(c)
            else:
                cs.append(str(c))
        return cs

    def getValueString(self):
        c = self.value
        if "name" in dir(c) and "value" in dir(c.name):
            return c.name.value
        elif "name" in dir(c) and "value" in dir(c):
            return str(c.name)
        elif c.__class__.__name__ == "str":
            return c
        else:
            return str(c)

    def getValue(self):
        c = self.value
        if "name" in dir(c) and "value" in dir(c):
            return c.value
        else:
            return c


    def getIndexByValue(self, value):
        for i in range(0, len(self.choices)):
            c = self.choices[i]
            if "name" in dir(c) and "value" in dir(c):
                if c.value == value:
                    return i
            else:
                if c == value:
                    return i
        return -1

    def updateValue(self,  value):
        #print(self.name, value)
        for c in self.choices:
            if "name" in dir(c) and "value" in dir(c):
                if c.value == value:
                    self.value = c
                    break
            else:
                if c == value:
                    self.value = c
                    #print("set ", self.name, "to", self.value)
                    break
        if self.callback != None:
            self.callback(self)
        if self.viewRefresh != None:
            self.viewRefresh(self)

    def updateValueByString(self,  value):
        #print "update value by string:", value
        strings = self.getChoiceStrings()
        for i in range(0, len(self.choices)):
            s = strings[i]
            if s == value:
                print(i,  s)
                self.value = self.choices[i]
        if self.callback != None:
            self.callback(self)

        if self.viewRefresh != None:
            self.viewRefresh()
        #print(self.value)

    def updateValueByIndex(self, index):
        self.value = self.choices[index]

        if self.callback != None:
            self.callback(self)

        if self.viewRefresh != None:
            self.viewRefresh()
        #print(self.value)


class ActionParameter(EditableParameter):
    def __init__(self,   **kwargs):
        EditableParameter.__init__(self, **kwargs)

