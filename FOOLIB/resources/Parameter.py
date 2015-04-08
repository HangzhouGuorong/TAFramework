## @package CMtools
#    Tools for CM testing.
#    \file Parameter.py

#ifndef _PARAMETER_
#define _PARAMETER_

import os, sys, re

#import PDDBData
from Definitions import *
from Common import *


## Stores data of a single PDDB parameter definition.
#
# Instance of this class stores data of a single PDDB parameter definition.
class Parameter:


    ## \brief The constructor.
    #
    #    \param self object reference
    #    \return -
    def __init__(self):
        debugTrace(DEBUG_ENTER)
        self.__name = None                                #e.g. 'ActivationTimeOffset'
        self.__fullName = None                        #e.g. 'Offset for activation time'
        self.__status = None                            #e.g. 'approved'
        self.__managedObject = None             #e.g. 'FMCI'
        self.__parentParam = None                 #parent parameter name of this parameter
        self.__paramType = None                     #'simpleType' or 'complexType'
        self.__maxOccurs = None                     #number of max parameter occurs in plan
        self.__modificationType = None        #'unmodifiable', onLine' or 'objectLocking'
        self.__creationPriority = None        #'mandatory' or 'optional'
        self.__featuresAsText = ""                #e.g. "HSDPA AND HSDPA Associated Uplink DPCH Scheduling OR HSDPA AND HSDPA Associated Uplink DPCH Scheduling AND 16 kbps Return Channel DCH Data Rate Support for HSDPA"
        self.__featuresAsBool = ""                #above with boolean values, to be used with eval(): "True and False or True and True and True"
        self.__defaultValue = None                #default values of parameter
        self.__internalValue = None               #internal value of parameter
        self.__paramPlanDirection = None    #parameter direction in plan: none, 'bi' or 'uni'
        self.__paramGuiDirection = None
        self.__paramInterfaceDirection = None #interface direction: bi, uni-up, uni-down, None
        self.__hasInterface = False             #check that parameter has interface definition in PDDB (mandatory field)
        self.__locationInGui = None             #e.f. "RNC RNW Object Browser/WCDMA Cell-dialog/General-tab"

        #following are in use only, if paramType = 'simple'
        #---begin
        self.__valueBase = None    #'string', 'decimal' or 'integer'

        #values from XML report
        self.__minValue = None
        self.__maxValue = None
        self.__defaultValue = None
        self.__valueStep = 1
        self.__divisor = 1
        self.__multiplicand = 1
        self.__shift = 0
        self.__enumerationValues = [] #list of all possible enumeration numeric values
        self.__enumerationTexts = {} #list of all possible enumeration text values
        self.__bits = [] #list of bits (in bitmap)
        self.__specialValue = None
        #---end

        #in use, if paramType = 'complex'
        self.__childParams = []    #child parameters of this parameter
     
        #set standard features are always on (=True)
        #'Full WCDMA 1900 UARFCN range' is for UARFCN
        self.__standardFeatures = ['Extension of sib11', 'BTS AAL2 Multiplexing Function', '3GPP Iub', 'Inter-system Handover Cancellation', \
                                                             'Load Based AMR Codec Mode Selection', 'Fast L1 Syncronisation', 'Replacing EMT with BTSOM in RNC', \
                                                             'Replacing EMT with BTSOM in mcRNC', 'New WBTS Parameters in Topology Data for Flexi/Ultra/MetroSite BTSs', \
                                                             'Cell Selection Parameter Set', 'Cell Selection Parameter Set', 'Compressed mode', 'Dynamic Link Optimisation for NRT Traffic Coverage', \
                                                             'C-Iub: Changes to Eb/N0 Parameterization', 'Basic functions', 'Radio Connection Performance Measurements', \
                                                             'Automatic OMS resiliency', 'Full WCDMA 1900 UARFCN range', 'Nokia Integrated O&M for Andrew 3G Pico BTS', 'Source IP on ICSU used for IuBC interface']
        
        #lookup table: map option name to different feature name (not all option and feature names are the same in PDDB)
        self.__mapOptionsToFeatures = {}
        self.__mapOptionsToFeatures['Detected Set Reporting Based SHO'] = 'Soft Handover Based on Detected Set Reporting'
        self.__mapOptionsToFeatures['Inter System Handover'] = 'WCDMA - GSM Inter-system Handover'
        self.__mapOptionsToFeatures['Load and Service Based Handover'] = 'Load and Service Based Inter-System/Inter-Frequency Handover'
        self.__mapOptionsToFeatures['WCDMA 1.7/2.1GHz'] = 'WCDMA 1700/2100'
        self.__mapOptionsToFeatures['WCDMA 1.7 and 1.8GHz'] = 'WCDMA 1700 & 1800'
        self.__mapOptionsToFeatures['HSDPA with AMR'] = 'HSDPA with Simultaneous AMR Voice Call'
        self.__mapOptionsToFeatures['Radio Network Access Regulation'] = 'Radio Network Access Regulation Function'
        self.__mapOptionsToFeatures['Flexible Connection of VPCs for WBTS'] = 'Flexible connection of VPCs for WBTS object in RNC'
        self.__mapOptionsToFeatures['IP Based Iub'] = 'IP Based Iub for Flexi WCDMA BTS'
        self.__mapOptionsToFeatures['Flexible IU'] = 'Flexible Iu'
        self.__mapOptionsToFeatures['RNC Iu Link Break Protection'] = 'RNC license control for Iu link break protection'
        self.__mapOptionsToFeatures['IP based IU-CS'] = 'IP based Iu-CS'
        self.__mapOptionsToFeatures['IP based IU-PS'] = 'IP based Iu-PS'
        self.__mapOptionsToFeatures['IP based Iur'] = 'IP Based Iur'
        self.__mapOptionsToFeatures['HSPA Inter RNC Cell Change'] = 'HSPA Inter-RNC Cell Change'
        self.__mapOptionsToFeatures['HS-FACH'] = 'High speed Cell_FACH DL'
        self.__mapOptionsToFeatures['Location Services - RTT'] = 'LCS - Cell Coverage Based (RTT) with Geographical Coordinates'
        self.__mapOptionsToFeatures['HSDPA 48 users per cell'] = 'HSDPA 48 Users per Cell'
        self.__mapOptionsToFeatures['Throughput Based Optimisation of PS Algorithm'] = 'Throughput based optimization of the PS algorithm'
        self.__mapOptionsToFeatures['Automated Definition of Neighbouring Cell'] = 'Automatic Definition of Neighbouring Cells'
        self.__mapOptionsToFeatures['Iub Transport QOS'] = 'Iub Transport QoS'
        self.__mapOptionsToFeatures['NodeB RAB Reconfig Support'] = 'PS RAB Reconfiguration'
        self.__mapOptionsToFeatures['Wideband AMR Codec Set [12.65, 8.85, 6.6]'] = 'Wideband AMR Codec Set (12.65, 8.85, 6.6)'
        self.__mapOptionsToFeatures['HSDPA Code multiplexing'] = 'HSDPA Code Multiplexing'
        self.__mapOptionsToFeatures['LCS periodical reporting'] = 'LCS Periodical Reporting'
        self.__mapOptionsToFeatures['Directed Retry of AMR call'] = 'Directed Retry of AMR call Intersystem Handover'
        self.__mapOptionsToFeatures['Multi-operator RAN'] = 'Multioperator RAN'
        self.__mapOptionsToFeatures['AMR Codec Sets [12.2,7.95,5.90,4.75] & [5.90,4.75]'] = 'AMR Codec Sets (12.2, 7.95, 5.90, 4.75) and (5.90, 4.75)'
        self.__mapOptionsToFeatures['Support for Tandem/Transcoder Free Operation'] = 'Support for Tandem and Transcoder Free Operarations (TFO & TrFO)'
        self.__mapOptionsToFeatures['HSUPA with simultaneous AMR voice call'] = 'HSUPA with Simultaneous AMR Voice Call'
        self.__mapOptionsToFeatures['HSUPA Basic 60 users per BTS'] = 'HSUPA 60 Users per BTS'
        self.__mapOptionsToFeatures['16 kbps Return Ch DCH Data Rate Support for HSDPA'] = '16 kbps Return Channel DCH Data Rate Support for HSDPA'
        self.__mapOptionsToFeatures['Intelligent Emergency Inter System Handover'] = 'Intelligent Directed Emergency Call Inter-System Handover'
        self.__mapOptionsToFeatures['Enhanced Priority Based Scheduling and OLC'] = 'Enhanced Priority Based Scheduling and Overload Control for NRT Traffic'
        self.__mapOptionsToFeatures['HSUPA 2ms TTI'] = 'HSUPA 2 ms TTI'
        self.__mapOptionsToFeatures['NRT Multi-RABs on HSPA'] = 'HSPA Multi NRT RABs'
        self.__mapOptionsToFeatures['HSUPA Inter Frequency Handover'] = 'HSUPA inter frequency handover'
        self.__mapOptionsToFeatures['HSPA 128 users'] = 'HSPA 128 users per cell'
        self.__mapOptionsToFeatures['Dual Iub'] = 'Dual Iub for Flexi WCDMA BTS'
        self.__mapOptionsToFeatures['UE based A-GPS'] = 'UE Based A-GPS Using External Reference Network '
        self.__mapOptionsToFeatures['Network based A-GPS'] = 'Network Based A-GPS Using External Reference Network'
        self.__mapOptionsToFeatures['IP Based Iub'] = 'IP Based Iub for Flexi WCDMA BTS'
        self.__mapOptionsToFeatures['Enhanced Virtual Antenna Mapping'] = 'Virtual antenna mapping'
        self.__mapOptionsToFeatures['Smart LTE Layering feature'] = 'Smart LTE Layering'
        self.__mapOptionsToFeatures['PCAP for CellID Measurement Method'] = 'PCAP Position Calculation procedure for Cell-ID Measurement Method'
        self.__mapOptionsToFeatures['CS Service Enabling Handover'] = 'I-HSPA CS Service Enabling HO'
        self.__mapOptionsToFeatures['AMR with DCH (0,0) Support on Iur'] = 'AMR with DCH (0,0) Support on Iur'
        self.__mapOptionsToFeatures['HSPA conversational QoS'] = 'PS conversational QoS for HSPA'
        self.__mapOptionsToFeatures['AMR with DCH (0,0) Support for Iur'] = 'AMR with DCH (0,0) Support on Iur'
        self.__mapOptionsToFeatures['Automatic Access Class Restriction'] = 'Automatic access class restriction'
        self.__mapOptionsToFeatures['Terminal Battery Drain Prevention in Cell Broadcas'] = 'Terminal Battery Drain Prevention in Cell Broadcast'
        self.__mapOptionsToFeatures['High Speed Cell FACH Uplink'] = 'High speed Cell_FACH Uplink'
        self.__mapOptionsToFeatures['RRC connection Redirection'] = 'RRC Connection Setup Redirection'
        self.__mapOptionsToFeatures['Improved CS CallSetup Attempts Starting FACH/PCH'] = 'Improvements to CS Call Setup Attempts Starting from Cell_FACH/Cell_PCH'
        self.__mapOptionsToFeatures['UEs Handling Measurement Events e6f/e6g Incorectly'] = 'UEs Handling Measurement Events e6f/e6g Incorrectly'
        self.__mapOptionsToFeatures['MultiRABSRNS Relocation Incompatibility with Huaw'] = 'Multi-RAB SRNS Relocation Incompatibility with Huawei DRNC'
        self.__mapOptionsToFeatures['MultiRAB Handling with Ericsson in SRNS Relocation'] = 'Multi-RAB handling with Ericsson in SRNS Relocation'
        self.__mapOptionsToFeatures['RABActFail and AccessFail due to UE after StateTra'] = 'RAB Act Fail and Access Fail due to UE after State Transition'
        self.__mapOptionsToFeatures['RRC connection Setup Redirection'] = 'RRC Connection Setup Redirection'
        self.__mapOptionsToFeatures['HSPA+ over Iur'] = 'HSPA+ Over Iur'
        self.__mapOptionsToFeatures['Inter-frequency Handover over Iur'] = 'IFHO Over Iur'
        #self.__mapOptionsToFeatures['RNC Resiliency'] = 'RNC RESILIENCY'
        self.__mapOptionsToFeatures['BTS load based AACR'] = 'BTS Load Based AACR'
        
        #ADA
        self.__mapOptionsToFeatures['Paging Optimization'] = 'Paging Optimizations'
        self.__mapOptionsToFeatures['Domain Specific Access Class Restriction'] = 'I-HSPA CS voice enabler'
        self.__mapOptionsToFeatures['CS Service Enabling Handover'] = 'I-HSPA CS Service Enabling HO'
        debugTrace(DEBUG_EXIT)


    #
    # Public methods
    #


    ## \brief Should parameter be present in download plan.
    #
    #    \param self object reference
    #    \return None, 'bi', 'uni' or None
    def getParamPlanDirection(self):
        return self.__paramPlanDirection

    def getParamInterfaceDirection(self):
        return self.__paramInterfaceDirection
    
    def getParamInternalValue(self, ui_value):
        if (self.__internalValue != None) and (self.__internalValue != "= UI_value") and ( self.getSpecialValue() != self.getDefaultValue()) :
            expression = self.__internalValue.replace("=", " ")
            expression = expression.replace("UI_value", ui_value)
            return eval(expression)
        else:
            return None

    ## \brief Check step: parameter value can be incremented by step amount only.
    #
    #    \param self object reference
    #    \param value plan value set by the user
    #    \return result (True or False)
    def isStepValid(self, value):
        if self.__valueBase == 'decimal':
            valueStep =    int( float(self.__valueStep) * int(self.__divisor) / int(self.__multiplicand) )
            if value % valueStep:
                return False
        #check enueration value (integer type can be bitmap also)
        elif self.__valueBase == 'integer' and len(self.__enumerationValues) > 0:
            if not str(value) in self.__enumerationValues:
                return False
        return True


    ## \brief Validate certain PDDB definitions.
    #
    #    \param self object reference
    #    \return result True or False (=validation passed/failed)
    def validate(self):
        result = True        
        errorText = "*** PDDB problem:"
        if self.__paramType == None:
            print errorText
            print "parameter type not defined: %s-%s" % (self.__managedObject, self.__name)
            result = False
        if self.__maxOccurs == None:
            print errorText
            print "max occurs    not defined: %s-%s" % (self.__managedObject, self.__name)
            result = False
        if self.__modificationType == None:
            print errorText
            print "modification type not defined: %s-%s" % (self.__managedObject, self.__name)
            result = False
        if self.__creationPriority == None:
            print errorText
            print "creation priority not defined: %s-%s" % (self.__managedObject, self.__name)
            result = False
        #if self.__paramPlanDirection == None and self.__managedObject != 'COCO': #some legacy COCO parameters have no IF definition, e.g. 'AAL2SigTPAdmState', 'DATree'
        if self.__hasInterface == False:
            print errorText
            print "interface not defined: %s-%s" % (self.__managedObject, self.__name)
            result = False
        if self.__paramType == 'simpleType' and self.__valueBase == None:
            print errorText
            print "value base not defined: %s-%s" % (self.__managedObject, self.__name)
            result = False
        #check PDDB min, max, default
        if self.__valueBase == 'decimal':
            if self.__minValue == None:
                print errorText
                print "min value not defined: %s-%s" % (self.__managedObject, self.__name)
                result = False
            if self.__maxValue == None:
                print errorText
                print "max value not defined: %s-%s" % (self.__managedObject, self.__name)
                result = False
            if self.__minValue != None and self.__maxValue != None:
                if self.__defaultValue != None and self.__defaultValue != self.__specialValue: #default can be special and special can be outside range
                    if float(self.__defaultValue) < float(self.__minValue):
                        print errorText
                        print "default value less than min value: %s-%s (min=%s, default=%s)" % (self.__managedObject, self.__name, self.__minValue, self.__defaultValue)
                        result = False
                    elif float(self.__defaultValue) > float(self.__maxValue):
                        print errorText
                        print "default value greater than max value: %s-%s (max=%s, default=%s)" % (self.__managedObject, self.__name, self.__maxValue, self.__defaultValue)
                        result = False
        if self.__paramPlanDirection != None:
            if self.__locationInGui == None:
                #print errorText
                #print "location in GUI is not defined: %s-%s" % (self.__managedObject, self.__name)
                pass #this is not mandatory field?
            else:
                if self.__managedObject == 'WCEL':
                    location = 'WCDMA Cell-dialog'
                elif self.__managedObject == 'WBTS':
                    location = 'BTS-dialog' #two variations in PDDB: 'WCDMA BTS-dialog', 'WBTS-dialog'
                else:
                    location = self.__managedObject+'-dialog'
                if self.__locationInGui.find(location) == -1: #e.g. "RNC RNW Object Browser/WCDMA BTS-dialog"
                    #print errorText
                    #print "location in GUI is incorrect: %s-%s" % (self.__managedObject, self.__name)
                    pass
        """
        if self.__paramPlanDirection != None and len(self.__bits) > 0:
            if self.__modificationType == 'unmodifiable': #all bits must be fixed
                allFixed = True
                for bit, fixed in self.__bits:
                    if fixed == False:
                        allFixed = False
                        break
                if allFixed == False:
                    print errorText
                    print "unmodifiable, but all bits are not fixed: %s-%s" % (self.__managedObject, self.__name)
                    return False
        """
        """
        if self.__defaultValue != None and self.__creationPriority == 'mandatory':
            print errorText
            print "mandatory in creation, but has default: %s-%s" % (self.__managedObject, self.__name)
            result = False
        if self.__paramPlanDirection == 'uni' and self.__creationPriority != 'Value set by the system':
            print errorText
            print "not a download parameter, but creation is not \'Value set by the system\': %s-%s" % (self.__managedObject, self.__name)
            result = False
        if self.__paramPlanDirection == 'uni' and self.__modificationType != 'unmodifiable':
            print errorText
            print "not a download parameter, but modification is not \'unmodifiable\': %s-%s" % (self.__managedObject, self.__name)
            result = False
        if self.__paramPlanDirection == 'bi' and self.__paramType == 'simpleType' and self.__creationPriority != 'mandatory' and self.__valueBase !='string' and self.__defaultValue == None:
            print errorText
            print "optional parameter, but no default value: %s-%s" % (self.__managedObject, self.__name)
            result = False
        if self.__paramPlanDirection != self.__paramGuiDirection:
            print errorText
            print "gui and plan interface definitions are different: %s-%s" % (self.__managedObject, self.__name)
            result = False
        """
            
        return result

    #
    # Set
    #


    ## \brief Set name of the parameter.
    #
    #    \param self object reference
    #    \param paramName name of the parameter (string)
    #    \return -
    def setName(self, paramName):
        self.__name = paramName


    ## \brief Set full name of the parameter.
    #
    #    \param self object reference
    #    \param paramFullName full name of the parameter (string)
    #    \return -
    def setFullName(self, paramFullName):
        self.__fullName = paramFullName


    ## \brief Set max occurs of the parameter.
    #
    #    \param self object reference
    #    \param maxOccurs max occurs of the parameter (string)
    #    \return -
    def setMaxOccurs(self, maxOccurs):
        self.__maxOccurs = maxOccurs


    ## \brief Set status of the parameter.
    #
    #    \param self object reference
    #    \param status PDDB status of the parameter (string)
    #    \return -
    def setStatus(self, status):
        self.__status = status


    ## \brief Set managed object.
    #
    #    \param self object reference
    #    \param managedObject managed object under which this parameter belongs
    #    \return -
    def setManagedObject(self, managedObject):
        self.__managedObject = managedObject


    ## \brief Set parameter location in GUI.
    #
    #    \param self object reference
    #    \param locationInGui GUI location description
    #    \return -
    def setLocationInGui(self, locationInGui):
        self.__locationInGui = locationInGui


    ## \brief Parameter has interface definition.
    #
    #    \param self object reference
    #    \return -
    def setInterface(self):
        self.__hasInterface = True


    ## \brief Set creation priority of the parameter.
    #
    #    \param self object reference
    #    \param creationPriority creation priority of the parameter (string)
    #    \return -
    def setCreationPriority(self, creationPriority):
        self.__creationPriority = creationPriority


    ## \brief Set modification type of the parameter.
    #
    #    \param self object reference
    #    \param modificationType modification type of the parameter (string)
    #    \return -
    def setModificationType(self, modificationType):
        self.__modificationType = modificationType


    ## \brief Set related features of a parameter.
    #
    #    \param self object reference
    #    \param features related features
    #    \return -
    def setFeatures(self, features):
        self.__featuresAsText = features
        self.__featuresAsText = self.__featuresAsText.replace('(optional)', '') #"HSDPA Serving Cell Change    (optional)"
        self.__featuresAsText = self.__featuresAsText.replace('(standard)', '') #"3GPP Iub    (standard) AND    BTS AAL2 Multiplexing Function    (standard)"
        self.__featuresAsBool = self.__featuresAsText
        for feature in self.__standardFeatures:
            self.__featuresAsBool = self.__featuresAsBool.replace(feature, "True")
        #print self.__featuresAsText
        #print self.__featuresAsBool


    ## \brief Set currently enabled features.
    #
    #    \param self object reference
    #    \param enabledOptions list of currently enabled options
    #    \param disabledOptions list of currently disabled options
    #    \param featureState parameter feature state as string if already known
    #    \return -
    def setUsedOptions(self, enabledOptions, disabledOptions, featureState=None):    
        #print "*** setUsedOptions", self.__managedObject, self.__name
    
        if featureState != None:
            self.__featuresAsBool = featureState
            return eval( self.__featuresAsBool )
    
        for enabledOption in enabledOptions:
            enabledOption = enabledOption.strip()
            if self.__mapOptionsToFeatures.has_key(enabledOption):
                enabledOption = self.__mapOptionsToFeatures[enabledOption]
            self.setFeatureStates(enabledOption, 'True')

        for disabledOption in disabledOptions:
            disabledOption = disabledOption.strip()
            if self.__mapOptionsToFeatures.has_key(disabledOption):
                disabledOption = self.__mapOptionsToFeatures[disabledOption]
            self.setFeatureStates(disabledOption, 'False')
        
        #print "feature enable status:", self.__name, ":", self.__featuresAsBool, '<->', self.__featuresAsText
        
        #feature can be empty in PDDB, set as True in that case
        self.__featuresAsBool =    self.__featuresAsBool.strip()
        if self.__featuresAsBool == "":
            self.__featuresAsBool = "True"
        
        #change to python 'or' and 'and'
        self.__featuresAsBool = self.__featuresAsBool.replace(' AND ', ' and ')
        self.__featuresAsBool = self.__featuresAsBool.replace(' OR ', ' or ')
        
        #both "HSDPA Layering for UEs in Common Channels" and "HSDPA layering for UEs in common channels" feature name used
        if 'HSDPA layering for UEs in common channels' in enabledOptions:
            self.__featuresAsBool = self.__featuresAsBool.replace('HSDPA Layering for UEs in Common Channels', 'True')
            self.__featuresAsBool = self.__featuresAsBool.replace('Directed RRC Connection Setup for HSDPA Layer', 'True')
        else:
            self.__featuresAsBool = self.__featuresAsBool.replace('HSDPA Layering for UEs in Common Channels', 'False')
            self.__featuresAsBool = self.__featuresAsBool.replace('Directed RRC Connection Setup for HSDPA Layer', 'False')
        
        #option "Dual" Iub can be feature "Dual Iub for Ultrasite WCDMA BTS" or "Dual Iub for Flexi WCDMA BTS"
        if 'Dual Iub' in enabledOptions:
            self.__featuresAsBool = self.__featuresAsBool.replace('Dual Iub for Ultrasite WCDMA BTS', 'True')
        else:
            self.__featuresAsBool = self.__featuresAsBool.replace('Dual Iub for Ultrasite WCDMA BTS', 'False')
        
        #option "IP Based Iub" can be feature "IP Based Iub for Ultrasite WCDMA BTS" or "IP Based Iub for Flexi WCDMA BTS"
        if 'IP Based Iub' in enabledOptions:
            self.__featuresAsBool = self.__featuresAsBool.replace('IP Based Iub for UltraSite WCDMA BTS', 'True')
        else:
            self.__featuresAsBool = self.__featuresAsBool.replace('IP Based Iub for UltraSite WCDMA BTS', 'False')
        
        #LCSShapeConversion parameter: "LCS Shape Conversion"     AND    "Point-to-Point Iu-pc Interface"
        #if 'LCS Shape Conversion' in enabledOptions:
        #    #self.__featuresAsBool = self.__featuresAsBool.replace('Point-to-Point Iu-pc Interface', 'True')
        #    self.__featuresAsBool = self.__featuresAsBool.replace('PCAP Position Calculation procedure for Cell-ID Measurement Method', 'True')
        #else:
        #    #self.__featuresAsBool = self.__featuresAsBool.replace('Point-to-Point Iu-pc Interface', 'False')
        #    self.__featuresAsBool = self.__featuresAsBool.replace('PCAP Position Calculation procedure for Cell-ID Measurement Method', 'False')
     
        #RNC Co-site
        self.__featuresAsBool = self.__featuresAsBool.replace('RNC co-siting', 'True')

        #SRVCC from LTE
        if 'LTE Interworking-ISHO from LTE' in enabledOptions:
            self.__featuresAsBool = self.__featuresAsBool.replace('SRVCC from LTE and CSFB with HO', 'True')
            self.__featuresAsBool = self.__featuresAsBool.replace('SRVCC from LTE', 'True')
        else:
            self.__featuresAsBool = self.__featuresAsBool.replace('SRVCC from LTE and CSFB with HO', 'False')
            self.__featuresAsBool = self.__featuresAsBool.replace('SRVCC from LTE', 'False')

        #HS-RACH (RAN1913) and HS-FACH (RAN1637) use the same option
        #so option HS-FACH equals features 'High speed Cell_FACH' and 'High speed Cell_FACH DL')
        if 'HS-FACH' in enabledOptions:
            self.__featuresAsBool = self.__featuresAsBool.replace('High speed Cell_FACH', 'True')
        else:
            self.__featuresAsBool = self.__featuresAsBool.replace('High speed Cell_FACH', 'False')

        #mcRNC RncOptions does not contain these options, but they are always activated
        if not 'IP based IU-CS' in enabledOptions + disabledOptions:
            self.__featuresAsBool = self.__featuresAsBool.replace('IP based Iu-CS', 'True')
        if not 'IP based IU-PS' in enabledOptions + disabledOptions:
            self.__featuresAsBool = self.__featuresAsBool.replace('IP based Iu-PS', 'True')
        if not 'IP based Iur' in enabledOptions + disabledOptions:
            self.__featuresAsBool = self.__featuresAsBool.replace('IP Based Iur', 'True')        

        #missing from RncOptions in some older PDDB reports
        if not 'RNC2600 Capacity Increase for Smartphones' in enabledOptions + disabledOptions:
            self.__featuresAsBool = self.__featuresAsBool.replace('RNC2600 Capacity Increase for Smartphones', 'True')

        #PRFILE controlled features - assume these are all enabled, not visible in RncOptions
        #
        #class 2 - option 1815 (HSUPA Interference Cancellation)
        #class 2 - option 2018 (HSUPA BLER)
        #class 2 - option 2039 (Fast Cell_PCH Switching)
        self.__featuresAsBool = self.__featuresAsBool.replace('HSUPA Interference Cancellation Receiver', "True")
        #self.__featuresAsBool = self.__featuresAsBool.replace('Fast Cell_PCH Switching', 'True')

        #FIFILE controlled features - assume these are all enabled, not visible in RncOptions
        #
        #class 55 - feature 3 (EMERGENCY_CALL_ISHO_SUP)
        #class 55 - feature 12 (INT_EMERG_CALL_ISHO_SUP)
        #class 55 - feature 15 (IUPC_INTERFACE)
        self.__featuresAsBool = self.__featuresAsBool.replace('Directed Emergency Call Inter-System Handover', 'True')
        self.__featuresAsBool = self.__featuresAsBool.replace('Point-to-Point Iu-pc Interface', 'True')

        if 'HSDPA Mob, SHO, SCC and Soft/softer HO for DPCH' in enabledOptions:
            self.__featuresAsBool = self.__featuresAsBool.replace('HSDPA Soft/softer Handover for Associated DPCH', 'True')
            self.__featuresAsBool = self.__featuresAsBool.replace('HSDPA Serving Cell Change', 'True')
        else:
            self.__featuresAsBool = self.__featuresAsBool.replace('HSDPA Soft/softer Handover for Associated DPCH', 'False')
            self.__featuresAsBool = self.__featuresAsBool.replace('HSDPA Serving Cell Change', 'False')

        #parameter can be related to general HSDPA features, special case
        #Note: anything containing this string will be replaced, might be problematic!
        if 'HSDPA, ChSw, UL DPCHSch, ResumpT and DirRRCConSetu' in enabledOptions:
            self.__featuresAsBool = self.__featuresAsBool.replace('HSDPA with QPSK and 5 Codes', 'True')
            self.__featuresAsBool = self.__featuresAsBool.replace('Basic HSDPA with QPSK and 5 codes', 'True')
            self.__featuresAsBool = self.__featuresAsBool.replace('HSDPA Associated Uplink DPCH Scheduling', 'True')
            self.__featuresAsBool = self.__featuresAsBool.replace('HSDPA Resource Allocation', 'True')
            self.__featuresAsBool = self.__featuresAsBool.replace('HSDPA Channel Switching', 'True')
            self.__featuresAsBool = self.__featuresAsBool.replace('HSDPA Transport with Best Effort AAL2 QoS', 'True')
            self.__featuresAsBool = self.__featuresAsBool.replace('HSDPA', "True")
        else:
            self.__featuresAsBool = self.__featuresAsBool.replace('HSDPA with QPSK and 5 Codes', 'False')
            self.__featuresAsBool = self.__featuresAsBool.replace('Basic HSDPA with QPSK and 5 codes', 'False')
            self.__featuresAsBool = self.__featuresAsBool.replace('HSDPA Associated Uplink DPCH Scheduling', 'False')
            self.__featuresAsBool = self.__featuresAsBool.replace('HSDPA Resource Allocation', 'False')
            self.__featuresAsBool = self.__featuresAsBool.replace('HSDPA Channel Switching', 'False')
            self.__featuresAsBool = self.__featuresAsBool.replace('HSDPA Transport with Best Effort AAL2 QoS', 'False')
            self.__featuresAsBool = self.__featuresAsBool.replace('HSDPA', 'False')
            
        #parameter can be related to "HSUPA" feature, special case
        if 'HSUPA Basic 3 users per BTS' in enabledOptions or \
             'HSUPA Basic 12 users per BTS' in enabledOptions or \
             'HSUPA Basic 24 users per BTS' in enabledOptions or \
             'HSUPA Basic 60 users per BTS' in enabledOptions:
            self.__featuresAsBool = self.__featuresAsBool.replace('HSUPA Basic RRM', 'True')
            self.__featuresAsBool = self.__featuresAsBool.replace('HSUPA Handovers', 'True')
            self.__featuresAsBool = self.__featuresAsBool.replace('HSUPA Congestion Control', 'True')
            self.__featuresAsBool = self.__featuresAsBool.replace('HSUPA', 'True')
        else:
            self.__featuresAsBool = self.__featuresAsBool.replace('HSUPA Basic RRM', 'False')
            self.__featuresAsBool = self.__featuresAsBool.replace('HSUPA Handovers', 'False')
            self.__featuresAsBool = self.__featuresAsBool.replace('HSUPA Congestion Control', 'False')
            self.__featuresAsBool = self.__featuresAsBool.replace('HSUPA', 'False')

        if 'Inter-frequency Handover over Iur' in enabledOptions or \
             'IFHO Over Iur' in enabledOptions:
            self.__featuresAsBool = self.__featuresAsBool.replace('Inter-frequency Handover over Iur', 'True')
            self.__featuresAsBool = self.__featuresAsBool.replace('IFHO Over Iur', 'True')    
        #now string should contain logic expression - only and, or, True, False and paranthesis
        if self.getParamPlanDirection() != None: #parameter belongs to RNW plan
            try:
                return eval( self.__featuresAsBool )
            except (NameError, SyntaxError):
                print ERROR_MSG
                print "can't eval enabled options:", self.__featuresAsBool
                print "features as string:", self.__featuresAsText
                print "parameter: %s-%s" % (self.__managedObject, self.__name)
                sys.exit()
            

    ## \brief Set parameter type of the parameter ('simple' or 'complex').
    #
    #    \param self object reference
    #    \param paramType type of the parameter (string)
    #    \return -
    def setParamType(self, paramType):
        self.__paramType = paramType


    ## \brief Set value base of the parameter.
    #
    #    \param self object reference
    #    \param valueBase value base of the parameter (string)
    #    \return -
    def setValueBase(self, valueBase):
        self.__valueBase = valueBase


    ## \brief Set divisor of the parameter for UI->plan value conversion.
    #
    #    \param self object reference
    #    \param divisor divisor of the parameter (string)
    #    \return -
    def setDivisor(self, divisor):
        self.__divisor = divisor


    ## \brief Set shift of the parameter for UI->plan value conversion.
    #
    #    \param self object reference
    #    \param shift shift of the parameter (string)
    #    \return -
    def setShift(self, shift):
        self.__shift = shift


    ## \brief Set multiplicand of the parameter for UI->plan value conversion.
    #
    #    \param self object reference
    #    \param multiplicand multiplicand of the parameter (string)
    #    \return -
    def setMultiplicand(self, multiplicand):
        self.__multiplicand = multiplicand


    ## \brief Set mimimun value of the parameter.
    #
    #    \param self object reference
    #    \param minValue min value of the parameter (string)
    #    \return -
    def setMinValue(self, minValue):
        self.__minValue = minValue


    ## \brief Set maximun value of the parameter.
    #
    #    \param self object reference
    #    \param maxValue max value of the parameter (string)
    #    \return -
    def setMaxValue(self, maxValue):
        self.__maxValue = maxValue


    ## \brief Set value step of the parameter.
    #
    #    \param self object reference
    #    \param step value step of the parameter (string)
    #    \return -
    def setStep(self, step):
        self.__valueStep = step


    ## \brief Add enumeration numericvalue of the parameter.
    #
    #    \param self object reference
    #    \param enum single enum value of the parameter (string)
    #    \return -
    def addEnumerationValue(self, enum):
        self.__enumerationValues.append(enum)


    ## \brief Add enumeration text value of the parameter.
    #
    #    \param self object reference
    #    \param enum single enum value
    #    \param text single enum text value
    #    \return -
    def addEnumerationText(self, enum, text):
        self.__enumerationTexts[enum] = text


    ## \brief Add bit value of the parameter.
    #
    #    \param self object reference
    #    \param default bit default value
    #    \param fixed is bit fixed
    #    \return -
    def addBitValue(self, default, fixed):
        self.__bits.insert(0, (default, fixed)    ) #list of tuples, insert highest bits as first


    ## \brief Set special value of the parameter.
    #
    #    \param self object reference
    #    \param specialValue special value of the parameter (string)
    #    \return -
    def setSpecialValue(self, specialValue):
        self.__specialValue = specialValue


    ## \brief Set names of child parameters of the parameter.
    #
    #    \param self object reference
    #    \param childParamList list of child parameter names of this parameter (as string)
    #    \return -
    def setChildParams(self, childParamList):
        self.__childParams = childParamList


    ## \brief Set name of the parent parameter of this parameter.
    #
    #    \param self object reference
    #    \param parentParam name of the parent parameter of this parameter (as string)
    #    \return -
    def setParentParam(self, parentParam):
        self.__parentParam = parentParam


    ## \brief Set default value of the parameter.
    #
    #    \param self object reference
    #    \param defaultValue default value of the parameter (as string)
    #    \return -
    def setDefaultValue(self, defaultValue):
        self.__defaultValue = defaultValue


    ## \brief Set parameter direction in plan (upload, download or both).
    #
    #    \param self object reference
    #    \param direction parameter plan direction ('bi' or 'uni')
    #    \return -
    def setPlanDirection(self, direction):
        self.__paramPlanDirection = direction


    def setInternalValue(self, internalValue):
        self.__internalValue = internalValue

    def setInterfaceDirection(self, direction):
        self.__paramInterfaceDirection = direction
        
    ## \brief Set that parameter belongs to download direction.
    #
    #    \param self object reference
    #    \param direction parameter gui direction ('bi' or 'uni')
    #    \return -
    def setGuiDirection(self, direction):
        self.__paramGuiDirection = direction


    ## \brief Set enabled and disabled features.
    #
    #    \param self object reference
    #    \param featureName parameter related feature name
    #    \param featureState "True" or "False" as string
    #    \return -
    def setFeatureStates(self, featureName, featureState):        
        startIndex = 0
        found = False
        features = ""
        featureIndexes = []
        for m in re.finditer(' AND | OR ', self.__featuresAsBool): #find every and/or
            found = True
            endIndex = m.start() - 1
            #print "matches found:", startIndex, endIndex, self.__featuresAsBool[startIndex:endIndex]
            featureIndexes.append( (startIndex, endIndex) )
            startIndex = m.end()
        if found:
            featureIndexes.append( (startIndex, -1) ) #add the last feature after and/or
            featureIndexes.reverse() #replace starting from the end, so that first string indexes remain valid
            for start, end in featureIndexes:
                if self.__featuresAsBool[start:end].strip() == 'True' or self.__featuresAsBool[start:end].strip() == 'False':
                    continue #string already replaced to boolean value
                #find feature names, skip parenthesis
                feaStart = self.__featuresAsBool[start:end].rfind('(') #search from the right
                feaEnd = self.__featuresAsBool[start:end].find(')')                    
                if feaStart == -1:
                    feaStart = start
                else:
                    feaStart = start + feaStart + 1
                if feaEnd == -1:
                    feaEnd = end
                else:
                    feaEnd = end + feaEnd - 1
                    
                #exceptions:
                #1) paranthesis are not part of boolean expression: "AMR Codec Sets (12.2, 7.95, 5.90, 4.75) and (5.90, 4.75)"
                #2) paranthesis in "(RTT)" are not part of boolean expression: "LCS - Cell Coverage Based (RTT) with Geographical Coordinates AND    LCS Support in Drift RNC"
                #3) paranthesis are not part of boolean expression: Extended Cell (35 km)
                if feaStart != -1 and (self.__featuresAsBool[start:end].find(', ') != -1 or self.__featuresAsBool[start:end].find('(RTT)') != -1 or self.__featuresAsBool[start:end].find('km)') != -1):
                    feaStart = start
                    feaEnd = end
                    
                #print "feaStart, feaEnd:", feaStart, feaEnd, ":", self.__featuresAsBool[feaStart:feaEnd]
                #print "expected feature:", featureName
                if self.__featuresAsBool[feaStart:feaEnd].strip() == featureName.strip():
                    self.__featuresAsBool = self.__featuresAsBool[:feaStart] + " " + featureState + " " + self.__featuresAsBool[feaEnd:]

            #print "features now:", self.__featuresAsBool
        else: #no 'and', 'or' in feature name, so just a single feature
            #print "single feature found"
            if self.__featuresAsBool.strip() == featureName.strip():
                self.__featuresAsBool = self.__featuresAsBool.replace(featureName, featureState)
            else:
                #print "mismatch:", self.__featuresAsBool, "<->", featureName
                pass
             
             
    # Get


    ## \brief Get parameter plan value.
    #
    #    \param self object reference
    #    \param paramValue wanted value (PARAM_VALUE_MIN, PARAM_VALUE_MAX, PARAM_VALUE_DEFAULT)
    #    \return parameter value
    def getParamValue(self, paramValue):
        if paramValue == PARAM_VALUE_MIN:
            if self.__valueBase == 'decimal':
                value = int( ( ( (float(self.__minValue) - float(self.__shift)) * int(self.__divisor)) / int(self.__multiplicand) ) )
                return str(value)
            elif self.__valueBase == 'integer':
                if self.__bits == []:
                    return str(self.__enumerationValues[0])
                else:
                    bitmap = '0b'
                    for i in range( len(self.__bits) ):
                        default, fixed = self.__bits[i]
                        if fixed == 'true':
                            bitmap = bitmap + default
                        else:
                            bitmap = bitmap + '0' #min bit value whenever possible
                    #print "min bitmap:", self.__name, bitmap
                    return str(int(bitmap, 2))                    
            elif self.__valueBase == 'string':
                value = ""
                for i in range( int(self.__minValue) ):
                    value += '1'
                return value
            return str(self.__minValue)
        elif paramValue == PARAM_VALUE_MAX:
            if self.__valueBase == 'decimal':
                value = int( ( ( (float(self.__maxValue) - float(self.__shift)) * int(self.__divisor)) / int(self.__multiplicand) ) )
                return str(value)
            elif self.__valueBase == 'integer':
                if self.__bits == []:
                    return str(self.__enumerationValues[-1])
                else:
                    bitmap = '0b'
                    for i in range( len(self.__bits) ):
                        default, fixed = self.__bits[i]
                        if fixed == 'true':
                            bitmap = bitmap + default
                        else:
                            bitmap = bitmap + '1' #max bit value whenever possible
                    return str(int(bitmap, 2))
            elif self.__valueBase == 'string':
                value = ""
                for i in range( int(self.__maxValue) ):
                    value += '1'
                return value
            return str(self.__maxValue)
        elif paramValue == PARAM_VALUE_DEFAULT:
            if self.__defaultValue == None:
                if self.__valueBase == 'string' and self.__creationPriority == 'optional': #e.g. CellAdditionalInfo
                    return ''
                return None
            else:
                if self.__valueBase == 'decimal': #do value conversion if needed
                    #if default value is as below, it must not be modified with divisor/multiplicand, but used in plan as such
                    if self.__specialValue != None and self.__specialValue == self.__defaultValue:
                        value = self.__defaultValue
                    else:
                        value = int( ( ( (float(self.__defaultValue) - float(self.__shift)) * int(self.__divisor)) / int(self.__multiplicand) ) )
                    return str(value)
                else:         
                    return str(self.__defaultValue)
        else:
            print "getParamValue: unknown value requested -", self.__name, paramValue
            sys.exit(1)


    ## \brief Get special value of the parameter.
    #
    #    \param self object reference
    #    \return specialValue special value of the parameter (string)
    def getSpecialValue(self):
        return self.__specialValue


    ## \brief Get name of the parameter.
    #
    #    \param self object reference
    #    \return name of the parameter
    def getName(self):
        return self.__name


    ## \brief Get full name of the parameter.
    #
    #    \param self object reference
    #    \return full name of the parameter
    def getFullName(self):
        return self.__fullName


    ## \brief Get max occurs of the parameter.
    #
    #    \param self object reference
    #    \return max occurs of the parameter
    def getMaxOccurs(self):
        return int(self.__maxOccurs)


    ## \brief Get PDDB status of the parameter.
    #
    #    \param self object reference
    #    \return status of the parameter
    def getStatus(self):
        return self.__status


    ## \brief Get creation priority of the parameter.
    #
    #    \param self object reference
    #    \return creation priority of the parameter
    def getCreationPriority(self):
        return self.__creationPriority


    ## \brief Get modification type of the parameter.
    #
    #    \param self object reference
    #    \return modification type of the parameter
    def getModificationType(self):
        return self.__modificationType


    ## \brief Get parameter type of the parameter.
    #
    #    \param self object reference
    #    \return param type ('simpleType' or 'complexType')
    def getParamType(self):
        return self.__paramType


    ## \brief Get value base of the parameter.
    #
    #    \param self object reference
    #    \return value base
    def getValueBase(self):
        return self.__valueBase


    ## \brief Get parameter child parameters.
    #
    #    \param self object reference
    #    \return list of child parameters
    def getChildParams(self):
        return self.__childParams


    ## \brief Get parent parameter name of this parameter.
    #
    #    \param self object reference
    #    \return parent parameter name or None
    def getParentParam(self):
        return self.__parentParam


    ## \brief Get interface status in PDDB.
    #
    #    \param self object reference
    #    \return True/False is interface defined or not
    def getInterface(self):
        return self.__hasInterface


    ## \brief Get default value.
    #
    #    \param self object reference
    #    \return default value as string or None
    def getDefaultValue(self):
        return self.__defaultValue


    ## \brief Get enumeration text value
    #
    #    \param self object reference
    #    \param enum single enum value
    #    \return list of enum text values
    def getEnumerationTextValue(self, enum):
        return self.__enumerationTexts[enum]


    ## \brief Get all enumeration text values as list
    #
    #    \param self object reference
    #    \return list of enum text values
    def getEnumerationTextValues(self):
        enumTextValues = []
        for enum in self.__enumerationValues:
            enumTextValues.append( self.getEnumerationTextValue(enum) )
        return enumTextValues


    def getFeatureAsText(self):
        return self.__featuresAsText
    
    def getFeatureAsBool(self):
        return self.__featuresAsBool


    ## \brief Get parameter option status
    #
    #    \param self object reference
    #    \return True of False - should parameter be included in plan or not
    def getParamOptionStatus(self):
        #print "***", self.__managedObject, self.__name, self.__parentParam, self.__featuresAsText, self.__featuresAsBool
        try:
            optionStatus = eval( self.__featuresAsBool )
        except:
            optionStatus = False
            print "Feature not enabled", self.__managedObject, self.__name, self.__parentParam, self.__featuresAsText, self.__featuresAsBool
        return optionStatus
    

    ## \brief Get features of parameter as text
    #
    #    \param self object reference
    #    \return features as text
    def getFeatures(self):
        return self.__featuresAsText


    ## \brief Is object ID parameter
    #
    #    \param self object reference
    #    \return True or False
    def isIdParameter(self):
        if self.__name == self.__managedObject+ 'Id' or self.__name == self.__managedObject+ 'id' or self.__name == self.__managedObject+ 'ID' or self.__name == 'LcrId' or \
             self.__name == 'RncId' or self.__name == 'SubscriberGroupId' or self.__name == 'AuthorisedNetworkId' or self.__name == self.__managedObject+ 'Identifier':
            return True
        return False
    

    ## \brief Check if parameter value is legal or illegal
    #
    #    \param self object reference
    #    \param planValue parameter plan value
    #    \return "" (legal) or "<error text>" (illegal)
    def isValidValue(self, planValue):
        if planValue == None:
            return ''
        planValue = planValue.strip()
        if planValue == "":
            return ''
        if self.__valueBase == 'decimal':
            if self.__specialValue != None:
                if int(planValue) == int(self.__specialValue): #no calculation rules for special value, gui value == plan value
                    return ''
            guiValue = float( float(planValue) * float(self.__multiplicand) / float(self.__divisor) + float(self.__shift) )
            if    float(guiValue) < float(self.__minValue) or float(guiValue) > float(self.__maxValue):
                return 'out of range'
        elif self.__valueBase == 'integer':
            if self.__enumerationValues != []: #enum
                if not planValue in self.__enumerationValues:
                    return 'invalid enum'
            else: #bitmap
                bits = bin( int(planValue) ).lstrip('-0b') #e.g. "57" => 57 => 0b111001 => 111001
                if len(bits) > len(self.__bits):
                    return 'extra bits'
                elif len(bits) < len(self.__bits):
                    bits = bits.zfill( len(self.__bits) ) #add missing leading zeros
                #print self.__name, bits, len(bits), len(self.__bits)                
                for i in range( len(bits) ):
                    default, fixed = self.__bits[i]
                    if fixed == 'true' and bits[i] != default:
                        print bits, self.__bits
                        return 'wrong fixed bit %d value' % i
        #check string length
        elif self.__valueBase == 'string':
            if len(planValue) < int(self.__minValue):
                return 'string too short'
            elif len(planValue) > int(self.__maxValue):
                return 'string too long'
        return ''


    #
    # Private methods
    #

#endif