## @package CMtools
#    Tools for CM testing.
#    \file Compare.py

#ifndef _COMPARE_
#define _COMPARE_
from xml.sax import handler, make_parser, saxutils
from xml.sax.handler import feature_namespaces
from xml.sax._exceptions import SAXParseException

import xml.dom.minidom as dom
import os, sys

import PDDBData
import Parameter
import CreatePlan
from Definitions import *
from Common import *


## Analyze RNW CM testing result files.
#
# Check initial upload plan, download plan, final upload plan, CM events and RNW plan operation feedbacks against each other and PDDB metadata.
class Compare:

    ## \brief The constructor.
    #
    #    \param self object reference
    #    \param pddbData instance of PDDBData class
    #    \param initialUploadPlan upload plan file before test
    #    \param finalUploadPlan upload plan file after test
    #    \param downloadPlan downloaded plan file
    #    \param cmEvents NWI3 CM events received by NetActStub
    #    \param planFeedbacks plan operation feedbacks received by NetActStub
    #    \return -
    def __init__(self, pddbData, initialUploadPlan, finalUploadPlan, downloadPlan, cmEvents, planFeedbacks):    
        self.__pddbData = pddbData #PDDB object
        self.__initialUploadPlan = initialUploadPlan #initial ul plan name
        self.__finalUploadPlan = finalUploadPlan #final ul plan name
        self.__downloadPlan = downloadPlan #dl plan name
        self.__cmEvents = cmEvents #cm events file name
        self.__planFeedbacks = planFeedbacks #feedbacks file name
        self.__enabledOptionsText = [] #enabled options in upload plan (text value)
        self.__problemsFound = 0
        self.__cocoId = "0" #if COCO is not defined, triplet ATM IF/VPI/VCI parameters are not sent, keep track of the value
        self.__btsType = "N-NB" #check from NBAPCommMode, if S-NB parameters are included to upload plan/event
        #these S-NB parameter are not included in upload plan, if WBTS type is N-NB
        self.__snbParameters = ['BlindTFdetectionUsage', 'DCHnumberRL', 'MaxDCHuserRateRLDL', 'MaxDCHuserRateRLUL', 'HSDPAMPO' , 'NonHSEventECommMeas', \
                                                        'PrxTotalReportPeriod', 'PtxOffsetHSSCCH', 'PtxTotalReportPeriod', 'RACHloadReportPeriod', 'RSEPSEventECommMeas', \
                                                        'RTWPEventECommHyst', 'RTWPEventECommMeas', 'RTWPMeasFilterCoeff', 'TCPEventECommHyst', 'TCPEventECommMeas', 'TCPMeasFilterCoeff']
        self.__createdObjects = [] #list: what object creation events/feedbacks are expected
        self.__modifiedObjects = [] #list: what object modification events/feedbacks are expected
        self.__deletedObjects = [] #list: what object deletion events/feedbacks are expected
        self.__createdParameters = {} #dictionary: what created parameters (and objects) are expected (lists of dom nodes)
        self.__modifiedParameters = {} #dictionary: what modified parameters (and objects) are expected (lists of dom nodes)
        self.__unmodifiedParameters = {} #dictionary: what existing parameters were not modified (lists of dom nodes)
        self.__defaultUlParameters = {} #dictionary: parameters that are set to default by RNC in upload (as dom nodes)
        self.__defaultEventParameters = {} #dictionary: parameters that are set to default by RNC in event (as dom nodes)
        self.__cmEventParameters = {} #dictionary: received CM event parameters (as dom nodes)
        self.__topologyEvents = {} #dictionary: received topolofy events
        self.__analyzedParameters = {} #dictionary: already analyzed parameters, don't report same problem twice
        self.__neId = None #NE under test, used to find events of this RNC only
        self.__expectedParameters = [] #list of expected parameters of single RNW object
        if self.__downloadPlan != None:
            self.__downloadPlanDoc = dom.parse(self.__downloadPlan)
        if self.__initialUploadPlan != None:
            self.__initialUploadPlanDoc = dom.parse(self.__initialUploadPlan)
        #always needed
        self.__finalUploadPlanDoc = dom.parse(self.__finalUploadPlan)
        self.__enabledOptionsText, self.__neId, self.__isAda = getRncOptions(self.__finalUploadPlanDoc, self.__pddbData, self.__finalUploadPlan)
        paramObject = self.__pddbData.getParamObject('RNC', 'RncOptions')
        #topology events from these objects only
        if self.__isAda == True:
            self.__topologyEventObjects = ['IADA', 'WBTS', 'WCEL']
        else:
            self.__topologyEventObjects = ['RNC', 'WBTS', 'WCEL']
        if self.__cmEvents != None:
            self.__parseCmEvents()
            #print "parsed events"
            #for node in self.__cmEventParameters["RNC-59/IUO-1"].documentElement.getElementsByTagName('p'):
            #    print "event p node name:", node.getAttribute('name')
            #for node in self.__cmEventParameters["RNC-59/IUO-1"].documentElement.getElementsByTagName('list'):
            #    print "event list node name:", node.getAttribute('name')
        #set used options for every parameter
        self.__pddbData.setOptions(self.__enabledOptionsText, self.__isAda)


    ## \brief Analyze upload plan and CM events against PDDB.
    #
    #    \param self object reference
    #    \return -
    def analyzeUploadAndEvsnts(self):
        #check all required parameters are present in upload plan
        ulManagedObjects = self.__finalUploadPlanDoc.documentElement.getElementsByTagName('managedObject')
        #compare upload values to event values
        ulParamNames = {} #store param names here as list
        ulParamValues = {} #store param names here as dict
        for ulManagedObject in ulManagedObjects:
            #1) check simple parameters
            className = ulManagedObject.getAttribute('class')
            ulDistName = ulManagedObject.getAttribute('distName')
            ulParamNodes = ulManagedObject.getElementsByTagName('p')
            self.__expectedParameters = self.__pddbData.getAllExpectedParameters(className) #get list of all expected parameters based on enabled options
            if self.__expectedParameters == None:
                print ERROR_MSG
                print "object not defined in PDDB (%s): %s" % (self.__finalUploadPlan, ulDistName)
                self.__problemsFound += 1
                continue
            ulParamNames[ulDistName], ulParamValues[ulDistName] = self.__checkUploadNodes(self.__finalUploadPlan, className, ulDistName, ulParamNodes, self.__expectedParameters, None, None)
            #2) check list parameters
            ulParamNodes = ulManagedObject.getElementsByTagName('list')            
            self.__checkUploadNodes(self.__finalUploadPlan, className, ulDistName, ulParamNodes, self.__expectedParameters, None, None)
            #if object was deleted and still exists, it is reported already: don't complain about every missing parameter too
            if self.__downloadPlan != None:
                dlManagedObjects = self.__downloadPlanDoc.documentElement.getElementsByTagName('managedObject')
                found = False
                for dlManagedObject in dlManagedObjects:
                    dlDistName = dlManagedObject.getAttribute('distName')
                    dlDistName = dlDistName.replace('PLMN-PLMN/', '')
                    if dlDistName == ulDistName and dlManagedObject.getAttribute('operation') == 'delete':
                        found = True
                        break
                if found:
                    continue
            #3) report all expected parameters that were missing
            self.__checkExpectedParameters(self.__finalUploadPlan, ulDistName, self.__expectedParameters)
        #check all required parameters are present in event
        if self.__cmEvents != None:
            for eventDistName in self.__cmEventParameters.iterkeys():
                eventManagedObject = self.__cmEventParameters[eventDistName].getElementsByTagName('managedObject')[0]
                className = eventManagedObject.getAttribute('class')
                if eventManagedObject.getAttribute('operation') == 'delete':
                    continue
                self.__expectedParameters = self.__pddbData.getAllExpectedParameters(className)
                #compare event against upload values
                eventParamNodes = eventManagedObject.getElementsByTagName('p')
                if eventDistName in ulParamValues:
                    self.__checkUploadNodes(self.__cmEvents, className, eventDistName, eventParamNodes, self.__expectedParameters, ulParamValues[eventDistName], ulParamValues[eventDistName])
                else:
                    self.__checkUploadNodes(self.__cmEvents, className, eventDistName, eventParamNodes, self.__expectedParameters, None, None)
                eventParamNodes = eventManagedObject.getElementsByTagName('list')
                self.__checkUploadNodes(self.__cmEvents, className, eventDistName, eventParamNodes, self.__expectedParameters, None, None)
                #if object was created, check all expected parameters exist in event
                if eventDistName in self.__createdObjects:
                    self.__checkExpectedParameters(self.__cmEvents, eventDistName, self.__expectedParameters)


    ## \brief Analyze download plan against initial upload, final upload, CM events, plan feedbacks and PDDB metadata.
    #
    #    \param self object reference
    #    \return -
    def analyzeDownload(self):
        ulManagedObjects = []
        if self.__downloadPlan != None:
            managedObjects = self.__downloadPlanDoc.documentElement.getElementsByTagName('managedObject')
            if self.__initialUploadPlan != None:
                ulManagedObjects = self.__initialUploadPlanDoc.documentElement.getElementsByTagName('managedObject')
            for managedObject in managedObjects:
                distName = managedObject.getAttribute('distName')
                distName = distName.replace('PLMN-PLMN/', '')
                className = managedObject.getAttribute('class')
                operation = managedObject.getAttribute('operation')
                if operation == 'delete':
                    #assume object exists and is deleted, if initial upload plan is not given
                    #otherwise check that it really exists in initial upload plan and can be deleted
                    if self.__initialUploadPlan == None or self.__findManagedObject(self.__initialUploadPlan, ulManagedObjects, distName, False) != None:
                        self.__deletedObjects.append(distName)
                else:
                    if self.__findManagedObject(self.__initialUploadPlan, ulManagedObjects, distName, False) == None:
                        self.__createdObjects.append(distName)
                    else:
                        self.__modifiedObjects.append(distName)
                    #check simple parameters only
                    dlParamNodes = managedObject.getElementsByTagName('p')
                    self.__checkDownloadNodes(distName, className, operation, dlParamNodes)
            self.__checkPlanActivationResults() #now compare download nodes to upload/events/feedbacks


    ## \brief Get nu,mber of found problems during result file analysis.
    #
    #    \param self object reference
    #    \return -
    def getProblemCount(self):
        return self.__problemsFound


    ## \brief Go through download plan and find out created, modified and unmodified nodes.
    #
    #    \param self object reference
    #    \param distName analyzed distName
    #    \param className analyzed object class name
    #    \param operation operation attribute read from the plan
    #    \param dlParamNodes list of downloaded dom parameter nodes of this object
    #    \return -
    def __checkDownloadNodes(self, distName, className, operation, dlParamNodes):
        for dlParamNode in dlParamNodes:
            paramName = dlParamNode.getAttribute('name')
            if paramName == "": #skip all analysis, for example: <p>1</p>
                continue
            parentParam = self.__pddbData.getParentParameter(dlParamNode)
            paramObject = self.__pddbData.getParamObject(className, paramName, parentParam)
            if paramObject == None:
                print "parameter not defined in PDDB, ignore: %s-%s" % (className, paramName)
                continue
            #needed options are not active, parameter will be skipped in download and RNW DB is not modified
            if paramObject.getParamOptionStatus() == False:
                if self.__isAda == False: #ADA has always all licenses enabled
                    print "skip disabled dl parameter: %s->%s" % (distName, paramName)
                    continue
            #check initial upload plan
            created = True
            modified = False
            unmodified = False
            if self.__initialUploadPlan != None:
                managedObjects = self.__initialUploadPlanDoc.documentElement.getElementsByTagName('managedObject')
                for managedObject in managedObjects:
                    if managedObject.getAttribute('distName') == distName: #object exists
                        ulParamNodes = managedObject.getElementsByTagName('p')
                        for ulParamNode in ulParamNodes:
                            if ulParamNode.getAttribute('name') == paramName: #parameter exists
                                created = False
                                #print "checking:", paramName, dlParamNode.firstChild
                                # None means no value (empty element)
                                if ((dlParamNode.firstChild == None and ulParamNode.firstChild != None) or \
                                        (dlParamNode.firstChild != None and ulParamNode.firstChild == None) or \
                                        (ulParamNode.firstChild.nodeValue != dlParamNode.firstChild.nodeValue) and paramObject.getModificationType() != 'unmodifiable' ): #same value, not included in event
                                    modified = True
                                else:
                                    unmodified = True
                                break
                    if modified or unmodified:
                        break
            if created:
                #AutomObjLock is present in download plan only
                if paramName not in ['AutomObjLock']:
                    if not distName in self.__createdParameters:
                        self.__createdParameters[distName] = []
                    self.__createdParameters[distName].append(dlParamNode) #similar node should be present in upload/event
                    #print "created param:", distName, paramName
            elif modified:
                if not distName in self.__modifiedParameters:
                    self.__modifiedParameters[distName] = []
                self.__modifiedParameters[distName].append(dlParamNode)
                #print "modified param:", distName, paramName
            elif unmodified:
                if not distName in self.__unmodifiedParameters:
                    self.__unmodifiedParameters[distName] = []
                self.__unmodifiedParameters[distName].append(dlParamNode)
                #print "unmodified param:", distName, paramName
            else:
                print "unknown parameter operation:", distName, paramName
                sys.exit()


    ## \brief Check that expected RNW changes have been done.
    #
    #    \param self object reference
    #    \return -
    def __checkPlanActivationResults(self):
        ulManagedObjects = self.__finalUploadPlanDoc.documentElement.getElementsByTagName('managedObject')
        #check all object creations
        className = None
        for distName in self.__createdParameters.iterkeys():
            #print "created object:", distName
            self.__checkActivationNodes(distName, ulManagedObjects, self.__createdParameters[distName], self.__defaultUlParameters, self.__defaultEventParameters)
            if distName in self.__createdObjects:
                self.__checkTopologyEvent(distName, 'TPElementCreation')
                #TODO: creation feedbacks
        #check all object modifications
        for distName in self.__modifiedParameters.iterkeys():
            #print "modified object:", distName
            self.__checkActivationNodes(distName, ulManagedObjects, self.__modifiedParameters[distName])
            #TODO: modification feedbacks
        #check parameters that were not modified
        if self.__initialUploadPlan != None:
            self.__checkUnmodifiedParameters()
        #check all object deletions
        for distName in self.__deletedObjects:
            self.__checkDeletedNode(ulManagedObjects, distName)
            self.__checkTopologyEvent(distName, 'TPElementDeletion')
            #TODO: deletion feedbacks


    ## \brief Check created/modified parameter from upload plan.
    #
    #    \param self object reference
    #    \param distName distName of expected object
    #    \param ulManagedObjects list of result managed object as dom nodes
    #    \param paramNodes list of download parameters as dom    nodes
    #    \param defaultUlParameters expected default values in upload (=params missing from download)
    #    \param defaultEventParameters expected default values in event
    #    \return -
    def __checkActivationNodes(self, distName, ulManagedObjects, paramNodes, defaultUlParameters=None, defaultEventParameters=None):
        eventManagedObjects = []
        #get event nodes of this object
        if self.__cmEvents != None:
            if distName in self.__cmEventParameters:
                eventManagedObjects = self.__cmEventParameters[distName].documentElement.getElementsByTagName('managedObject')
            else:
                print ERROR_MSG
                print "object missing (%s): %s" % (self.__cmEvents, distName)
                self.__problemsFound += 1
        for paramNode in paramNodes: #'p' nodes
            paramName = paramNode.getAttribute('name')
            if paramName == "": #e.g. <p>1</p>
                continue
            #what parameters have been analyzed already
            if not distName in self.__analyzedParameters:
                self.__analyzedParameters[distName] = []
            self.__analyzedParameters[distName].append(paramName)
            className = self.__checkCreatedNode(ulManagedObjects, distName, paramNode, self.__finalUploadPlan, defaultUlParameters)
            if className == "": #object is missing
                return
            if eventManagedObjects != []: #CM events
                self.__checkCreatedNode(eventManagedObjects, distName, paramNode, self.__cmEvents, defaultEventParameters)
                #TODO: creation feedbacks
        if distName in self.__createdObjects: #object was created, check parameters set by RNC have default value
            #check created default values in upload
            self.__checkDefaultValues(self.__defaultUlParameters[distName], self.__finalUploadPlan, distName, className)
            #check created default values in event
            if eventManagedObjects != []:
                self.__checkDefaultValues(self.__defaultEventParameters[distName], self.__cmEvents, distName, className)


    ## \brief Check created/modified parameter from upload plan.
    #
    #    \param self object reference
    #    \param resultManagedObjects list of result managed objects as dom nodes
    #    \param expectedDistName distName of expected object
    #    \param dlParamNode download parameter dom node to be created
    #    \param fileName result file name
    #    \param defaultParams list of default parameter values of this created object
    #    \return className object class name or ""
    def __checkCreatedNode(self, resultManagedObjects, expectedDistName, dlParamNode, fileName, defaultParams=None):
        expectedParamName = dlParamNode.getAttribute('name')
        paramFound = False
        className = ""
        managedObject = self.__findManagedObject(fileName, resultManagedObjects, expectedDistName)
        if managedObject == None:
            return ""    
        className = managedObject.getAttribute('class')
        paramNodes = managedObject.getElementsByTagName('p')
        if defaultParams != None and not expectedDistName in defaultParams: #keep track of parameters created by RNC
            defaultParams[expectedDistName] = paramNodes
        paramNode = self.__findParameter(fileName, paramNodes, expectedDistName, dlParamNode)
        if paramNode == None:
            return ""
        if defaultParams != None:
            try:
                defaultParams[expectedDistName].remove(paramNode)
            except ValueError:
                pass #already removed
        #print "compare:", expectedParamName, fileName, expectedDistName, expectedParamName, paramNode.firstChild, dlParamNode.firstChild
        if paramNode.firstChild == None and dlParamNode.firstChild == None:
            pass #empty node created, e.g. <p name="RestrictionGroupName"></p>
        elif expectedParamName in ['SharedAreaMNClength']:
            pass #SharedAreaMNClength default is 2, but it's set to 3 (minor PDDB definition problem, will not be fixed)
        elif paramNode.firstChild == None and dlParamNode.firstChild != None:
            if dlParamNode.firstChild.nodeValue.strip() != '': #when value is empty string (spaces only), RNC sets value to ''
                print ERROR_MSG
                print "parameter value mismatch (%s): %s->%s: %s <=> <empty>" % (fileName, expectedDistName, expectedParamName, dlParamNode.firstChild.nodeValue)
                self.__problemsFound += 1
        elif paramNode.firstChild != None and dlParamNode.firstChild == None:
            if paramNode.firstChild.nodeValue.strip() != '':
                print ERROR_MSG
                print "parameter value mismatch (%s): %s->%s: <empty> <=> %s" % (fileName, expectedDistName, expectedParamName, paramNode.firstChild.nodeValue)
                self.__problemsFound += 1
        elif paramNode.firstChild.nodeValue.strip() != dlParamNode.firstChild.nodeValue.strip():
            print ERROR_MSG
            print "parameter value mismatch (%s): %s->%s: %s <=> %s" % (fileName, expectedDistName, expectedParamName, dlParamNode.firstChild.nodeValue, paramNode.firstChild.nodeValue)
            self.__problemsFound += 1
        return className


    ## \brief Parameters created by RNC (missing from download) should have default value
    #
    #    \param self object reference
    #    \param defaultParameters list of created parameters that should have default value as dom nodes
    #    \param fileName analyzed file name
    #    \param distName analyzed distName
    #    \param className analyzed object class name
    #    \return -
    def __checkDefaultValues(self, defaultParameters, fileName, distName, className):
        for paramNode in defaultParameters:
            paramName = paramNode.getAttribute('name')
            if paramName == '':
                continue
            parentParam = self.__pddbData.getParentParameter(paramNode)
            paramObject = self.__pddbData.getParamObject(className, paramName, parentParam)
            #print "***", distName, parentParam, paramName
            if paramObject == None: #does not exist in PDDB, reported as error in analyzeUpload, just skip it here
                continue
            defaultValue = paramObject.getParamValue(PDDBData.PARAM_VALUE_DEFAULT)
            if defaultValue == None: #for example RNCChangeOrigin: no default, set by the system
                continue
            if paramNode.firstChild != None and paramNode.firstChild.nodeValue.strip() != defaultValue:
                if not paramName in ['WCelState', 'VCCBundlePCR', 'VCCBundleEBS', 'DCNLinkStatus', 'DCNSecurityStatus', 'SecOMSIpAddress', 'HSRACHCapability', 'AvailabilityStatus']: #some parameters may be set to non-default value by system, not a problem
                    print ERROR_MSG
                    print "parameter has non-default value (%s): %s->%s: %s" % (fileName, distName, paramName, paramNode.firstChild.nodeValue)
                    self.__problemsFound += 1


    ## \brief Check deleted objects don't exist anymore
    #
    #    \param self object reference
    #    \param resultManagedObjects list of existing managed objects after test as dom nodes
    #    \param distName analyzed distName
    #    \return -
    def __checkDeletedNode(self, resultManagedObjects, distName):
        for managedObject in resultManagedObjects:
            if managedObject.getAttribute('distName') == distName:
                if managedObject.getAttribute('distName') != 'delete':
                    print ERROR_MSG
                    print "deleted object found (%s): %s" % (self.__finalUploadPlan, distName)
                    self.__problemsFound += 1
        if self.__cmEvents != None:
            if distName in self.__cmEventParameters:
                eventManagedObject = self.__cmEventParameters[distName].documentElement.getElementsByTagName('managedObject')[0]
                if eventManagedObject.getAttribute('operation') != 'delete':
                    print ERROR_MSG
                    print "not deletion event (%s): %s" % (self.__cmEvents, distName)
                    self.__problemsFound += 1
            else:
                print ERROR_MSG
                print "deletion event missing (%s): %s" % (self.__cmEvents, distName)
                self.__problemsFound += 1


    ## \brief Check upload nodes
    #
    #    \param self object reference
    #    \param fileName analyzed file name
    #    \param className analyzed object class name
    #    \param distName analyzed distName
    #    \param paramNodes parameter nodes to be checked as list of dom nodes
    #    \param expectedParams expected parameter names as list
    #    \param ulParameterNames parameter names in upload, check against event
    #    \param ulParameterValues parameter values in upload, check against event
    #    \return paramNames as list, paramValues as dictionary
    def __checkUploadNodes(self, fileName, className, distName, paramNodes, expectedParams, ulParameterNames, ulParameterValues):
        #store all expected parameters as a copy, items are removed from expectedParams as they are found
        #=> if same unexpected parameter is present multiple times in upload/event, only one error msg
        allParams = list(expectedParams)
        paramNames = []
        paramValues = {}
        for paramNode in paramNodes:
            paramName = paramNode.getAttribute('name')
            #print "paramName (%s): %s-%s" % (fileName, className, paramName)
            if paramName != "":
                if paramName == 'NBAPCommMode':
                    if paramNode.firstChild.nodeValue == "1":
                        self.__btsType = "S-NB" #Siemens BTS
                if paramName == 'COCOId':
                    self.__cocoId = paramNode.firstChild.nodeValue
                parentParam = self.__pddbData.getParentParameter(paramNode)                
                paramObject = self.__pddbData.getParamObject(className, paramName, parentParam)
                if paramObject == None:
                    print ERROR_MSG
                    print "parameter not defined in PDDB (%s): %s->%s" % (fileName, distName, paramName)
                    self.__problemsFound += 1
                    continue
                if paramObject.getParamPlanDirection() != None and paramObject.getParamOptionStatus() == False:
                    if self.__isAda == False: #ADA has always all licenses enabled
                        print ERROR_MSG
                        print "disabled parameter (%s): %s->%s" % (fileName, distName, paramName)
                        self.__problemsFound += 1
                else:
                    #check value of simple parameters (lists have no values)
                    #parameter might not have a value, for exzample <p name="BTSAdditionalInfo"></p>
                    if paramNode.firstChild != None: # dom.Node.TEXT_NODE
                        if paramNode.firstChild.nodeValue != None:
                            errorText = paramObject.isValidValue(paramNode.firstChild.nodeValue)
                            if errorText != '':
                                print ERROR_MSG
                                print "illegal value, %s (%s): %s->%s" % (errorText, fileName, distName, paramName)
                                self.__problemsFound += 1
                            if ulParameterNames == None: #store upload values, so that can compare to event values
                                paramNames.append(paramName) #<name> <value>
                                paramValues[paramName] = paramNode.firstChild.nodeValue.strip()
                            else: #check event vs. upload values
                                if paramName in ulParameterNames:
                                    if not paramName in ['WCELChangeOrigin', 'WBTSChangeOrigin']: #RNC sends value 1 in event during cell creation and 2 in upload, but that is acceptable for Netact
                                        if paramNode.firstChild.nodeValue.strip() != ulParameterValues[paramName]:
                                            print ERROR_MSG
                                            print "different value in upload (%s): %s->%s: %s <=> %s" % (fileName, distName, paramName, paramNode.firstChild.nodeValue.strip(), ulParameterValues[paramName])
                                            self.__problemsFound += 1
                    if paramName in allParams: #is an expected parameter
                        try:
                            expectedParams.remove(paramName)
                        except ValueError: #if parameter is present multiple times, it might be deleted already
                            pass
                    else:
                        print ERROR_MSG
                        print "unexpected parameter (%s): %s->%s" % (fileName, distName, paramName)
                        self.__problemsFound += 1
        return (paramNames, paramValues)


    ## \brief Check all expected parameters exist
    #
    #    \param self object reference
    #    \param fileName analyzed file name
    #    \param distName analyzed distName
    #    \param expectedParams list of expected parameters
    #    \return -
    def __checkExpectedParameters(self, fileName, distName, expectedParams):
        for expectedParam in expectedParams:
            if distName in self.__analyzedParameters:
                if expectedParam in self.__analyzedParameters[distName]:
                    continue
            #if not distName in self.__createdParameters: #check expected parameters for created objects only
            # continue
            #ignore S-NB parameters if N-NB WBTS
            if self.__btsType == "N-NB" and not expectedParam in self.__snbParameters:
                #1) if COCO is not defined, ATM IF/VPI/VCI are missing
                #2) AdminWBTSState can be used by direct activation only, not present in upload
                #3) ServingOMSSwoRequest: download parameter only
                if (self.__cocoId == "0" and not expectedParam in ['VCI', 'VPI', 'ATMInterfaceID']) and not expectedParam in ['AdminWBTSState', 'ServingOMSSwoRequest']:
                    #SharedAreaPLMNid list is set to empty by default, list items are missing
                    if not expectedParam in ['SharedAreaMCC', 'SharedAreaMNC', 'SharedAreaMNClength']:
                        print ERROR_MSG
                        print "parameter missing (%s): %s->%s" % (fileName, distName, expectedParam)
                        self.__problemsFound += 1


    ## \brief Check unmodified parameters were not modified in final upload plan
    #
    #    \param self object reference
    #    \return -
    def __checkUnmodifiedParameters(self):
        finalManagedObjects = self.__finalUploadPlanDoc.documentElement.getElementsByTagName('managedObject')
        initialManagedObjects = self.__initialUploadPlanDoc.documentElement.getElementsByTagName('managedObject')        
        for finalManagedObject in finalManagedObjects:
            distName = finalManagedObject.getAttribute('distName')
            if not distName in self.__createdObjects and not distName in self.__deletedObjects: #object exists in both upload plans
                initialManagedObject = self.__findManagedObject(self.__initialUploadPlan, initialManagedObjects, distName)
                if initialManagedObject == None:
                    continue
                finalParamNodes = finalManagedObject.getElementsByTagName('p')
                initialParamNodes = initialManagedObject.getElementsByTagName('p')
                for finalParamNode in finalParamNodes:
                    paramName = finalParamNode.getAttribute('name')
                    if paramName == "":
                        continue
                    if self.__isParameterModified(distName, paramName):
                        continue
                    initialParamNode = self.__findParameter(self.__initialUploadPlan, initialParamNodes, distName, finalParamNode)
                    if initialParamNode == None:
                        continue
                    #print "param:", paramName, finalParamNode.firstChild.nodeValue
                    if initialParamNode.firstChild != None and initialParamNode.firstChild.nodeValue.strip() != finalParamNode.firstChild.nodeValue.strip():
                        print ERROR_MSG
                        print "unmodified parameter changed (%s): %s->%s" % (self.__initialUploadPlan, distName, paramName)
                        self.__problemsFound += 1


    ## \brief Check if parameter was modified in the test
    #
    #    \param self object reference
    #    \param distName analyzed distName
    #    \param paramName parameter name
    #    \return True or False
    def __isParameterModified(self, distName, paramName):
        if not distName in self.__unmodifiedParameters:
            #print "param was modified: %s->%s" % (distName, paramName)
            return True
        else:
            for paramNode in self.__unmodifiedParameters[distName]:
                if paramNode.getAttribute('name') == paramName:
                    #print "param was not modified: %s->%s" % (distName, paramName)
                    return False
        #print "param was modified: %s->%s" % (distName, paramName)
        return True


    ## \brief Find managed object by distName
    #
    #    \param self object reference
    #    \param fileName analyzed file name
    #    \param managedObjects all present managed objects as dom nodes
    #    \param distName analyzed distName
    #    \param reportError report as error if not found
    #    \return found managedObject or None
    def __findManagedObject(self, fileName, managedObjects, distName, reportError=True):
        for managedObject in managedObjects:
            if managedObject.getAttribute('distName') == distName:
                return managedObject
        if reportError:
            print ERROR_MSG
            print "object missing (%s): %s" % (fileName, distName)
            self.__problemsFound += 1
        return None


    ## \brief Find parameter by parameter name
    #
    #    \param self object reference
    #    \param fileName analyzed file name
    #    \param paramNodes all present parameters as list of dom nodes
    #    \param distName analyzed distName
    #    \param expectedParamNode parameter to be found
    #    \return parameter dom node or None
    def __findParameter(self, fileName, paramNodes, distName, expectedParamNode):
        #same parameter name may be used inside different lists within the same object, check parent parameter name also
        #for example: PLMNid.MCC, ICRPLMNid.MCC
        #<managedObject class="IUO" distName="RNC-59/IUO-1" operation="create" version="RN6.0">
        #    <p name="NRILengthForCSCN">0</p>
        #    <p name="NRILengthForPSCN">0</p>
        #    <p name="NullNRIForCSPool">1024</p>
        #    <p name="NullNRIForPSPool">1024</p>
        #    <p name="OperatorWeight">0</p>
        #    <list name="PLMNid">
        #        <item>
        #            <p name="MCC">520</p>
        #            <p name="MNC">18</p>
        #            <p name="MNCLength">2</p>
        #        </item>
        #    </list>
        #    <list name="ICRPLMNid">
        #        <item>
        #            <p name="MCC">520</p>
        #            <p name="MNC">18</p>
        #            <p name="MNCLength">2</p>
        #        </item>
        #    </list>
        for paramNode in paramNodes:
            #parent name is '' if not found
            if paramNode.getAttribute('name') == expectedParamNode.getAttribute('name') and \
                 paramNode.parentNode.parentNode.getAttribute('name') == expectedParamNode.parentNode.parentNode.getAttribute('name'):
                parentParamName = paramNode.parentNode.parentNode.getAttribute('name')
                #print "found parameter:", parentParamName, paramNode.getAttribute('name')
                return paramNode
        #AutomObjLock belongs to download plan only
        if expectedParamNode.getAttribute('name') not in ['AutomObjLock']:
            print ERROR_MSG
            print "parameter missing (%s): %s->%s" % (fileName, distName, expectedParamNode.getAttribute('name'))
            self.__problemsFound += 1
        return None


    ## \brief Parse event XML from NetActStub event file
    #
    #    \param self object reference
    #    \param distName analyzed distName
    #    \param operation operation for object, 'TPElementCreation' or 'TPElementDeletion'
    #    \return -
    def __checkTopologyEvent(self, distName, operation):
        if self.__cmEvents != None:
            className = distName
            if distName.find('/') != -1:
                className = distName.split('/')[-1]
            className = className.split('-')[0] #RNC-135 => RNC
            if className in self.__topologyEventObjects:
                if not distName in self.__topologyEvents:
                    print ERROR_MSG
                    print "topology event missing (%s): %s->%s" % (self.__cmEvents, distName, operation)
                    self.__problemsFound += 1
                elif self.__topologyEvents[distName] != operation:
                    print ERROR_MSG
                    print "wrong topology event type (%s): %s->%s <=> %s" % (self.__cmEvents, distName, self.__topologyEvents[distName], operation)
                    self.__problemsFound += 1


    ## \brief Check all parameters in event have legal values
    #
    #    \param self object reference
    #    \param doc event content as XML document
    #    \param className analyzed object class
    #    \param distName analyzed distName
    #    \return -
    def __checkParamValues(self, doc, className, distName):
        if len( doc.documentElement.getElementsByTagName('managedObject') ) > 1: #assume only one managedObject in one event
            print "more than one managedObject in event!"
            print "need to add proper handling, exiting..."
            sys.exit()
        paramNodes = doc.documentElement.getElementsByTagName('p') 
        for paramNode in paramNodes:
            paramName = paramNode.getAttribute('name')
            if paramName == '':
                continue
            if paramNode.firstChild != None:
                value = paramNode.firstChild.nodeValue
                parentParam = self.__pddbData.getParentParameter(paramNode)
                paramObject = self.__pddbData.getParamObject(className, paramName, parentParam)
                if paramObject == None: #does not exist in PDDB
                    continue
                errorText = paramObject.isValidValue(paramNode.firstChild.nodeValue)
                if errorText != '':
                    print ERROR_MSG
                    print "illegal value, %s (%s): %s->%s" % (errorText, self.__cmEvents, distName, paramName)
                    self.__problemsFound += 1


    ## \brief Parse event XML from NetActStub event file
    #
    #    \param self object reference
    #    \return -
    def __parseCmEvents(self):
        f = open(self.__cmEvents, 'r')
        topologyEvent = False
        index = -1
        lines = f.readlines()
        f.close()
        cmEventFound = False
        for line in lines:
            index += 1
            
            #
            # TpEvent_V1 of RNC under test found (GOMS can be connected to multiple RNCs)
            #
            #structEvent.filterable_data.length() = 12
            #filterable_data[0].name = typeOfEvent
            #filterable_data[0].value = (enum) TPElementCreation (0)
            #filterable_data[1].name = tpElemType
            #filterable_data[1].value = (string) WCEL
            #filterable_data[2].name = tpElemPtr
            #filterable_data[2].value = (NWI3::ManagedObjectSpecifier) class=NE BaseId=NE-RNC-135 LocalMOID = DN:NE-WBTS-72/WCEL-1
            if line.find('filterable_data[2].value = (NWI3::ManagedObjectSpecifier) class=') != -1:
                if line.find(self.__neId) != -1:
                    typeOfEvent = lines[index-4]
                    typeOfEvent = typeOfEvent.replace('filterable_data[0].value = (enum) ', '')
                    typeOfEvent = typeOfEvent.split(' (')[0]
                    typeOfEvent = typeOfEvent.strip()
                    tpElemType = lines[index-2]
                    tpElemType = tpElemType.split(' = (string) ')[1]
                    tpElemType = tpElemType.strip()
                    #print "tpElemType:", tpElemType
                    if tpElemType in self.__topologyEventObjects:
                        distName = line.split(' LocalMOID = ')[1]
                        distName = distName.replace('DN:NE-', '')
                        distName = distName.strip()
                        distName = self.__neId + '/' + distName
                        distName = distName.replace('NE-', '')
                        if typeOfEvent == 'TPElementCreation' or typeOfEvent == 'TPElementDeletion':
                            #print "distName:", distName, typeOfEvent
                            self.__topologyEvents[distName] = typeOfEvent
            
            #
            # RACCMModificationEvent_V2 of RNC under test found (GOMS can be connected to multiple RNCs)
            #
            if line.find('filterable_data[4].value = (NWI3::ManagedObjectSpecifier) class=NE BaseId=') != -1:
                cmEventStartIndex = None
                cmEventStopIndex = None
                distName = None
                if line.find(self.__neId) != -1:
                    cmEventFound = True
                    #print "*** event header found"
                else:
                    cmEventFound = False
                continue
            if cmEventFound == False:
                continue
            if line.find('<?xml version') != -1:
                cmEventStartIndex = index
            loc = line.find('distName=')
            if loc != -1: #distName needed as a dictonary key
                #<managedObject class="WBTS" distName="RNC-135/WBTS-72" version="RN6.0" ...
                #=>
                #RNC-135/WBTS-72
                distName = line[loc:]
                distName = distName.split(' ')[0] #distName="RNC-135/WBTS-72" version="RN6.0" operation="update">
                distName = distName.replace('distName=', '')
                distName = distName.replace('\"', '')
            if line.find('</raml>') != -1:
                cmEventStopIndex = index
                xmlData = lines[cmEventStartIndex:cmEventStopIndex+1]
                #event start includes data = <?xml version ...
                xmlData[0] = xmlData[0].replace('data =', '')
                xmlData[0] = xmlData[0].lstrip()
                xmlData = ''.join(xmlData) #list of strings to plain string
                #print "parsing event data:"
                #print xmlData
                doc = dom.parseString(xmlData)
                operation = doc.documentElement.getElementsByTagName('managedObject')[0].getAttribute('operation')
                className = doc.documentElement.getElementsByTagName('managedObject')[0].getAttribute('class')
                if operation != 'delete':
                    self.__checkParamValues(doc, className, distName)
                if distName in self.__cmEventParameters and operation != 'delete': #event for same object, update params
                    newParamNodes = doc.documentElement.getElementsByTagName('p')
                    oldParamNodes = self.__cmEventParameters[distName].documentElement.getElementsByTagName('p')
                    for newParamNode in newParamNodes:
                        #if inside list, need to check list name also
                        newParamName = newParamNode.getAttribute('name')
                        newParentParamName = newParamNode.parentNode.parentNode.getAttribute('name')
                        if newParamName == "":
                            continue
                        found = False
                        for oldParamNode in oldParamNodes:
                            oldParamName = oldParamNode.getAttribute('name')
                            oldParentParamName = oldParamNode.parentNode.parentNode.getAttribute('name')
                            if newParamName == oldParamName and newParentParamName == oldParentParamName:
                                found = True
                                if newParamNode.firstChild != None: #parameter might not have any value
                                    #print "update value of:", newParamName, newParamNode.firstChild.nodeValue, oldParamName, oldParamNode.firstChild
                                    if oldParamNode.firstChild != None:
                                        oldParamNode.firstChild.nodeValue = newParamNode.firstChild.nodeValue
                                    else:
                                        oldParamNode.appendChild(newParamNode.firstChild)
                                    break
                        if found == False: #totally new parameter
                            #print "new parameter in event:", distName, newParamName
                            managedObject = self.__cmEventParameters[distName].documentElement.getElementsByTagName('managedObject')[0]
                            #add full list if needed
                            #
                            #<list name="URAId">
                            #    <p>65535</p>
                            #</list>
                            if newParamNode.parentNode.nodeName == 'list':
                                newParamNode = newParamNode.parentNode
                            #<list name="PowerOffsetSCCPCHTFCI">
                            #    <item>
                            #        <p name="PO1_15">24</p>
                            #        <p name="PO1_30">24</p>
                            #        <p name="PO1_60">24</p>
                            #    </item>
                            #</list>
                            elif newParamNode.parentNode.nodeName == 'item':
                                newParamNode = newParamNode.parentNode.parentNode
                            node = self.__cmEventParameters[distName].importNode(newParamNode, True) #import node from new to old xml document
                            managedObject.appendChild(node)
                            oldParamNodes = self.__cmEventParameters[distName].documentElement.getElementsByTagName('p') #fetch list again, nodes were added
                else: #first event or deletion event
                    self.__cmEventParameters[distName] = doc


