# # @package CMtools
#    Tools for CM testing.
#    \file PDDBData.py

import sys, string, time, math, os

# SAX
from xml.sax import handler, make_parser, saxutils
from xml.sax.handler import feature_namespaces
from xml.sax._exceptions import SAXParseException

import Parameter
import XML_utils
from Definitions import *


# # Reads and stores parameter definitions from PDDB report
#
# This class uses SAX parsing to read the PDDB report and stores all the necessary data. Parameter information
# can then be retrieved using the get methods.
class PDDBData(handler.ContentHandler):


    # # \brief The constructor.
    #
    #    \param self object reference
    #    \return -
    def __init__(self):
        self.__paramNameDictionary = {}    # dictionary to store parameter names of every managed object
        self.__paramDataDictionary = {}    # dictionary to store parameter data of every parameter
        self.__childObjectDictionary = {}    # dictionary containing list of children of every managed objects (if any)
        self.__managedObjectList = []    # list of all RNW objects
        self.__currentObject = None    # current object SAX is processing (e.g. WBTS)
        self.__currentChildObjectList = []    # list of child objects of current object
        self.__currentParamLevel = -1    # 'deepness' of structure, there may be several parameters inside of one
        self.__currentChildDictionary = {}    # dictionary of child parameters in all levels
        self.__currentParamStackList = []    # upper level parameters of struct
        self.__skipParam = False    # ignore all elements if parameter is deleted or excluded
        self.__skipLevel = -1    # keep track when to stop skipping (this is needed, because parameter can be a struct)

        self.__paramsChecked = 0
        self.__validateProblems = 0

    #
    # Public methods
    #


    # # \brief SAX element start handling.
    #
    #    \param self object reference
    #    \param name name of the element
    #    \param attrs attributes of the element
    #    \return -
    def startElement(self, name, attrs):
        if name == 'managedObject':
            object = attrs.get('class', None)
            self.__managedObjectList.append(object)
            self.__currentObject = object
            self.__currentChildObjectList = []    # new object, reset child object list
            self.__paramNameDictionary[self.__currentObject] = []    # no params yet
        if name == 'childManagedObject':
            child = attrs.get('class', None)
            self.__currentChildObjectList.append(child)
        if name == 'p':
            self.__currentParamLevel += 1
            name = attrs.get('name', None)
            fullName = attrs.get('fullName', None)
            maxOccurs = attrs.get('maxOccurs', None)
            status = attrs.get('status', None)
            hidden = attrs.get('hidden', None)
            # skip parameter, if status is 'deleted' or
            # it is excluded (e.g. change origins)
            if status == 'deleted' or hidden == 'true':
                if self.__skipParam == False:
                    self.__skipParam = True
                    self.__skipLevel = self.__currentParamLevel
            # ignore inner elements too
            if self.__skipParam:
                return
            paramInstance = Parameter.Parameter()    # instantiate Parameter object to store the data
            paramInstance.setName(name)
            paramInstance.setFullName(fullName)
            paramInstance.setMaxOccurs(maxOccurs)
            paramInstance.setStatus(status)
            paramInstance.setManagedObject(self.__currentObject)
            # initialize children list to empty
            self.__currentChildDictionary[self.__currentParamLevel] = []
            # e.g. child parameters are missing, but can't know if there are any yet
            if self.__currentParamLevel > 0:
                self.__currentChildDictionary[self.__currentParamLevel - 1].append(name)
            self.__currentParamStackList.append(name)
            # RAML2.1: no nested lists anymore
            if len(self.__currentParamStackList) > 2:
                print ERROR_MSG
                print "multi-level parameter structure definition in PDDB, not allowed in RAML2.1!"
                print "managedObject:", self.__currentObject
                print "param stack:", self.__currentParamStackList
                sys.exit(1)            
            parentParam = self.__getParenParam()
            paramInstance.setParentParam(parentParam)
            self.__storeParamInstance(paramInstance, name)            
        # no need to check parameter value fields
        if self.__skipParam:
            return
        if name == 'creation':
            creationPriority = attrs.get('priority', None)
            paramInstance = self.__getParamInstance()
            paramInstance.setCreationPriority(creationPriority)    # reference, so object in dictionary is updated
        if name == 'modification':
            modificationType = attrs.get('type', None)
            paramInstance = self.__getParamInstance()
            paramInstance.setModificationType(modificationType)
        if name == 'feature':
            features = attrs.get('name', None)
            feaType = attrs.get('type', None)
            # PDDB definitions not very consistent
            if feaType == 'standard' and features.find('optional') != -1:
                feaType = 'optional'
                # print "fix feaType:", features, feaType
            # ignore standard features
            # print "features:", features, "-", feaType
            if features != None and feaType.find('standard') == -1:
                paramInstance = self.__getParamInstance()
                paramInstance.setFeatures(features)
        # one-way parameters should not be present in download plan
        if name == 'interface':
            source = attrs.get('source', None)
            target = attrs.get('target', None)
            bidirection = attrs.get('bidirectional', None)
            paramInstance = self.__getParamInstance()
            paramInstance.setInterface()
            if (source == 'RAC' and target == 'RNC') or (source == 'RNC' and target == 'RAC') or \
                 (source == 'RAC' and target == 'IADA') or (source == 'IADA' and target == 'RAC'):
                if bidirection == 'no':
                    paramInstance.setPlanDirection('uni')    # unidirectional
                    if (source == 'RAC' and target == 'RNC') or (source == 'RAC' and target == 'IADA') :
                        paramInstance.setInterfaceDirection('uni-down')
                    else:
                        paramInstance.setInterfaceDirection('uni-up')
                else:
                    paramInstance.setPlanDirection('bi')    # birectional
                    paramInstance.setInterfaceDirection('bi')
            if (source == 'EM' and target == 'RNC') or (source == 'RNC' and target == 'EM'):
                if bidirection == 'no':
                    paramInstance.setGuiDirection('uni')    # unidirectional
                else:
                    paramInstance.setGuiDirection('bi')    # birectional
        if name == 'property':
            location = attrs.get('name', None)
            if location == 'Location in GUI':
                value = attrs.get('value', None)
                paramInstance = self.__getParamInstance()
                paramInstance.setLocationInGui(value)
        if name == 'simpleType':
            valueBase = attrs.get('base', None)
            paramInstance = self.__getParamInstance()
            paramInstance.setParamType(name)
            paramInstance.setValueBase(valueBase)
        if name == 'complexType':
            paramInstance = self.__getParamInstance()
            paramInstance.setParamType(name)
        if name == 'editing':
            for attrName in attrs.keys():
                if attrName == 'divisor':
                    paramInstance = self.__getParamInstance()
                    paramInstance.setDivisor(attrs.get(attrName))
                if attrName == 'shift':
                    paramInstance = self.__getParamInstance()
                    paramInstance.setShift(attrs.get(attrName))
                if attrName == 'multiplicand':
                    paramInstance = self.__getParamInstance()
                    paramInstance.setMultiplicand(attrs.get(attrName))
                if attrName == 'internalValue':
                    paramInstance = self.__getParamInstance()
                    paramInstance.setInternalValue(attrs.get(attrName))
        if name == 'range':
            for attrName in attrs.keys():
                if attrName == 'minIncl':
                    paramInstance = self.__getParamInstance()
                    paramInstance.setMinValue(attrs.get(attrName))
                if attrName == 'maxIncl':
                    paramInstance = self.__getParamInstance()
                    paramInstance.setMaxValue(attrs.get(attrName))
                if attrName == 'step':
                    paramInstance = self.__getParamInstance()
                    paramInstance.setStep(attrs.get(attrName))
        if name == 'enumeration':
            enum = attrs.get('value', None)
            text = attrs.get('text', "")
            paramInstance = self.__getParamInstance()
            paramInstance.addEnumerationValue(enum)
            paramInstance.addEnumerationText(enum, text)
        if name == 'bit':
            default = attrs.get('default', None)
            fixed = attrs.get('fixed', False)
            paramInstance = self.__getParamInstance()
            paramInstance.addBitValue(default, fixed)
        if name == 'default':    # default value inside'bit' element
            defaultValue = attrs.get('value', None)
            paramInstance = self.__getParamInstance()
            paramInstance.setDefaultValue(defaultValue)
        if name == 'special':
            special = attrs.get('value', None)
            paramInstance = self.__getParamInstance()
            paramInstance.setSpecialValue(special)
        if name == 'minLength':
            min = attrs.get('value', None)
            paramInstance = self.__getParamInstance()
            paramInstance.setMinValue(min)
        if name == 'maxLength':
            max = attrs.get('value', None)
            paramInstance = self.__getParamInstance()
            paramInstance.setMaxValue(max)


    # # \brief SAX element end handling.
    #
    #    \param self object reference
    #    \param name name of the element
    #    \return -
    def endElement(self, name):
        if name == 'p':
            # skipping parameters and param level is back to were this was started - continue processing new parameters
            if self.__skipParam:
                if self.__skipLevel == self.__currentParamLevel:
                    # return to 'normal' mode
                    self.__skipParam = False
                self.__currentParamLevel -= 1
                return
            paramInstance = self.__getParamInstance()
            if paramInstance == None:
                return
            
            # parentParam = self.__getParenParam()
            # paramInstance.setParentParam(parentParam)
            
            # child parameters
            if paramInstance.getParamType() == 'complexType':
                childParams = self.__getChildParams()
                paramInstance.setChildParams(childParams)
                self.__currentChildDictionary[self.__currentParamLevel] = []
            # check that certain mandatory fields are correctly defined in the PDDB
            result = paramInstance.validate()
            if result == False:
                self.__validateProblems += 1
            self.__paramsChecked += 1
            # done with this param
            self.__currentParamStackList.pop(self.__currentParamLevel)
            self.__currentParamLevel -= 1
        if name == 'managedObject':
            self.__childObjectDictionary[self.__currentObject] = self.__currentChildObjectList
            self.__currentChildObjectList = []


    # # \brief Get number of PDDB parameter definitions checked for correctness.
    #
    #    \param self object reference
    #    \return -
    def getParamsChecked(self):
        return self.__paramsChecked


    # # \brief Get number of PDDB parameter definition problems found.
    #
    #    \param self object reference
    #    \return -
    def getProblemCount(self):
        return self.__validateProblems


    # # \brief Get all parameters of an object.
    #
    #    \param self object reference
    #    \param managedObject name of the RNW object (e.g. 'WCEL')
    #    \return list containing names (as string) of all parameters of this object
    def getParamList(self, managedObject):
        if managedObject in self.__paramNameDictionary:
            return self.__paramNameDictionary[managedObject]
        return None


    # # \brief Get stored data of a single PDDB parameter.
    #
    #    \param self object reference
    #    \param managedObject name of the RNW object (e.g. 'COCO')
    #    \param parameter name of the RNW parameter (e.g. 'VCI')
    #    \param parentParam name of the parent of this RNW parameter
    #    \return instance of Parameter class or None
    def getParamObject(self, managedObject, parameter, parentParam=None):
        # print "dict:", self.__paramDataDictionary
        if parentParam != None:    # parameter is inside a structure or list
            parentParam = parentParam.strip()
            if parentParam == '':
                print "abort, empty parentParam: %s-%s" % (managedObject, parameter)
                sys.exit()
            if managedObject + parentParam + parameter in self.__paramDataDictionary:
                return self.__paramDataDictionary[managedObject + parentParam + parameter]
        else:
            if managedObject + parameter in self.__paramDataDictionary:
                return self.__paramDataDictionary[managedObject + parameter]
        return None


    # # \brief Get name of the parent RNW object.
    #
    #    \param self object reference
    #    \param managedObject name of the RNW object (e.g. 'WCEL')
    #    \return name of the object as a string (e.g. 'WBTS') or None
    def getParentObject(self, managedObject):
        for mo in self.__managedObjectList:
            if managedObject in self.__childObjectDictionary[mo]:
                return mo
        return None


    # # \brief Get list of all RNW objects.
    #
    #    \param self object reference
    #    \return list of all defined RNW objects
    def getManagedObjectList(self):
        return self.__managedObjectList


    # # \brief Get list of all RNW objects.
    #
    #    \param self object reference
    #    \param managedObject name of the RNW object
    #    \return list of expected parameter names or None
    def getAllExpectedParameters(self, managedObject):
        expectedParams = []
        params = self.getParamList(managedObject)        
        if params == None:
            return None
        for param, parentParam in params:        
            paramObject = self.getParamObject(managedObject, param, parentParam)
            if paramObject == None:
                print "Parameter not found: %s-%s!" % (managedObject, param)
                sys.exit(1)
            if paramObject.getParamPlanDirection() != None and paramObject.getParamOptionStatus():
                # skip all object ID parameters and AutomObjLock
                if paramObject.isIdParameter() == False and paramObject.getName() != 'AutomObjLock':
                    expectedParams.append(param)
        return expectedParams

    def getExpectedParametersWithInterfaceDirection(self, managedObject, interfaceDirection="uni-down"):
        expectedParams = []
        params = self.getParamList(managedObject)        
        if params == None:
            return None
        for param, parentParam in params:        
            #skipt all child Params
            if parentParam != None:
                continue
            paramObject = self.getParamObject(managedObject, param, parentParam)
            if paramObject == None:
                print "Parameter not found: %s-%s!" % (managedObject, param)
                sys.exit(1)
            paramInterfaceDirection = paramObject.getParamInterfaceDirection()
            featureStatus = paramObject.getParamOptionStatus()
            paramFeatureAsBool = paramObject.getFeatureAsBool()
            paramFeatureAsText = paramObject.getFeatureAsText()
            if featureStatus == True:
                if (paramInterfaceDirection == interfaceDirection) or (paramInterfaceDirection == "bi"):
                    # skip all object ID parameters and AutomObjLock
                    if paramObject.isIdParameter() == False and paramObject.getName() != 'AutomObjLock':
                        expectedParams.append(param)
            else:
                print "Feature not enabled for %s param %s:"% (interfaceDirection, param)
                print "Feature Names: %s"% paramFeatureAsText
                print "Feature status: %s"% paramFeatureAsBool
        return expectedParams

    # # \brief Get parent parameter name of paranmeter node.
    #
    #    \param self object reference
    #    \param paramNode parameter as a DOM node
    #    \return name of the parent parameter or None
    def getParentParameter(self, paramNode):    
        if paramNode.parentNode.nodeName == 'item':
            return paramNode.parentNode.parentNode.getAttribute('name')
        return None


    # # \brief Set currently enabled options for every parameter.
    #
    #    \param self object reference
    #    \param enabledOptions list of enabled option names
    #    \param isAda is NE ADA or not
    #    \return none
    def setOptions(self, enabledOptions, isAda):
        if isAda == False:
            paramObject = self.getParamObject('RNC', 'RncOptions')
            allOptions = paramObject.getEnumerationTextValues()
            disabledOptions = list(set(allOptions).difference(set(enabledOptions)))
        for managedObject in self.getManagedObjectList():
            for param, parentParam in self.getParamList(managedObject):
                paramObject = self.getParamObject(managedObject, param, parentParam)
                # ADA has always all licenses enabled
                if isAda:
                    paramObject.setUsedOptions([], [], "True")
                # cRNC or mcRNC: set features based on license status in upload plan
                elif parentParam == None:    # basic parameter (not inside a list)
                    paramObject.setUsedOptions(enabledOptions, disabledOptions)
                else:
                    parentParamObject = self.getParamObject(managedObject, parentParam)
                    # if list parent parameter has more features, they apply to all children
                    if len(parentParamObject.getFeatures()) > 0 and len(paramObject.getFeatures()) == 0:
                        if parentParamObject.getParamOptionStatus():
                            paramObject.setUsedOptions(enabledOptions, disabledOptions, "True")
                        else:
                            paramObject.setUsedOptions(enabledOptions, disabledOptions, "False")
                    else:
                        # otherwise parameter inside a list may have different related features then list parent
                        paramObject.setUsedOptions(enabledOptions, disabledOptions)


    #
    # Private methods
    #


    # # \brief Store data of a single PDDB parameter.
    #
    #    \param self object reference
    #    \paramInstance instance of Parameter class
    #    \paramName parameter name
    #    \return -
    def __storeParamInstance(self, paramInstance, paramName):
        parentParam = paramInstance.getParentParam()
        if parentParam == None:
            self.__paramDataDictionary[self.__currentObject + paramName] = paramInstance
            self.__paramNameDictionary[self.__currentObject].append((paramName, None))
        else:
            self.__paramDataDictionary[self.__currentObject + parentParam + paramName] = paramInstance
            self.__paramNameDictionary[self.__currentObject].append((paramName, parentParam))
        


    # # \brief Get data of a single PDDB parameter.
    #
    #    \param self object reference
    #    \return instance of Parameter class or None
    def __getParamInstance(self):
        if len(self.__currentParamStackList) > self.__currentParamLevel and self.__currentParamLevel >= 0:
            paramName = self.__currentParamStackList[self.__currentParamLevel]
            if self.__currentParamLevel == 0:
                return self.__paramDataDictionary[self.__currentObject + paramName]
            else:
                parentParam = self.__currentParamStackList[self.__currentParamLevel - 1]
                return self.__paramDataDictionary[self.__currentObject + parentParam + paramName]
        else:
            return None


    # # \brief Get child parameters of the parameter.
    #
    #    \param self object reference
    #    \return list of child parameter names
    def __getChildParams(self):
        return self.__currentChildDictionary[self.__currentParamLevel]


    # # \brief Get parent parameter of the parameter.
    #
    #    \param self object reference
    #    \return name of the parent parameter or None
    def __getParenParam(self):
        parentParam = None
        if self.__currentParamLevel > 0:
            parentParam = self.__currentParamStackList[self.__currentParamLevel - 1]
        return parentParam

