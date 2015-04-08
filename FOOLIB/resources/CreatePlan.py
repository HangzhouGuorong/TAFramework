## @package CMtools
#    Tools for CM testing.
#    \file CreatePlan.py

#ifndef _CREATE_PLAN_
#define _CREATE_PLAN_

import xml.dom.minidom as dom
import os, sys
from time import strftime

import PDDBData
from Definitions import *
from Common import *


## Create RNW test plans from PDDB metadata.
#
# Generate creation, modification or deletion test RNW plans.
class CreatePlan:

    ## \brief The constructor.
    #
    #    \param self object reference
    #    \param pddbData instance of PDDBData class
    #    \param uploadPlan upload plan file name
    #    \param excludedObjects list of PDDB objects excluded from plan generation
    #    \param neId network element ID used in managed object IDs in generated plan
    #    \return -
    def __init__(self, pddbData, uploadPlan, excludedObjects, neId):
        self.__pddbData = pddbData #PDDB definitions
        self.__uploadPlan = uploadPlan #upload plan from where to check enabled options
        self.__excludedObjects = excludedObjects #objects not tested
        self.__enabledOptionsEnum = [] #enabled options (as integers)
        self.__enabledOptionsText = [] #enabled options (as text)
        self.__neId = neId
        self.__isAda = False
        self.__resultDoc = None
        self.__cmdataNode = None
        self.__failed = False
        self.__objectsAdded = 0
        self.__paramsAdded = 0
                
        #these S-NB parameter are not included in upload plan, if WBTS type is N-NB
        self.__snbParameters = ['BlindTFdetectionUsage', 'DCHnumberRL', 'MaxDCHuserRateRLDL', 'MaxDCHuserRateRLUL', 'HSDPAMPO' , 'NonHSEventECommMeas', \
                                                        'PrxTotalReportPeriod', 'PtxOffsetHSSCCH', 'PtxTotalReportPeriod', 'RACHloadReportPeriod', 'RSEPSEventECommMeas', \
                                                        'RTWPEventECommHyst', 'RTWPEventECommMeas', 'RTWPMeasFilterCoeff', 'TCPEventECommHyst', 'TCPEventECommMeas', 'TCPMeasFilterCoeff']
        #RNC_EFS_2077_1904_121 RNW object order in RNC
        self.__rncObjects = ['RNC', 'RNAC', 'RNPS', 'RNHSPA', 'RNRLC', 'RNTRM', 'RNMOBI', 'RNFC', 'RNCERM', 'COSITE', 'COSRNC', 'CBCI', 'IUO', 'IPQM', 'IUCS', 'IUCSIP', 'IUPS', 'IUPSIP', \
                                                 'IUR', 'CMOB', 'COCO', 'IPNB', 'PREBTS', 'PFL', 'FMCS', 'FMCI', 'FMCG', 'FMCL', 'HOPS', 'HOPI', 'HOPG', 'HOPL', 'TQM', 'WRAB', 'WAC', 'VBTS', 'VCEL', 'WBTS', \
                                                 'WCEL', 'ADJS', 'ADJI', 'ADJG', 'ADJL', 'ADJD', 'ADJE', 'WSMLC', 'WLCSE', 'WANE', 'WSG', 'RNCSRV', 'BKPRNC', 'PRNC', 'DATSYN', 'WDEV']
        #RNC_EFS_2077_1904_127 RNW object order in ADA:
        self.__adaObjects = ['IADA', 'RNAC', 'RNPS', 'RNHSPA', 'RNRLC', 'RNTRM', 'RNMOBI', 'RNFC', 'CBCI', 'IUO', 'IPQM', 'TQM', 'IUCS', 'IUPS', 'IUCSIP', 'IUPSIP', 'IUR', \
                                                 'CMOB', 'IPNB', 'WRAB', 'WAC', 'HOPS', 'HOPI', 'HOPG', 'HOPL', 'FMCS', 'FMCI', 'FMCG', 'PFL', 'WBTS', 'WCEL', 'VBTS', 'VCEL', 'ADJS', 'ADJI', 'ADJG', \
                                                 'ADJD', 'ADJL', 'WSMLC', 'WLCSE', 'WANE', 'WSG']

        #check enabled options
        if self.__uploadPlan != None:
            self.__uploadPlanDoc = dom.parse(self.__uploadPlan)
            managedObjects = self.__uploadPlanDoc.documentElement.getElementsByTagName('managedObject')
            self.__enabledOptionsText, neId, self.__isAda = getRncOptions(self.__uploadPlanDoc, self.__pddbData, self.__uploadPlan)
            self.__pddbData.setOptions(self.__enabledOptionsText, self.__isAda)
        #set managed objects under test
        if self.__isAda:        
            self.__managedObjects = self.__adaObjects
        else:
            self.__managedObjects = self.__rncObjects
        #object order may contain new objects that are not yet present in PDDB of this (oldser) SW packet,
        #remove those objects silently
        #for example: WAC object appeared in R_QFCB.11.41.0_4, but is not present in previous packets
        deletedMOs = []
        for mo in self.__managedObjects:
            #print "looping mo:", mo
            if not mo in self.__pddbData.getManagedObjectList():
                #print "*** removing:", mo
                #self.__managedObjects.remove(mo)
                deletedMOs.append(mo)
        for deletedMO in deletedMOs:
            self.__managedObjects.remove(deletedMO)
        if len(self.__managedObjects) != len( self.__pddbData.getManagedObjectList() ):
            diff = list(set(self.__pddbData.getManagedObjectList()).difference(set(self.__managedObjects)))
            if len(diff) == 1 and diff[0] == 'RNCOPT':
                pass #RNCOPT is upload direction object only, don't need to know place in download plan
            else:
                print ERROR_MSG
                print "new objects in PDDB, missing from the script: %d <=> %d" % (len(self.__managedObjects), len(self.__pddbData.getManagedObjectList()))
                print self.__managedObjects
                print self.__pddbData.getManagedObjectList()
                print "difference:", diff
                sys.exit()
                                                 
        self.__createParams = {} #parameters that don't have default value or non-default value is used in creation
        self.__modifyMaxParams = {} #parameters that can't be set to PDDB max values
        self.__createParams['RNC'] = { 'SecOMSIpAddress':'10.10.10.10',    'OMSIpAddress':'11.11.11.11', 'RNCName':'RNC-'+self.__neId }
        self.__createParams['IADA'] = self.__createParams['RNC'] #ADA specific
        self.__createParams['RNTRM'] = { 'A2EA':'1234567890' }
        self.__createParams['COSRNC'] = { 'IPBasedRouteIdRNCcl1':'1', 'IPBasedRouteIdRNCcl2':'2' }
        self.__createParams['IUO'] = { 'MCC':'520', 'MNC':'18', 'MNCLength':'2' }
        self.__createParams['CBCI'] = { 'CBCIPaddress':'1.1.1.1', 'MCC':'520', 'MNC':'18', 'IUOIdentifier':'1' }
        self.__createParams['IUCS'] = { 'CNDomainVersion':'6', 'CNId':'1', 'MCC':'520', 'MNC':'18', 'NetworkInd':'8', 'SignPointCode':'1', 'IUOIdentifier':'1' }
        self.__createParams['IUCSIP'] = { 'DestIPAddressCS':'12.12.12.12', 'IPBasedRouteIdCS':'1', 'IPNetmaskCS':'255.255.255.0', 'IPQMIdCS':'1'}
        self.__createParams['IUPS'] = { 'CNDomainVersion':'6', 'CNId':'2', 'MCC':'520', 'MNC':'18', 'NetworkInd':'8', 'SignPointCode':'2', 'IUOIdentifier':'1' }
        self.__createParams['IUPSIP'] = { 'DestIPAddressPS':'13.13.13.13', 'IPBasedRouteIdPS':'2', 'IPNetmaskPS':'255.255.255.0', 'IPQMIdPS':'1' }
        self.__createParams['IUR'] = { 'NRncId':'2', 'NRncNetworkInd':'8', 'NRncSignPointCode':'3', 'MCC':'520', 'MNC':'18', 'ADAURAId':'1', 'IPBasedRouteIdIur':'1', 'NRncVersion':'5' }
        self.__createParams['CMOB'] = { 'RestrictionGroupType':'3' }
        self.__createParams['BKPRNC'] = { 'BackUpRNCIP4Address':'14.14.14.14' }
        self.__createParams['COCO'] = { 'AAL2SigCDVT01Egr':'1', 'AAL2SigCDVT01Ing':'1', 'AAL2SigPCR01Egr':'1', 'AAL2SigPCR01Ing':'1', 'AAL2SignLinkATMIfId':'1', 'AAL2SignLinkTPId':'1', \
                                                                        'AAL2SignLinkVCI':'1', 'AAL2SignLinkVPI':'1', 'AAL2PathId':'1', 'AAL2SignLinkATMIfId':'1', 'AAL2SignLinkVCI':'2', 'AAL2SignLinkVPI':'1', \
                                                                        'AAL2UPATMIfId':'1', 'AAL2UPCDVT01Egr':'1', 'AAL2UPCDVT01Ing':'1', 'AAL2UPPCR01Egr':'1', 'AAL2UPPCR01Ing':'1', 'AAL2UPVCI':'3', 'AAL2UPVPI':'1', \
                                                                        'COCOA2EA':'1', 'WAMId':'1', 'CNBAPCDVT01Egr':'1', 'CNBAPCDVT01Ing': '1', 'CNBAPPCR01Egr':'1', 'CNBAPPCR01Ing':'1', 'CNBAPTPATMIfId':'1', \
                                                                        'CNBAPVCI':'4', 'CNBAPVPI':'1', 'CControlPortID':'1', 'DNBAPATMIfId':'1', 'DNBAPCDVT01Egr':'1', 'DNBAPCDVT01Ing':'1', 'DNBAPPCR01Egr':'1', \
                                                                        'DNBAPPCR01Ing':'1', 'DNBAPVCI':'5', 'DNBAPVPI':'1', 'COCOVPI':'1', 'VPLTPATMIfId':'1', 'VPLTPCDVT01Egr':'1', 'VPLTPPCR01Egr':'1' }
        self.__createParams['IPNB'] = { 'CControlPortID':'1', 'MinSCTPPortIub':'49152', 'NodeBIPAddress':'1.2.3.4', 'VRF':'1', 'NBAPCSPUIndex':'0', 'NBAPEIPUIndex':'0', 'NBAPQNIUBIndex':'0' }
        self.__createParams['PREBTS'] = { 'AutoConnHWID':'12345', 'AutoConnSiteID':'7890', 'BTSID':'1', 'TechnologyInformation':'3' }
        self.__createParams['VBTS'] = { 'IHSPAadapterId':'1', 'ServingRNCId':'1' }
        self.__createParams['RNCERM'] = { 'WBTSId':'1' }
        self.__createParams['VCEL'] = { 'EbNoSetIdentifier':'1', 'LAC':'1', 'RAC':'0' }
        self.__createParams['WBTS'] = { 'BTSAdditionalInfo':'WBTS-SITE-1', 'COCOId':'1', 'NBAPCommMode':'0', 'WBTSName':'WBTS', 'R99OperatorWeight':'0', 'PWSMAVTrafficVERLogic':'0' }
        self.__createParams['WCEL'] = { 'CId':'1', 'CellAdditionalInfo':'WCEL-1', 'CellRange':'100', 'EbNoSetIdentifier':'1', 'LAC':'1', \
                                                                        'PriScrCode':'1', 'RAC':'0', 'SAC':'0', 'Tcell':'0', 'UARFCN':'10650', 'URAId':'1', 'WCELMCC':'520', 'WCELMNC':'18' }
        self.__createParams['ADJS'] = { 'AdjsCI':'2', 'AdjsCPICHTxPwr':'330', 'AdjsLAC':'2', 'AdjsMCC':'520', 'AdjsMNC':'18', 'AdjsRAC':'1', 'AdjsRNCid':'2', 'AdjsScrCode':'10', \
                                                                        'AdjsTxPwrRACH':'21', 'HSDPAHopsIdentifier':'1', 'NrtHopsIdentifier':'1', 'RTWithHSDPAHopsIdentifier':'1', 'RtHopsIdentifier':'1' }
        self.__createParams['ADJI'] = { 'AdjiCI':'10', 'AdjiCPICHTxPwr':'330', 'AdjiLAC':'1', 'AdjiMCC':'520', 'AdjiMNC':'18', 'AdjiRAC':'1', 'AdjiRNCid':'2', 'AdjiScrCode':'1', \
                                                                        'AdjiTxPwrDPCH':'24', 'AdjiTxPwrRACH':'21', 'AdjiUARFCN':'10750', 'NrtHopiIdentifier':'1', 'RtHopiIdentifier':'1' }
        self.__createParams['ADJG'] = { 'AdjgBCC':'0', 'AdjgBCCH':'0', 'AdjgBandIndicator':'0', 'AdjgCI':'1', 'AdjgLAC':'1', 'AdjgMCC':'520', 'AdjgMNC':'18', \
                                                                        'AdjgNCC':'0', 'AdjgTxPwrMaxRACH':'23', 'AdjgTxPwrMaxTCH':'23', 'NrtHopgIdentifier':'1', 'RtHopgIdentifier':'1' }
        self.__createParams['ADJL'] = { 'AdjLEARFCN':'10000' }
        self.__createParams['ADJD'] = { 'AdjdCI':'20', 'AdjdCPICHTxPwr':'330', 'AdjdLAC':'1', 'AdjdMCC':'520', 'AdjdMNC':'18', 'AdjdNRTHopsId':'1', 'AdjdRAC':'1', 'AdjdRNCId':'2', \
                                                                        'AdjdRTHopsId':'1', 'AdjdScrCode':'2', 'AdjdHSDPAHopsId':'1', 'AdjdRTWithHSDPAHopsId':'1' }
        self.__createParams['ADJE'] = { 'AdjLIdentifier':'1', 'AdjeCellId':'1', 'AdjeENodeBId':'1', 'AdjeMCC':'1', 'AdjeMNC':'1', 'AdjePhysicalCellId':'1', 'AdjeTAC':'1' }									
        self.__createParams['WSMLC'] = { 'ConfAreaLevel':'50' }
        self.__createParams['WLCSE'] = { 'AntBearing':'0', 'AntennaCoordAltitudeGround':'0', 'AntennaCoordLatitudeDegrees':'0', 'AntennaCoordLatitudeFractions':'0', \
                                                                         'AntennaCoordLatitudeMinutes':'0', 'AntennaCoordLatitudeSeconds':'0', 'AntennaCoordLatitudeSign':'0', 'AntennaCoordLongitudeDegrees':'0', \
                                                                         'AntennaCoordLongitudeFractions':'0', 'AntennaCoordLongitudeMinutes':'0', 'AntennaCoordLongitudeSeconds':'0', 'AntennaCoordLongitudeSign':'0', \
                                                                         'MaxCellBackRad':'0', 'MaxCellRad':'1', 'WLCSECId':'1', 'WLCSEMCC':'520', 'WLCSEMNC':'18', 'WLCSERncId':self.__neId }
        self.__createParams['WANE'] = { 'AuthorisedNetworkMCC':'520', 'AuthorisedNetworkMNC':'18', 'Technology':'1', 'WANEName':'WANE-1' }
        self.__createParams['WSG'] = { 'HomePlmnMCC':'520', 'HomePlmnMNC':'18', 'OperatorName':'Operator-1' }
        #not all parameters can be set to max value: parameter interdependencies
        self.__modifyMaxParams['RNC'] = { 'OMSIpAddress':'20.20.20.20', 'SecOMSIpAddress':'20.20.20.21', 'LCSSupportForAnchoring':'0', 'CBCSourceIPAddress':'20.20.20.20', 'CommonMCC':'998' }
        self.__modifyMaxParams['RNC'] = { 'RCPMtputDLCl01to02Range':'63100', 'RCPMtputDLCl02to03Range':'63200', 'RCPMtputDLCl03to04Range':'63300', 'RCPMtputDLCl04to05Range':'63400', 'RCPMtputDLCl05to06Range':'63500', 'RCPMtputDLCl06to07Range':'63600', \
                                                                         'RCPMtputDLCl07to08Range':'63700', 'RCPMtputDLCl08to09Range':'63800', 'RCPMtputDLCl09to10Range':'63900', 'RCPMtputDLCl10to11Range':'63910', 'RCPMtputDLCl11to12Range':'63920', 'RCPMtputDLCl12to13Range':'63930', \
                                                                         'RCPMtputULCl01to02Range':'61000', 'RCPMtputULCl02to03Range':'62000', 'RCPMtputULCl03to04Range':'63000', 'RCPMtputULCl04to05Range':'64000' }
        self.__modifyMaxParams['IADA'] = self.__modifyMaxParams['RNC']
        self.__modifyMaxParams['RNFC'] = { 'IntelligentEmergencyCallISHOSupport':'0' }
        self.__modifyMaxParams['RNAC'] = { 'ULmaxBitRateSF128':'1196', 'ULmaxBitRateSF16':'1199', 'ULmaxBitRateSF256':'1195', 'ULmaxBitRateSF32':'1198', 'ULmaxBitRateSF64':'1197', 'ULmaxBitRateSF8':'1200', \
                                                                             'DLmaxBitRateSF128':'1077', 'DLmaxBitRateSF16':'1080', 'DLmaxBitRateSF256':'1076', 'DLmaxBitRateSF32':'1079', 'DLmaxBitRateSF64':'1078' }
        self.__modifyMaxParams['RNHSPA'] = { 'HSDPAinitialBitrateUL':'4', 'HSDPAminAllowedBitrateUL':'4', 'ThresholdMaxEDPDCHSR1920kbps':'249', 'ThresholdMaxEDPDCHSR960kbps':'248', \
                                                                                 'DSCPCode1':'59', 'DSCPCode2':'60', 'DSCPCode3':'61', 'DSCPCode4':'62', 'DSCPCode5':'63', \
                                                                                 'NBRForPri1DL':'0', 'NBRForPri1UL':'0', 'NBRForPri2DL':'0', 'NBRForPri2UL':'0', 'NBRForPri3DL':'0', 'NBRForPri3UL':'0', 'NBRForPri4DL':'0', 'NBRForPri4UL':'0', \
                                                                                 'NBRForPri5DL':'0', 'NBRForPri5UL':'0', 'NBRForPri6DL':'0', 'NBRForPri6UL':'0', 'NBRForPri7DL':'0', 'NBRForPri7UL':'0', 'NBRForPri8DL':'0', 'NBRForPri8UL':'0', \
                                                                                 'NBRForPri9DL':'0', 'NBRForPri9UL':'0', 'NBRForPri0DL':'0', 'NBRForPri0UL':'0', 'NBRForPri10DL':'0', 'NBRForPri10UL':'0', 'NBRForPri11DL':'0', 'NBRForPri11UL':'0', \
                                                                                 'NBRForPri12DL':'0', 'NBRForPri12UL':'0' }
        self.__modifyMaxParams['RNMOBI'] = { 'DefaultAuthorisedNetworkId':'1' }
        self.__modifyMaxParams['IUO'] = { 'MCC':'520', 'MNC':'18', 'MNCLength':'2', 'SharedAreaMCC':'998', 'SharedAreaMNC':'998' }
        self.__modifyMaxParams['CBCI'] = { 'CBCIPaddress':'20.20.20.22', 'IUOIdentifier':'1' }
        self.__modifyMaxParams['IUR'] = { 'DelayThresholdMidIur':'31999', 'DelayThresholdMinIur':'31998' }
        self.__modifyMaxParams['IUCS'] = { 'CNId':'4094', 'NRIMaxForCSCN':'1023', 'NRIMinForCSCN':'1023' }    
        self.__modifyMaxParams['IUCSIP'] = { 'DestIPAddressCS':'20.20.20.23', 'IPBasedRouteIdCS':'1', 'IPNetmaskCS':'255.255.127.0', 'IPQMIdCS':'1' }
        self.__modifyMaxParams['IUPS'] = { 'NRIMaxForPSCN':'1023', 'NRIMinForPSCN':'1023' }
        self.__modifyMaxParams['IUPSIP'] = { 'DestIPAddressPS':'20.20.20.24', 'IPBasedRouteIdPS':'2', 'IPNetmaskPS':'255.255.127.0', 'IPQMIdPS':'1' }
        self.__modifyMaxParams['WAC'] = { 'TrafVolPendingTimeDL':'800', 'TrafVolPendingTimeUL':'800' }
        self.__modifyMaxParams['FMCS'] = { 'HHoEcNoThreshold':'-1', 'HHoRscpThreshold':'-26', 'EDCHAddEcNoOffset':'8' }
        self.__modifyMaxParams['FMCG'] = { 'IMSIbasedGsmHo':'0' }
        self.__modifyMaxParams['HOPL'] = { 'AdjLAbsPrioCellReselec':'6' }
        self.__modifyMaxParams['HOPG'] = { 'AdjgAbsPrioCellReselec':'4' }        
        self.__modifyMaxParams['IPNB'] = { 'NodeBIPAddress':'20.20.20.25', 'MinSCTPPortIub':'65530', 'CControlPortID':'2', 'SourceNBAPIPAddress':'0.0.0.0', 'SourceNBAPIPNetmask':'0' }
        self.__modifyMaxParams['VCEL'] = { 'EbNoSetIdentifier':'1', 'WACSetIdentifier':'1', 'SRBDCHFmcsId':'1' }
        self.__modifyMaxParams['BKPRNC'] = { 'BackUpRNCIP4Address':'20.20.20.26' }
        self.__modifyMaxParams['RNCERM'] = { 'RecvCscpLoadThr':'99' }
        self.__modifyMaxParams['WBTS'] = { 'IubTransportMedia':'1', 'IPNBId':'1', 'COCOId':'0', 'TQMId':'1', 'TQMId2':'0', 'TQMId3':'0', 'TQMId4':'0', 'IPBasedRouteIdIub2':'4094', 'IPBasedRouteIdIub3':'4093', 'IPBasedRouteIdIub4':'4092', 'DelayThresholdMid':'31999', 'DelayThresholdMid2msTTI':'31999', 'DelayThresholdMin':'31998', \
                                                                             'DelayThresholdMin2msTTI':'31998', 'NBAPCommMode':'0', 'PWSMInUse':'0', 'HSDPA14MbpsPerUser':'1', 'ICREnabled':'0', 'HSDPACCEnabled':'0', 'IubTransportSharing':'0', 'PWSMShutdownEndHour':'22', 'PWSMShutdownEndMin':'58' }
        self.__modifyMaxParams['WCEL'] = { 'AllowedPreambleSignatures':'61440', 'DCellHSDPAFmcsId':'1', 'EbNoSetIdentifier':'1', 'PFLIdentifier':'1', \
                                                                             'CSGroupId':'0', 'PSGroupId':'0', 'RNARGroupId':'0', 'PFLIdentifier':'0', 'RACH_Tx_NB01min':'49', 'PriScrCode':'510', 'WCELCSCNId':'4094', \
                                                                             'HSDPA64QAMallowed':'0', 'DCellAndMIMOUsage':'0', 'DCellHSDPACapaHO':'0', 'DCellHSDPAEnabled':'1', 'MIMOWith64QAMUsage':'0', \
                                                                             'HSUPA2MSTTIEnabled':'0', 'AdminPICState':'1', 'MIMOEnabled':'0', 'MaxTotalUplinkSymbolRate':'2', 'AMRUnderTransmission':'98', \
                                                                             'AMRTargetTransmission':'99', 'AMRUnderSC':'98', 'AMRTargetSC':'99','AMRUnderTxNC':'148', 'AMRTargetTxNC':'149','AMRTargetTxNonHSPA':'149', 'AMRUnderTxNonHSPA':'148', \
                                                                             'AMRTargetTxTotal':'149', 'AMRUnderTxTotal':'148', 'HSPAQoSEnabled':'1', 'NbrOfSCCPCHs':'2', 'CellRange':'10000', 'HSUPA16QAMAllowed':'0', 'WACSetIdentifier':'1', \
                                                                             'PtxTargetPSMin':'400', 'TargFreqLower':'16382', 'SRBDCHFmcsId':'1', 'SRBHSPAFmcsId':'1', 'MassEventHandler':'0', 'HSUPA2MSTTIEnabled':'1', 'AbsPrioCellReselec':'5', 'FMCLIdentifier':'1' }
        #For RAN 2054 feature "Extension of RNC ids" only, extended range of 4096..65534 will be used, otherwise older range 1..4095 will be used
        #always enabled in ADA, disabled in mcRNC/cRNC
        if self.__isAda:
            adjdRNCIdMaxValue = '65534'
        else:
            adjdRNCIdMaxValue = '4095'
        self.__modifyMaxParams['ADJS'] = { 'AdjsRNCid':adjdRNCIdMaxValue }
        self.__modifyMaxParams['ADJI'] = { 'AdjiUARFCN':'10800', 'BlindHOTargetCell':'0', 'AdjiCI':'65534', 'AdjiRNCid':adjdRNCIdMaxValue }
        self.__modifyMaxParams['ADJD'] = { 'AdjdScrCode':'509', 'AdjdCI':'65533', 'AdjdRNCId':adjdRNCIdMaxValue }
        self.__modifyMaxParams['ADJE'] = { 'AdjLIdentifier':'1' }
        self.__modifyMaxParams['WSG'] = { 'WSGAuthorisedNetworkId':'1' }
        self.__modifyMaxParams['WLCSE'] = { 'AntennaCoordLatitudeDegrees':'89', 'AntennaCoordLongitudeDegrees':'179', 'WLCSEMNC':'99', 'WLCSERncId':self.__neId, 'WLCSECId':'1', 'WLCSEMCC':'520', 'WLCSEMNC':'18', 'WLCSEMNCLength':'2' }                             
        self.__modifyMaxParams['WSMLC'] = { 'EmArc':'1', 'EmPoint':'2', 'EmPointAndAlt':'3', 'EmPointAndCircle':'4', 'EmPointAndEll3D':'5', 'EmPointAndEllipse':'6', 'EmPolygon':'7', \
                                                                                'Arc':'1', 'Point':'2', 'PointAndAlt':'3', 'PointAndCircle':'4', 'PointAndEll3D':'5', 'PointAndEllipse':'6', 'Polygon':'7', 'CiPosCalcInSAS':'0', 'OperationalMode':'0' }
        self.__modifyMaxParams['PFL'] = { 'PrefLayer64QAMAMR':'10660',    'PrefLayer64QAMAMRNRT':'10660', 'PrefLayer64QAMNRT':'10660', 'PrefLayer64QAMStr':'10660', 'PrefLayerCSHSAMR':'10660', 'PrefLayerCSHSAMRNRT':'10660', \
                                                                            'PrefLayerCSHSNRT':'10660', 'PrefLayerCSHSStr':'10660', 'PrefLayerDCHSDAMR':'10660', 'PrefLayerDCHSDAMRNRT':'10660', 'PrefLayerDCHSDNRT':'10660', 'PrefLayerDCHSDStr':'10660', \
                                                                            'PrefLayerDCMIAMR':'10660', 'PrefLayerDCMINRT':'10660', 'PrefLayerDCMIStr':'10660', 'PrefLayerFDPCHAMR':'10660', 'PrefLayerFDPCHAMRNRT':'10660', 'PrefLayerFDPCHNRT':'10660', \
                                                                            'PrefLayerFDPCHStr':'10660', 'PrefLayerFastMovUECS':'10660', 'PrefLayerFastMovUEPS':'10660', 'PrefLayerHSDPAAMR':'10660', 'PrefLayerHSDPAAMRNRT':'10660', 'PrefLayerHSDPANRT':'10660', \
                                                                            'PrefLayerHSDPAStr':'10660', 'PrefLayerHSPAAMR':'10660', 'PrefLayerHSPAAMRNRT':'10660', 'PrefLayerHSPANRT':'10660', 'PrefLayerHSPAStr':'10660', 'PrefLayerMIMOAMR':'10660', \
                                                                            'PrefLayerMIMOAMRNRT':'10660', 'PrefLayerMIMONRT':'10660', 'PrefLayerMIMOStr':'10660', 'PrefLayerR99AMR':'10660', 'PrefLayerR99AMRNRT':'10660', 'PrefLayerR99NRT':'10660', \
                                                                            'PrefLayerDCMIAMRNRT':'10660', 'PrefLayerR99Str':'10660' }
        #create empty test plan, to be modified later
        self.__createEmptyPlan()


    ## \brief Generate RNW creation plan
    #
    #    \param self object reference
    #    \param creationMode use 'min' or 'max' set of creation parameters
    #    \return -
    def creationPlan(self, creationMode):
        for managedObject in self.__managedObjects:
            if (self.__excludedObjects != None) and (managedObject in self.__excludedObjects):
                continue
            distName = self.__createDistName(managedObject)
            #print "distName:", distName
            newMoNode = self.__createManagedObject(managedObject, distName, 'create', 'RN6.0')
            for param, parentParam in self.__pddbData.getParamList(managedObject):
                paramObject = self.__pddbData.getParamObject(managedObject, param, parentParam)
                paramNode = self.__addParameter(managedObject, paramObject, PARAM_VALUE_DEFAULT, creationMode)
                if paramNode != None:
                    newMoNode.appendChild(paramNode)
            if self.__isObjectModifiable(managedObject):
                self.__cmdataNode.appendChild(newMoNode)
        if self.__failed == False:
            plan = 'RNWCREATE.XML'
            self.__writeDocToFile(plan)
            print "\nTest plan created: %s (%d objects, %d parameters added)" % (plan, self.__objectsAdded, self.__paramsAdded)


    ## \brief Generate RNW modification plan
    #
    #    \param self object reference
    #    \param modifyValue use 'min' or 'max' parameter values in modification plan 
    #    \return -
    def modificationPlan(self, modifyValue):
        if modifyValue == 'min':
            modifyValue = PARAM_VALUE_MIN
        else:
            modifyValue = PARAM_VALUE_MAX
        for managedObject in self.__managedObjects:
            if managedObject in self.__excludedObjects:
                continue
            distName = self.__createDistName(managedObject)
            newMoNode = self.__createManagedObject(managedObject, distName, 'update', 'RN6.0')
            for param, parentParam in self.__pddbData.getParamList(managedObject):
                paramObject = self.__pddbData.getParamObject(managedObject, param, parentParam)
                paramNode = self.__addParameter(managedObject, paramObject, modifyValue)
                if paramNode != None:
                    newMoNode.appendChild(paramNode)
            if self.__isObjectModifiable(managedObject):
                self.__cmdataNode.appendChild(newMoNode)
        if self.__failed == False:
            plan = 'RNWMODIFY.XML'
            self.__writeDocToFile(plan)
            print "\nTest plan created: %s (%d objects, %d parameters added)" % (plan, self.__objectsAdded, self.__paramsAdded)


    ## \brief Generate RNW deletion plan
    #
    #    \param self object reference
    #    \return -
    def deletionPlan(self):
        self.__managedObjects.reverse() #deletion order is opposite to creation
        for managedObject in self.__managedObjects:
            if managedObject in self.__excludedObjects:
                continue
            if managedObject in ['RNC', 'IADA', 'RNFC', 'RNMOBI', 'RNTRM', 'RNRLC', 'RNHSPA', 'RNPS', 'RNAC']: #can't be deleted
                continue
            distName = self.__createDistName(managedObject)
            newMoNode = self.__createManagedObject(managedObject, distName, 'delete', 'RN6.0')
            if self.__isObjectModifiable(managedObject):
                self.__cmdataNode.appendChild(newMoNode)
        plan = 'RNWDELETE.XML'
        self.__writeDocToFile(plan)
        print "\nTest plan created: %s (%d objects, %d parameters added)" % (plan, self.__objectsAdded, self.__paramsAdded)


    ## \brief Add one parameter to plan (list or single parameter)
    #
    #    \param self object reference
    #    \param managedObject name of the managed object
    #    \param paramObject instance of Parameter class
    #    \param paramValue parameter value (min/max/default)
    #    \param creationMode creation parameter set ( min (mandatory only) or max(mandatory+optional) )
    #    \return created parameter as dom node or None
    def __addParameter(self, managedObject, paramObject, paramValue, creationMode=None):
        if paramObject.isIdParameter():
            return None #id parameters are put to distName attribute, not as separate parameters
        if paramObject.getParamPlanDirection() != 'bi':
            return None #upload plan only parameter
        if self.__uploadPlan != None and paramObject.getParamOptionStatus() == False:
            return None #related option disabled
        if paramObject.getParentParam() != None:
            return None #list item parameter, they are added inside list when list parameter is added
        #S-NB parameters
        if 'NBAPCommMode' in self.__createParams['WBTS']:
            if self.__createParams['WBTS']['NBAPCommMode'] == '0':
                if paramObject.getName() in self.__snbParameters:
                    return None
        if paramObject.getName() in ['OMSIpAddress', 'SecOMSIpAddress', 'ServingOMSAdminSetting']:
            return None #don't modify GOMS address, because then CM events can't sent via GOMS to NetactStub anymore
        mode = 'create'
        if creationMode == 'min': #mandatory parameters only in creation
            if self.__isMandatoryParameter(paramObject, managedObject) == False:
                return None
        elif creationMode == 'max':
            pass
        else: #modification plan
            mode = 'modify'
            if paramObject.getModificationType() == 'unmodifiable':
                return None
            #if paramObject.getName() in self.__snbParameters:
            #    print "skip S-NB param:", paramObject.getName()
            #    return None
        childParams = paramObject.getChildParams()        
        includeName = True
        includeItem = True
        if childParams == [] and not paramObject.getName() in ['URAId', 'ADAURAId', 'CBCIPaddress']: #simple parameter
            if paramObject.getName() == "TACList":
                paramNode = self.__createListParameter(paramObject, False) 
            else:
                paramNode = self.__createSimpleParameter(managedObject, paramObject, paramValue, mode)
        else:
            if childParams == []: #e.g. UraId, special case when simple parameter and maxOccurs>1 => define values as list
                childParams = [paramObject.getName()]
                includeName = False
                includeItem = False
            paramNode = self.__createListParameter(paramObject, includeItem)            
        for childParam in childParams:
            if includeName == False and includeItem == False: #e.g. CBCIPaddress, no 'item'
                childParamObject = self.__pddbData.getParamObject(managedObject, childParam)
            else:
                childParamObject = self.__pddbData.getParamObject(managedObject, childParam, paramObject.getName())
            if childParamObject.getParamPlanDirection() != 'bi':
                continue #upload plan only parameter
            if self.__uploadPlan != None and childParamObject.getParamOptionStatus() == False:
                continue #related option disabled
            #emptyList = False
            childNode = self.__createSimpleParameter(managedObject, childParamObject, paramValue, mode, includeName)
            if includeItem: #add under item
                paramNode.firstChild.appendChild(childNode)
            else: #add directly under list
                paramNode.appendChild(childNode)
        return paramNode


    ## \brief Cretae simple parameter node
    #
    #    \param self object reference
    #    \param managedObject name of the managed object
    #    \param paramObject instance of Parameter class
    #    \param paramValue wanted parameter value (min, max or default)
    #    \param mode 'create' or 'modify'
    #    \param includeName add parameter name as attribute or not
    #    \return created parameter dom node
    def __createSimpleParameter(self, managedObject, paramObject, paramValue, mode, includeName=True):
        paramName = paramObject.getName()
        paramNode = self.__resultDoc.createElement('p')
        value = paramObject.getParamValue(paramValue)
        if mode == 'create':
            if managedObject in self.__createParams:
                if paramName in self.__createParams[managedObject]:
                    value = self.__createParams[managedObject][paramName]                    
        elif mode == 'modify':
            if paramObject.getModificationType() == 'unmodifiable': #can't be modified, use creation value (for example AMRLCSRBHSPATriggers)
                value = paramObject.getParamValue(PARAM_VALUE_DEFAULT) #use default unless created with different value
                if managedObject in self.__createParams:
                    if paramName in self.__createParams[managedObject]:
                        value = self.__createParams[managedObject][paramName]
            elif paramValue == PARAM_VALUE_MAX:
                if managedObject in self.__modifyMaxParams:
                    if paramName in self.__modifyMaxParams[managedObject]:
                        value = self.__modifyMaxParams[managedObject][paramName]
            elif paramValue == PARAM_VALUE_MIN:
                #TODO: add self.__modifyMinParams for parameters where PDDB min value is not accepted
                pass
        #only FMCX-1/HOPX-1 exists        
        if (paramName.find('Fmc') != -1 and paramName.find('Identifier') != -1) or \
             (paramName.find('Hop') != -1 and paramName.find('Identifier') != -1) or \
             (paramName.find('HopsId') != -1):
            value = '1'
        if includeName:
            paramNode.setAttribute('name', paramName)
        if value == None:
            value = paramObject.getSpecialValue()
        if value == None:
            print ERROR_MSG
            print "no default value: %s->%s" % (managedObject, paramName)
            print "don't know what value should be put to the plan"
            value = "NO DEFAULT"
            self.__failed = True
        valueNode = self.__resultDoc.createTextNode(value)
        paramNode.appendChild(valueNode)
        self.__paramsAdded += 1
        return paramNode

    ## \brief Cretae list parameter node
    #
    #    \param self object reference
    #    \param paramObject instance of Parameter class
    #    \param includeItem create 'item' node also
    #    \return -
    def __createNoItemListParameter(self, paramObject, includeItem):
        paramNode = self.__resultDoc.createElement('list')
        paramNode.setAttribute('name', paramObject.getName())
        if includeItem:
            itemNode = self.__resultDoc.createElement('item')
            paramNode.appendChild(itemNode)
        return paramNode

    ## \brief Cretae list parameter node
    #
    #    \param self object reference
    #    \param paramObject instance of Parameter class
    #    \param includeItem create 'item' node also
    #    \return -
    def __createListParameter(self, paramObject, includeItem):
        paramNode = self.__resultDoc.createElement('list')
        paramNode.setAttribute('name', paramObject.getName())
        if includeItem:
            itemNode = self.__resultDoc.createElement('item')
            paramNode.appendChild(itemNode)
        return paramNode


    ## \brief Create new managed object node
    #
    #    \param self object reference
    #    \param objectclass object class
    #    \param distName object distName
    #    \param operation plan operation, 'create', 'update' or 'delete'
    #    \param version object version
    #    \return managedObject created managed object as dom node
    def __createManagedObject(self, objectclass, distName, operation, version):
        self.__objectsAdded += 1
        managedObject = self.__resultDoc.createElement('managedObject')
        managedObject.setAttribute('class', objectclass)
        managedObject.setAttribute('distName', distName)
        managedObject.setAttribute('operation', operation)
        managedObject.setAttribute('version', version)
        return managedObject


    ## \brief Create empty new RNW plan
    #
    #    \param self object reference
    #    \return -
    def __createEmptyPlan(self):
        implementation = dom.getDOMImplementation()
        docType = implementation.createDocumentType('raml', None, None)
        self.__resultDoc = implementation.createDocument(dom.EMPTY_NAMESPACE, 'raml', docType)
        self.__resultDoc.documentElement.setAttribute('version', '2.1')
        self.__resultDoc.documentElement.setAttribute('xmlns', 'raml21.xsd')
        cmdataNode = self.__resultDoc.createElement('cmData')
        cmdataNode.setAttribute('adaptationVersionMajor', 'RN6.0')
        cmdataNode.setAttribute('id', '12345')
        cmdataNode.setAttribute('domain', 'RNCRNWCMPlan')
        cmdataNode.setAttribute('scope', 'all')
        cmdataNode.setAttribute('type', 'plan')
        headerNode = self.__resultDoc.createElement('header')
        logNode = self.__resultDoc.createElement('log')
        logNode.setAttribute('action', 'created')
        logNode.setAttribute('appInfo', 'test plan')
        logNode.setAttribute('dateTime', strftime("%Y-%m-%d %H:%M:%S"))
        headerNode.appendChild(logNode)
        cmdataNode.appendChild(headerNode)
        self.__resultDoc.documentElement.appendChild(cmdataNode)
        self.__cmdataNode = cmdataNode #add new managed objects here


    ## \brief Create object distName
    #
    #    \param self object reference
    #    \param managedObject managed object name
    #    \return distName
    def __createDistName(self, managedObject):
        #print "create distName for:", managedObject
        distName = ''
        while True:
            if managedObject == 'CMOB':
                objectId = '-4' # CMOB-1. CMOB-2, CMOB-3 created by the system, use 4 in testing
            else:
                objectId = '-1'
            parent = self.__pddbData.getParentObject(managedObject)
            if parent == None:
                return managedObject+ '-' + self.__neId + distName
            distName = '/' + managedObject + objectId + distName
            #print "parent:", parent, distName
            managedObject = parent


    ## \brief Is parameter mandatory in creation
    #
    #    \param self object reference
    #    \param paramObject instance of Parameter class
    #    \param className object class name
    #    \return True or False
    def __isMandatoryParameter(self, paramObject, className):
        #some object can't be created without parameters, although PDDB says so, add one parameter to such objects
        if paramObject.getName() in ['AMRLoadTxPower', 'ActivationTimeOffset', 'CPICHECNOSRBHSPA', 'AMRLCBufMaxOverbook2NRT', 'A2EA', \
                                                                 'AnchorFmciIdentifier', 'CMmasterSwitch', 'PLMNid', 'BackgroundTCToDSCP', 'AdditionTime', 'IFHOcauseCPICHEcNo', \
                                                                 'GSMcauseCPICHEcNo', 'AdjsHCSpriority', 'AdjiEcNoMargin', 'AdjgHCSpriority', 'AdjLAbsPrioCellReselec', \
                                                                 'FallbackForDCHQoSPri0']:
            return True
        childParams = paramObject.getChildParams()
        if childParams == []:
            #1) mandatory and no meaningful default
            #2) FmcxIdentifier: need to be defined, so that adjacencies can be created (default is not defined)
            #3) IP based route must be created with MML: error code 442D otherwise
            if (paramObject.getCreationPriority() == 'mandatory' and (paramObject.getDefaultValue() == None or paramObject.getDefaultValue() == '-' or \
                    paramObject.getDefaultValue() == '0.0.0.0')) or (paramObject.getName().find('Identifier') != -1 and paramObject.getName().find('Fmc') != -1) or \
                    paramObject.getName() == 'IPBasedRouteIdPS' or paramObject.getName() == 'IPBasedRouteIdCS':
                return True
        else:
            for childParam in childParams: #list is mandatory, if any child does not have default value            
                childParamObject = self.__pddbData.getParamObject(className, childParam, paramObject.getName())
                if childParamObject.getCreationPriority() == 'mandatory' and (childParamObject.getDefaultValue() == None or childParamObject.getDefaultValue() == '-'):
                    return True
        return False


    ## \brief Write created XML document to a file.
    #
    #    \param self object reference
    #    \param fileName created RNW plan file name
    #    \return -
    def __writeDocToFile(self, fileName):
        f = open(fileName, 'w')
        f.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        self.__printXml(f, self.__resultDoc.documentElement, indent = '', addindent = '    ', newl = '\n')
        f.close()


    # \brief Write XML document to open file handle, add proper indentation.
    #
    #    \param self object reference
    #    \param handle open file handle
    #    \param indent initial indentation
    #    \param addindent additional indentation for nested structures
    #    \param newl newline character
    #    \param fileName created RNW plan file
    #    \return -
    def __printXml(self, handle, node, indent = '', addindent = '', newl = ''):
        if node.nodeType == dom.Node.TEXT_NODE:
            if node.nodeValue.strip() != '':
                handle.write(node.nodeValue)
                return True
        if node.nodeType == dom.Node.COMMENT_NODE:
            handle.write(indent + "<!--" + node.nodeValue + "-->" + newl)
        if node.nodeType == dom.Node.ELEMENT_NODE:
            handle.write(indent + "<" + node.tagName)
            attrs = node.attributes
            a_names = attrs.keys()
            a_names.sort()
            for a_name in a_names:
                handle.write(" %s=\"%s\"" % (a_name, attrs[a_name].value))
            handle.write(">")
            #do not add a newline, if node has only text node children
            for childNode in node.childNodes:
                if childNode.nodeType == dom.Node.ELEMENT_NODE:
                    handle.write(newl)
                    break
            #recursive loop
            hasTextNode = False
            for childNode in node.childNodes:
                hasTextNode = self.__printXml(handle, childNode, indent + addindent, addindent, newl)
            if hasTextNode: #closing tag to the same line
                handle.write("</%s>%s" % (node.tagName, newl))
            elif node.childNodes == []: #empty list, e.g. <list name="DestIPAddrListCS"/>
                handle.write("</%s>%s" % (node.tagName, newl))
            else:
                handle.write("%s</%s>%s" % (indent, node.tagName, newl))
        return False


    # \brief Are needed licenses activated, so that object can be created/modified/deleted.
    #
    #    \param self object reference
    #    \param managedObject name of the managed object
    #    \return True or False
    def __isObjectModifiable(self, managedObject):
        if self.__uploadPlan == None: #no upload plan given, don't know which options are enabled, assume all
            return True
        params = self.__pddbData.getParamList(managedObject)
        for param, parentParam in params:
            #print "***", managedObject, param
            #e.g. 'WANEChangeOrigin' is not related to any feature, but it's IMSI HO parameter only
            if param.find('Origin') != -1:
                continue
            #VCEL-WACSetIdentifier is not related to any feature, but requires "I-BTS Sharing" anyway
            if param.find('WACSetIdentifier') != -1:
                continue
            paramObject = self.__pddbData.getParamObject(managedObject, param, parentParam)
            #also id parameters might not have proper feature defined
            if paramObject.isIdParameter():
                continue
            if paramObject.getParamOptionStatus():
                return True
        return False
                

#endif