#endif

def main():
    #pddbReport = "PDX_REPO.XML"
    pddbReport = "PDDB_REP.xml"
    pddbData = PDDBData.PDDBData()
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

    #XML_utils.XML_utils().print_diff_dict(pddbData.__paramNameDictionary[pddbData.__currentObject])
    moList = pddbData.getManagedObjectList()
    print moList
    for mo in moList:
        paramList = pddbData.getParamList(mo)
        for paramName, parentParam in paramList:
            print paramName, parentParam
            paramObject = pddbData.getParamObject(mo, paramName, parentParam)
            paramName = paramObject.getName()
            if parentParam != None:
                parentParamObject = pddbData.getParamObject(mo, parentParam)
            else:
                parentParamObject = None
            paramDefaultValue = paramObject.getDefaultValue()
            if paramObject.getInterface():
                paramInterface = paramObject.getParamPlanDirection()
            print paramName, paramDefaultValue, paramInterface
            
            

        
    compare = Compare(pddbData, "InitialUpload.XML", "FinalUpload.XML", "DownloadActivation.XML", None, None)
        #compare = Compare.Compare(pddbData, "InitialUpload.XML", "FinalUpload.XML", "DownloadActivation.XML", cmEvents, planFeedbacks)
    compare.analyzeDownload()
    compare.analyzeUploadAndEvsnts()
    print "\n%d problems found" % compare.getProblemCount()
    
if __name__ == '__main__':
    main()
    sys.exit(0)