def main():
    pddbReport = "PDX_REPO.XML"
    pddbData = PDDBData()
    parser = make_parser()
    parser.setFeature(feature_namespaces, 0)
    parser.setContentHandler(pddbData)
    try:
        parser.parse(pddbReport)
    except ValueError:
        print ERROR_MSG
        print "Can't read file:", pddbReport
        sys.exit(3)
    except SAXParseException:
        print ERROR_MSG
        print "XML parsing error:", pddbReport
        sys.exit(4)

    # XML_utils.XML_utils().print_diff_dict(pddbData.__paramNameDictionary[pddbData.__currentObject])
    mo_list = pddbData.getManagedObjectList()
    print mo_list
    for mo in mo_list:
        param_list = pddbData.getParamList(mo)
        print param_list

    for managedObject in pddbData.getManagedObjectList():
        for param, parentParam in pddbData.getParamList(managedObject):
            paramObject = pddbData.getParamObject(managedObject, param, parentParam)

    XML_utils.XML_utils().print_diff_list(managedObject)
        
    # pddbData.__paramNameDictionary = {}    # dictionary to store parameter names of every managed object
    pddbData.__paramDataDictionary = {}    # dictionary to store parameter data of every parameter
    pddbData.__childObjectDictionary = {}    # dictionary containing list of children of every managed objects (if any)
    pddbData.__managedObjectList = []    # list of all RNW objects
    pddbData.__currentObject = None    # current object SAX is processing (e.g. WBTS)
    pddbData.__currentChildObjectList = []    # list of child objects of current object
    pddbData.__currentParamLevel = -1    # 'deepness' of structure, there may be several parameters inside of one
    pddbData.__currentChildDictionary = {}    # dictionary of child parameters in all levels
    pddbData.__currentParamStackList = []    # upper level parameters of struct

if __name__ == '__main__':
    main()
    sys.exit(0)

