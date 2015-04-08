import xml.etree.ElementTree as ET
import string
import TestResources
import os
import plan_generate
import PDDBData
import CreatePlan

from xml.sax import handler, make_parser, saxutils
from xml.sax.handler import feature_namespaces
from xml.sax._exceptions import SAXParseException

import xml.dom.minidom as dom
import os, sys

from Definitions import *
from Common import *

class XML_utils:

    """
    Keywords for XML comparison
    """

    class Diff:

        def __init__(self, name, val1, val2, parent_name=""):
            self.name = name
            self.val1 = val1
            self.val2 = val2
            self.parent_name = parent_name

        def __str__(self):
            s = self.name + ": " + str(self.val1) + " " + str(self.val2) + " " + self.parent_name
            return s
        
    class DiffThree:

        def __init__(self, name, val1, val2, val3, parent_name=""):
            self.name = name
            self.val1 = val1
            self.val2 = val2
            self.val3 = val3
            if parent_name == None:
                self.parent_name = "None"
            else:
                self.parent_name = parent_name

        def __str__(self):
            s = self.name + ": " + str(self.val1) + " " + str(self.val2) + " "+ str(self.val3) + " " + self.parent_name
            return s
            
    def print_diff_list(self, diff_list):
        """
        Prints the diff list
        """
        diff_text = ""
        for diff in diff_list:
            diff_text += str(diff)+"\r\n"
        print diff_text
        return diff_text
    
    def print_diff_dict(self, diff_list_all):
        """
        Prints the diff dict
        """
        if ( diff_list_all is None) or (len(diff_list_all) == 0):
            print ( "Errors are NOT detected in these plan files!" )
        else:
            print ( "Errors are detected in these plan files!" )
            for diff_type in diff_list_all.iterkeys():
                if ( len(diff_list_all[diff_type]) == 0 ):
                    continue
                print "Diff Obj:", diff_type
                print "ParamName:    InitialUploadPlan    DownloadPlan    FinalUploadPlan    ParentParam"
                #if diff_type == "Modified":
                if diff_type:
                    for mo in diff_list_all[diff_type].iterkeys():
                        if ( len(diff_list_all[diff_type][mo]) == 0 ):
                            continue
                        else:
                            print "MO:", mo
                            XML_utils().print_diff_list(diff_list_all[diff_type][mo])
                else:
                    XML_utils().print_diff_list(diff_list_all[diff_type])
            
    def get_cmdata_elem_from_text(self, text):
        """
        Returns the cmdata element from the plan XML given as text.
        (For some reason, ElementTree does not like the raml part, 
        so it is first manually removed before parsing the XML)
        """
        if text == None:
            return None
        cmdata_start = text.find("<cmData")
        cmdata_end = text.find("</cmData>")        
        if (cmdata_start==-1) or (cmdata_end==-1):
            raise AssertionError('Invalid parameter: cmData section not found')
        
        text = text[cmdata_start:cmdata_end+9]
        
        return ET.fromstring(text)

    def compare_three_element_text(self, elem_upload1, elem_download, elem_upload2, parent=""):
        """
        Compares the element text.
        Returns: Diff or None
        """
        if elem_upload1.text != elem_upload2.text and elem_download.text != elem_upload2.text:
            name = elem_upload1.get("name")
            if (name is not None):
                diff = self.DiffThree(name, elem_upload1.text, elem_download.text, elem_upload2.text, parent)
            else:
                diff = self.DiffThree(elem_upload1.tag, elem_upload1.text, elem_upload2.text, elem_download.text, parent)
            return diff
        return None
    
    def get_diff_three_p_elements(self, param_name, p_element_upload1, p_element_download, p_element_upload2, parent=""):
        diff = self.DiffThree(param_name, p_element_upload1.text, p_element_download.text, p_element_upload2.text, parent)
        return diff
       
    def compare_three_plans_p_elements(self, mo_upload1, mo_download, mo_upload2):
        p_names_upload1 = self._get_plan_p_element_names(mo_upload1)
        p_names_upload2 = self._get_plan_p_element_names(mo_upload2)
        diff_list = []

        common_p_names = p_names_upload1 & p_names_upload2
        for p_name in common_p_names:
            if "ChangeOrigin" in p_name:
                continue
            p_upload1 = self.find_subelement_with_attr_value(
                    mo_upload1, "p", "name", p_name)
            p_upload2 = self.find_subelement_with_attr_value(
                    mo_upload2, "p", "name", p_name)
            diff = self.compare_element_text(p_upload1, p_upload2, "")
            print "upload1, upload2 ", diff
            if diff is not None:
                #parameter modified, comparing download plan with final upload, 
                # if parameter exist in download, should be equal
                # if parameter doesn't exist in download, might be changed by other direct activation operation
                if mo_download != None:
                    p_names_download = self._get_plan_p_element_names(mo_download)
                    common_p_names_download = common_p_names & p_names_download
                    if p_name in common_p_names_download:
                        p_download = self.find_subelement_with_attr_value(
                                mo_download, "p", "name", p_name)
                        diff_download = self.compare_element_text(p_download, p_upload2, "")
                        if diff_download is None:
                            print "download, upload2 ", p_name, " is same"
                            diff = None
                        else:
                            print "download, upload2 ", diff_download
                    else:
                        #note, no parameter: p_name not in download
                        print "no related Parameter configuration in download, but configuration is changed"
                else:
                    #note, no mo: mo_download in download, but configuration is changed
                    print "no related MO configuration in download, but configuration is changed"
                if diff is not None:
                    diff_list.append(diff)
            else:
                #if parameter in download has different value, the parameter type should be 'uni-upload'
                print "if parameter in download has different value, the parameter type should be 'uni-upload'"
        return diff_list

        p_names_only_in_1 = p_names_upload1 - p_names_upload2
        for p_name in p_names_only_in_1:
            p1 = self.find_subelement_with_attr_value(
                mo_upload1, "p", "name", p_name)
            diff_list.append(self.Diff(p1.get("name"), p1.text, None, ""))

        p_names_only_in_2 = p_names_upload2 - p_names_upload1
        for p_name in p_names_only_in_2:
            p2 = self.find_subelement_with_attr_value(
                mo_upload2, "p", "name", p_name)
            diff_list.append(self.Diff(p2.get("name"), None, p2.text, ""))

    def compare_four_plans_mos(self, pddbData, mo_upload1, mo_download, mo_upload2, mo_history):
        param_names_upload1 = self.get_mo_param_names(mo_upload1)
        param_names_download = self.get_mo_param_names(mo_download)
        param_names_upload2 = self.get_mo_param_names(mo_upload2)
        param_names_history = self.get_mo_param_names(mo_history)
        skippedDownParams = []                            
        diff_result = []
        warn_result = []
        
        if mo_upload1 != None:
            #based on initialUpload parameter name
            mo_class = mo_upload1.get("class")
            dist_name = mo_upload1.get("distName")
            
            downCouldHaveParams = pddbData.getExpectedParametersWithInterfaceDirection(mo_class) 
            upExpectedParams = pddbData.getExpectedParametersWithInterfaceDirection(mo_class, "uni-up")
            print mo_class, dist_name
            print "PDDBdownParam", len(downCouldHaveParams), downCouldHaveParams
            print "PDDBupParam", len(upExpectedParams), upExpectedParams
                        
            if mo_upload2 != None:
                # "Operation Checking is done in check_config_management_result"
                # "Operation Checking parameter operation of Download is not delete"
                print "Checking parameter value of InitialUpload and FinalUpload"
                #if param value equals between InitialUpload and FinalUpload, it is either not changed in download or not present in download
                #if param value not equals between InitialUpload and FinalUpload, param value should be equal between download and FinalUpload
                """
                MO Modification checking rule:
                @todo: pddb related check
                for all parameters in initial upload, 
                    check if it's expected upload param
                        if not expected, record the error
                        if expected, remove it from the expected upload param list
                    check if it's included in final upload param
                        if not included, record the error
                    check if it's included in download param and not expected download param
                            if in download param but not expected, 
                                remove it from the download param list
                                log it in skipped download param list
                    compare the param value between initial and final upload plan
                        if not equal, check if the param is included in download plan
                            if included, check the value is equal between download and final upload plan
                                if not equal, record the error
                            if not included, record the error(if param in skipped download param list, show it in the error)
                        if equal, check if the param is included in download plan
                            if included, check the value is equal between download and final upload plan
                                if not equal, record the error
                check that all params included in download plan are checked
                check that expected upload param list is empty after processing
                """
                for param_name in param_names_upload1:
                    param_upload1 = self.get_mo_param_value(mo_upload1, param_name)
                    param_download = self.get_mo_param_value(mo_download, param_name)
                    param_upload2 = self.get_mo_param_value(mo_upload2, param_name)
                    param_history = self.get_mo_param_value(mo_history, param_name)
                    
                    if param_name in upExpectedParams:
                        upExpectedParams.remove(param_name)
                    else:
                        diff_result += [self.DiffThree(param_name + "NotExpectedInUpload", param_upload1, param_download, param_upload2)]
                        print param_name, "is not expected in upload, skipped"
                        continue
                    if param_name not in param_names_upload2:
                        diff_result += [self.DiffThree(param_name, param_upload1, param_download, param_upload2)]
                        print param_name, "is not included in final upload"
                        continue
                    if (param_names_download != None) and (param_name in param_names_download) and (param_name not in downCouldHaveParams):
                        print param_name, "is not expected in download, skipped in download param list"
                        param_names_download.remove(param_name)
                        skippedDownParams.append(param_name)
                        
                    if "ChangeOrigin" in param_name:
                        print param_name, "skipped in initial upload param list"
                        continue
                    print type(param_upload1), param_name, param_upload1, param_download, param_upload2, param_history
                        
                    if (not isinstance(param_upload1, set)):
                        if param_upload1 != param_upload2:
                            if param_download == None:
                                if param_name in skippedDownParams:
                                    diff_result += [self.DiffThree(param_name, param_upload1, "Skipped(NotExpected)", param_upload2)]
                                else:
                                    diff_result += [self.DiffThree(param_name, param_upload1, None , param_upload2)]
                            elif param_download != param_upload2:
                                #unmodified parameter
                                #if param_name not in skippedDownParams:
                                diff_result += [self.DiffThree(param_name, param_upload1, param_download, param_upload2)]
                        else:
                            if (param_download != None) and (param_download != param_upload2):
                                diff_result += [self.DiffThree(param_name, param_upload1, param_download, param_upload2)]
                    else:
                        if param_upload1 != param_upload2:
                            if param_download == None:
                                if param_name in skippedDownParams:
                                    diff_result += [self.DiffThree(param_name, param_upload1.difference(param_upload2), 
                                                               "Skipped(NotExpected)", param_upload2.difference(param_upload1))]
                                elif param_upload2 != None:
                                    diff_result += [self.DiffThree(param_name, param_upload1.difference(param_upload2), 
                                                               None, param_upload2.difference(param_upload1))]
                                else:
                                    diff_result += [self.DiffThree(param_name, param_upload1, None, None)]
                            elif param_download != param_upload2:
                                param_download_bi = self.get_mo_bi_param_value(pddbData, mo_download, param_name)
                                param_upload2_bi = self.get_mo_bi_param_value(pddbData, mo_upload2, param_name)
                                if param_download_bi == param_upload2_bi:
                                    print "param_download",param_download
                                    print "param_download_bi",param_download_bi
                                    print "param_upload2",param_upload2
                                    print "param_upload2_bi",param_upload2_bi
                                    continue                                    
                                diff_result += [self.DiffThree(param_name, param_upload1, param_download, param_upload2.difference(param_download))]
                        else:
                            if (param_download != None) and (param_download != param_upload2):
                                param_download_bi = self.get_mo_bi_param_value(pddbData, mo_download, param_name)
                                param_upload2_bi = self.get_mo_bi_param_value(pddbData, mo_upload2, param_name)
                                if param_download_bi == param_upload2_bi:
                                    print "param_download",param_download
                                    print "param_download_bi",param_download_bi
                                    print "param_upload2",param_upload2
                                    print "param_upload2_bi",param_upload2_bi
                                    continue                                    
                                diff_result += [self.DiffThree(param_name, param_upload1, param_download.difference(param_upload2), param_upload2)]
                if (param_names_download != None) and len(param_names_download - param_names_upload1) != 0:
                    notProcessedDownloadParamNames = param_names_download - param_names_upload1
                    for param_name in notProcessedDownloadParamNames:
                        paramInterfaceDirection = self.get_param_interface_direction(pddbData, mo_class, param_name)
                        featureStatus = self.get_param_feature_status(pddbData, mo_class, param_name)
                        if featureStatus == True:
                            if paramInterfaceDirection == "bi" or paramInterfaceDirection == "uni-up":
                                diff_result += [self.DiffThree(param_name, None, "ParamDirection:%s"%paramInterfaceDirection, None)]
                            elif paramInterfaceDirection == "uni-down":
                                print "Param direction of %s is uni-down"
                        else:
                            print "Feature not enabled for param %s:"%  param_name
                            warn_result += [self.DiffThree(str(upExpectedParams), "ExpectedButMissing", None, None)]
                if len(upExpectedParams) != 0:
                    for upExpectedParam in upExpectedParams:
                        featureStatus = self.get_param_feature_status(pddbData, mo_class, upExpectedParam)    
                        if featureStatus == True:
                            diff_result += [self.DiffThree(str(upExpectedParams), "ExpectedButMissing", None, None)]
                        else:
                            print "Feature not enabled for param %s:"%  upExpectedParam
                            warn_result += [self.DiffThree(str(upExpectedParams), "ExpectedButMissing", None, None)]
            else:
                print "Operation Checking is done in check_config_management_result"
                print "Checking parameter operation of Download is delete"
                #ManagedObject is deleted
        else:
            #based on finalUpload parameter name
            mo_class = mo_upload2.get("class")
            dist_name = mo_upload2.get("distName")
            downCouldHaveParams = pddbData.getExpectedParametersWithInterfaceDirection(mo_class) 
            upExpectedParams = pddbData.getExpectedParametersWithInterfaceDirection(mo_class, "uni-up")
        
            print mo_class, dist_name
            print "PDDBdownParam", len(downCouldHaveParams), downCouldHaveParams
            print "PDDBupParam", len(upExpectedParams), upExpectedParams
            
            # "Operation Checking is done in check_config_management_result"
            # "Checking parameter operation of Download is create or update"
            print "Checking parameter value of Download and FinalUpload"
            #ManagedObject is created
            
            #for all parameters in download, 
            #first check it's legal download parameter 
            #check legal download parameters have same value with parameters in upload2
            #check other parameters in upload2
            #parameter value should equal the default value defined in PDDB.  

            """
            MO Creation checking rule:
            
            for all parameters in upload, 
                check if it's expected upload param
                    if not, record the error
                    if yes, remove it from the expected upload param list
                check if it's expected download param
                    if not, continue
                check if it's included in download plan
                    if included, compare the value between download and upload plan
                        if value is different, then it's an error, record it
                    else(not included), compare the value between PDDB default value and upload plan
                        if value is different, then it's an error, record it
            check that all download plan params are checked 
            check that expected upload param list is empty after processing
            """
            for param_name in param_names_upload2:
                param_upload1 = self.get_mo_param_value(mo_upload1, param_name)
                param_download = self.get_mo_param_value(mo_download, param_name)
                param_upload2 = self.get_mo_param_value(mo_upload2, param_name)
                param_history = self.get_mo_param_value(mo_history, param_name)
                print type(param_upload2), param_name, param_upload1, param_download, param_upload2, param_history
                if param_name in upExpectedParams:
                    upExpectedParams.remove(param_name)
                else:
                    diff_result += [self.DiffThree(param_name + "NotExpectedInUpload", None, param_download, param_upload2)]
                    print param_name, "is not expected in upload, skipped"
                    continue
                if param_name not in downCouldHaveParams:
                    print param_name, "is not expected in download, skipped"
                    continue
                if param_name in param_names_download:
                    if param_download != param_upload2:
                        print "param_name: ", param_name
                        print "param_download: ", param_download
                        print "param_upload2: ", param_upload2
                        print "param_history: ", param_history
                        if param_upload2 == param_history:
                            continue
                        diff_result += [self.DiffThree(param_name, param_upload1, param_download, param_upload2)]
                else:
                    #param_expected_in_download = getPDDBParamDefaultValue()
                    paramParentName = self.get_mo_param_parent_name(pddbData, mo_class, param_name)
                    paramObject = pddbData.getParamObject(mo_class, param_name, paramParentName)
                    #param_expected_in_download = paramObject.getDefaultValue()
                    param_expected_in_download = self.get_mo_param_default_value(pddbData, mo_class, param_name)
                    if param_expected_in_download != param_upload2:
                        print "param_name, parentParam: ", param_name, paramParentName
                        print "param_expected_in_download: ", param_expected_in_download
                        print "param_upload2: ", param_upload2
                        print "param_history: ", param_history
                        if (param_names_history != None) and (param_name in param_names_history) and (param_upload2 == param_history):
                            continue
                        if param_expected_in_download == None:
                            param_expected_in_download = "None "
                        diff_result += [self.DiffThree(param_name, param_upload1, "(default)" + str(param_expected_in_download), param_upload2, paramParentName)]
            if len(param_names_download - param_names_upload2) != 0:
                    notProcessedDownloadParamNames = param_names_download - param_names_upload2
                    for param_name in notProcessedDownloadParamNames:
                        paramInterfaceDirection = self.get_param_interface_direction(pddbData, mo_class, param_name)
                        featureStatus = self.get_param_feature_status(pddbData, mo_class, param_name)
                        if featureStatus == True:
                            if paramInterfaceDirection == "bi" or paramInterfaceDirection == "uni-up":
                                diff_result += [self.DiffThree(param_name, None, "ParamDirection:%s"%paramInterfaceDirection, None, paramParentName)]
                            elif paramInterfaceDirection == "uni-down":
                                print "Param direction of %s is uni-down"
                        else:
                            print "Feature not enabled for param %s:"%  param_name
                            warn_result += [self.DiffThree(str(upExpectedParams), "ExpectedButMissing", None, None)]
            if len(upExpectedParams) != 0:
                for upExpectedParam in upExpectedParams:
                    featureStatus = self.get_param_feature_status(pddbData, mo_class, upExpectedParam)
                    if featureStatus == True:
                        diff_result += [self.DiffThree(str(upExpectedParams), None, None, "ExpectedButMissing")]
                    else:
                        print "Feature not enabled for param %s:"%  upExpectedParam
                        warn_result += [self.DiffThree(str(upExpectedParams), None, None, "ExpectedButMissing")]
        return diff_result

    def get_param_interface_direction(self, pddbData, mo_class, param_name):
        paramParentName = self.get_mo_param_parent_name(pddbData, mo_class, param_name)
        paramObject = pddbData.getParamObject(mo_class, param_name, paramParentName)
        if (paramObject != None):
            paramInterfaceDirection = paramObject.getParamInterfaceDirection()
        else:
            paramInterfaceDirection = None
        return paramInterfaceDirection

    def get_param_feature_status(self, pddbData, mo_class, paramName):
        paramParentName = self.get_mo_param_parent_name(pddbData, mo_class, paramName)
        paramObject = pddbData.getParamObject(mo_class, paramName, paramParentName)
        if (paramObject != None):
            featureStatus = paramObject.getParamOptionStatus()
        else:
            featureStatus = False
        return featureStatus

    def compare_three_plans_mos(self, pddbData, mo_upload1, mo_download, mo_upload2):
        param_names_upload1 = self.get_mo_param_names(mo_upload1)
        param_names_download = self.get_mo_param_names(mo_download)
        param_names_upload2 = self.get_mo_param_names(mo_upload2)
        skippedDownParams = []                            
        diff_result = []
        
        if mo_upload1 != None:
            #based on initialUpload parameter name
            mo_class = mo_upload1.get("class")
            dist_name = mo_upload1.get("distName")
            downCouldHaveParams = pddbData.getExpectedParametersWithInterfaceDirection(mo_class) 
            upExpectedParams = pddbData.getExpectedParametersWithInterfaceDirection(mo_class, "uni-up")
            print mo_class, dist_name
            print "PDDBdownParam", len(downCouldHaveParams), downCouldHaveParams
            print "PDDBupParam", len(upExpectedParams), upExpectedParams
                        
            if mo_upload2 != None:
                # "Operation Checking is done in check_config_management_result"
                # "Operation Checking parameter operation of Download is not delete"
                print "Checking parameter value of InitialUpload and FinalUpload"
                #if param value equals between InitialUpload and FinalUpload, it is either not changed in download or not present in download
                #if param value not equals between InitialUpload and FinalUpload, param value should be equal between download and FinalUpload
                """
                MO Modification checking rule:
                @todo: pddb related check
                for all parameters in initial upload, 
                    check if it's expected upload param
                        if not expected, record the error
                        if expected, remove it from the expected upload param list
                    check if it's included in final upload param
                        if not included, record the error
                    check if it's included in download param and not expected download param
                            if in download param but not expected, 
                                remove it from the download param list
                                log it in skipped download param list
                    compare the param value between initial and final upload plan
                        if not equal, check if the param is included in download plan
                            if included, check the value is equal between download and final upload plan
                                if not equal, record the error
                            if not included, record the error(if param in skipped download param list, show it in the error)
                        if equal, check if the param is included in download plan
                            if included, check the value is equal between download and final upload plan
                                if not equal, record the error
                check that all params included in download plan are checked
                check that expected upload param list is empty after processing
                """
                for param_name in param_names_upload1:
                    param_upload1 = self.get_mo_param_value(mo_upload1, param_name)
                    param_download = self.get_mo_param_value(mo_download, param_name)
                    param_upload2 = self.get_mo_param_value(mo_upload2, param_name)
                    
                    if param_name in upExpectedParams:
                        upExpectedParams.remove(param_name)
                    else:
                        diff_result += [self.DiffThree(param_name, param_upload1 + "NotExpectedInUpload", param_download, param_upload2)]
                        print param_name, "is not expected in upload, skipped"
                        continue
                    if param_name not in param_names_upload2:
                        diff_result += [self.DiffThree(param_name, param_upload1, param_download, param_upload2)]
                        print param_name, "is not included in final upload"
                        continue
                    if (param_names_download != None) and (param_name in param_names_download) and (param_name not in downCouldHaveParams):
                        print param_name, "is not expected in download, skipped in download param list"
                        param_names_download.remove(param_name)
                        skippedDownParams.append(param_name)
                        
                    if "ChangeOrigin" in param_name:
                        print param_name, "skipped in initial upload param list"
                        continue
                    print type(param_upload1), param_name, param_upload1, param_download, param_upload2
                        
                    if (not isinstance(param_upload1, set)) and (not isinstance(param_upload1, list)):
                        if param_upload1 != param_upload2:
                            if param_download == None:
                                if param_name in skippedDownParams:
                                    diff_result += [self.DiffThree(param_name, param_upload1, "Skipped(NotExpected)", param_upload2)]
                                else:
                                    diff_result += [self.DiffThree(param_name, param_upload1, None , param_upload2)]
                            elif param_download != param_upload2:
                                diff_result += [self.DiffThree(param_name, param_upload1, param_download, param_upload2)]
                        else:
                            if (param_download != None) and (param_download != param_upload2):
                                diff_result += [self.DiffThree(param_name, param_upload1, param_download, param_upload2)]
                    elif isinstance(param_upload1, set):
                        if param_upload1 != param_upload2:
                            if param_download == None:
                                if param_name in skippedDownParams:
                                    diff_result += [self.DiffThree(param_name, param_upload1.difference(param_upload2), 
                                                               "Skipped(NotExpected)", param_upload2.difference(param_upload1))]
                                else:
                                    diff_result += [self.DiffThree(param_name, param_upload1.difference(param_upload2), 
                                                               None, param_upload2.difference(param_upload1))]
                            elif param_download != param_upload2:
                                diff_result += [self.DiffThree(param_name, param_upload1, param_download, param_upload2.difference(param_download))]
                                
                        else:
                            if (param_download != None) and (param_download != param_upload2):
                                diff_result += [self.DiffThree(param_name, param_upload1, param_download.difference(param_upload2), param_upload2)]
                    elif isinstance(param_upload1, list):
                        #ToDo param_name in diff needs to be changed as p_name
                        if param_upload1 != param_upload2:
                            if param_download == None:
                                if param_name in skippedDownParams:
                                    diff_result += [self.DiffThree(param_name, param_upload1, "Skipped(NotExpected)", param_upload2)]
                                else:
                                    diff_result += [self.DiffThree(param_name, param_upload1, None, param_upload2)]
                            elif param_download != param_upload2:
                                diff_result += [self.DiffThree(param_name, param_upload1, param_download, set(param_upload2).difference(set(param_download)))]
                                
                        else:
                            if (param_download != None) and (param_download != param_upload2):
                                diff_result += [self.DiffThree(param_name, param_upload1, set(param_download).difference(set(param_upload2)), param_upload2)]
                if (param_names_download != None) and len(param_names_download - param_names_upload1) != 0:
                    notProcessedDownloadParamNames = param_names_download - param_names_upload1
                    for param_name in notProcessedDownloadParamNames:
                        paramParentName = self.get_mo_param_parent_name(pddbData, mo_class, param_name)
                        paramObject = pddbData.getParamObject(mo_class, param_name, paramParentName)
                        if (paramObject != None):
                            paramInterfaceDirection = paramObject.getParamInterfaceDirection()
                        else:
                            paramInterfaceDirection = None 
                        if paramInterfaceDirection == "bi" or paramInterfaceDirection == "uni-up":
                            diff_result += [self.DiffThree(param_name, None, "ParamDirection:%s"%paramInterfaceDirection, None)]
                        elif paramInterfaceDirection == "uni-down":
                            print "Param direction of %s is uni-down"
                if len(upExpectedParams) != 0:
                    diff_result += [self.DiffThree(str(upExpectedParams), "ExpectedButMissing", None, None)]
            else:
                print "Operation Checking is done in check_config_management_result"
                print "Checking parameter operation of Download is delete"
                #ManagedObject is deleted
        else:
            #based on finalUpload parameter name
            mo_class = mo_upload2.get("class")
            dist_name = mo_upload2.get("distName")
            downCouldHaveParams = pddbData.getExpectedParametersWithInterfaceDirection(mo_class) 
            upExpectedParams = pddbData.getExpectedParametersWithInterfaceDirection(mo_class, "uni-up")
        
            print mo_class, dist_name
            print "PDDBdownParam", len(downCouldHaveParams), downCouldHaveParams
            print "PDDBupParam", len(upExpectedParams), upExpectedParams
            
            # "Operation Checking is done in check_config_management_result"
            # "Checking parameter operation of Download is create or update"
            print "Checking parameter value of Download and FinalUpload"
            #ManagedObject is created
            
            #for all parameters in download, 
            #first check it's legal download parameter 
            #check legal download parameters have same value with parameters in upload2
            #check other parameters in upload2
            #parameter value should equal the default value defined in PDDB.  

            """
            MO Creation checking rule:
            
            for all parameters in upload, 
                check if it's expected upload param
                    if not, record the error
                    if yes, remove it from the expected upload param list
                check if it's expected download param
                    if not, continue
                check if it's included in download plan
                    if included, compare the value between download and upload plan
                        if value is different, then it's an error, record it
                    else(not included), compare the value between PDDB default value and upload plan
                        if value is different, then it's an error, record it
            check that all download plan params are checked 
            check that expected upload param list is empty after processing
            """
            for param_name in param_names_upload2:
                param_upload1 = self.get_mo_param_value(mo_upload1, param_name)
                param_download = self.get_mo_param_value(mo_download, param_name)
                param_upload2 = self.get_mo_param_value(mo_upload2, param_name)
                print type(param_upload2), param_name, param_upload1, param_download, param_upload2
                if param_name in upExpectedParams:
                    upExpectedParams.remove(param_name)
                else:
                    diff_result += [self.DiffThree(param_name, None, param_download, param_upload2 + "NotExpectedInUpload")]
                    print param_name, "is not expected in upload, skipped"
                    continue
                if param_name not in downCouldHaveParams:
                    print param_name, "is not expected in download, skipped"
                    continue
                if param_name in param_names_download:
                    if param_download != param_upload2:
                        diff_result += [self.DiffThree(param_name, param_upload1, param_download, param_upload2)]
                else:
                    #param_expected_in_download = getPDDBParamDefaultValue()
                    paramParentName = self.get_mo_param_parent_name(pddbData, mo_class, param_name)
                    paramObject = pddbData.getParamObject(mo_class, param_name, paramParentName)
                    #param_expected_in_download = paramObject.getDefaultValue()
                    param_expected_in_download = self.get_mo_param_default_value(pddbData, mo_class, param_name)
                    if param_expected_in_download != param_upload2:
                        if param_expected_in_download == None:
                            param_expected_in_download = "None "
                        diff_result += [self.DiffThree(param_name, param_upload1, "(default)" + str(param_expected_in_download), param_upload2)]
            if len(param_names_download - param_names_upload2) != 0:
                    notProcessedDownloadParamNames = param_names_download - param_names_upload2
                    for param_name in notProcessedDownloadParamNames:
                        paramParentName = self.get_mo_param_parent_name(pddbData, mo_class, param_name)
                        paramObject = pddbData.getParamObject(mo_class, param_name, paramParentName)
                        paramInterfaceDirection = paramObject.getParamInterfaceDirection()
                        if paramInterfaceDirection == "bi" or paramInterfaceDirection == "uni-up":
                            diff_result += [self.DiffThree(param_name, None, "ParamDirection:%s"%paramInterfaceDirection, None)]
                        elif paramInterfaceDirection == "uni-down":
                            print "Param direction of %s is uni-down"
            if len(upExpectedParams) != 0:
                diff_result += [self.DiffThree(str(upExpectedParams), None, None, "ExpectedButMissing")]
        return diff_result

    def get_mo_param_parent_name(self, pddbData, mo_class, param_name):
        
        params = pddbData.getParamList(mo_class)
        for param, parentParam in params:
            if param_name == param:
                return parentParam
        return None
        """
        paramDict = self.get_mo_param_dict(mo_class)
        if (paramDict == None ) or (param_name not in paramDict.iterkeys()):
            return None
        paramType, parentParam = paramDict[param_name]
        return parentParam
        """                
                            
    def get_mo_param_element(self, managedObject, paramName):
        if managedObject == None:
            return None
        paramDict = self.get_mo_param_dict(managedObject)
        paramType, parentParam = paramDict[paramName]
        if parentParam == None:
            if paramType == "p":
                paramElement = self.find_subelement_with_attr_value(
                        managedObject, "p", "name", paramName)
            else:
                paramElement = self.find_subelement_with_attr_value(
                        managedObject, "list", "name", paramName)
        else:
            parentParamObject = self.find_subelement_with_attr_value(managedObject, "list", "name", parentParam)
            paramElement = self.find_subelement_with_attr_value(parentParamObject, "p", "name", paramName)
        return paramElement
        
    def get_mo_param_names(self, managedObject):
        if managedObject == None:
            return None
        p_element_param_names = self._get_plan_p_element_names(managedObject)
        list_element_param_names = self._get_plan_list_element_names(managedObject)
        item_list_element_param_names = set()
        
        for list_name in list_element_param_names:
            list_object = self.find_subelement_with_attr_value(managedObject, "list", "name", list_name)
            if list_object.find("item") is not None:
                for item in list_object.iter("item"):
                    for p in item.iter('p'):
                        item_list_element_param_names.add(p.get('name'))
        # include child Params
        #mo_param_names = p_element_param_names.union(list_element_param_names.union(item_list_element_param_names))
        # skip child Params
        mo_param_names = p_element_param_names.union(list_element_param_names)
        return mo_param_names
        
    
    def get_mo_param_dict(self, managedObject):
        if managedObject == None:
            return None
        mo_param_dict = {}
        p_element_param_names = self._get_plan_p_element_names(managedObject)
        for param_name in p_element_param_names:
            #when param_name is empty?
            mo_param_dict.update({param_name: ("p", None)})
        list_element_param_names = self._get_plan_list_element_names(managedObject)
        for list_name in list_element_param_names:
            list_object = self.find_subelement_with_attr_value(
                    managedObject, "list", "name", list_name)
            if list_object.find("item") is not None:
                mo_param_dict.update({list_name: ("item-list", None)})
                for item in list_object.iter("item"):
                    for p in item.iter('p'):
                        mo_param_dict.update({p.get('name'): ("p", list_name)})
            else:
                mo_param_dict.update({list_name: ("p-list", None)})
        return mo_param_dict
    
    def check_config_management_result(self, pddbData, initial_upload_text, download_text, final_upload_text, \
                                       config_change_notify_text=None, history_upload_file_name=None):
        """
        Check configuration management result via initial upload, download, final download and configuration change notification
        """    
        cm_upload1 = self.get_cmdata_elem_from_text(initial_upload_text)
        cm_download = self.get_cmdata_elem_from_text(download_text)
        cm_upload2 = self.get_cmdata_elem_from_text(final_upload_text)
        cm_ccn = self.get_cmdata_elem_from_text(config_change_notify_text)
        cm_history = self.get_cmdata_from_file(history_upload_file_name)
            
        mo_names_upload1 = self._get_plan_mo_names(cm_upload1, "distName")
        mo_names_download = self._get_plan_mo_names(cm_download, "distName")
        mo_names_upload2 = self._get_plan_mo_names(cm_upload2, "distName")
        mo_names_ccn = self._get_plan_mo_names(cm_ccn, "distName")
        mo_names_history = self._get_plan_mo_names(cm_history, "distName")

        print "mo_names_upload1", mo_names_upload1
        print "mo_names_download", mo_names_download
        print "mo_names_upload2", mo_names_upload2
        print "mo_names_ccn", mo_names_ccn
        print "mo_names_history", mo_names_history
        
        diff_dict = {}
        warn_dict = {}
        common_diff_list = {}
        only_in_cm_upload1 = {}
        only_in_cm_upload2 = {}
        
        pddbData = XML_utils().get_rnc_feature_status(pddbData, final_upload_text)
        
        common_mo_names = mo_names_upload1 & mo_names_upload2
        for mo_name in common_mo_names:
            mo_upload1 = self.find_subelement_with_attr_value(
                    cm_upload1, "managedObject", "distName", mo_name)
            mo_download = self.find_subelement_with_attr_value(
                    cm_download, "managedObject", "distName", mo_name)
            if mo_download != None:
                mo_operation_download = mo_download.get("operation")
            else:
                mo_operation_download = None
            mo_upload2 = self.find_subelement_with_attr_value(
                    cm_upload2, "managedObject", "distName", mo_name)
            mo_history = self.find_subelement_with_attr_value(
                    cm_history, "managedObject", "distName", mo_name)
                    
            mo_diff_list = []
            if mo_operation_download == "delete":
                mo_diff_list += [self.DiffThree(mo_name, mo_name, mo_operation_download, mo_name, None)]
            else:
                mo_diff_list += self.compare_four_plans_mos(pddbData, mo_upload1, mo_download, mo_upload2, mo_history)

            if len(mo_diff_list) != 0:
                common_diff_list.update({mo_name: mo_diff_list})
        if len(common_diff_list) != 0 :
            diff_dict.update({"Modified": common_diff_list})

        #mo_names_only_in_upload1 are managed objects which are deleted
        mo_names_only_in_upload1 = mo_names_upload1 - mo_names_upload2
        for mo_name in mo_names_only_in_upload1:
            mo_upload1 = self.find_subelement_with_attr_value(
                    cm_upload1, "managedObject", "distName", mo_name)
            mo_download = self.find_subelement_with_attr_value(
                    cm_download, "managedObject", "distName", mo_name)
            mo_diff_list = []
            if mo_download != None:
                mo_operation_download = mo_download.get("operation")
            else:
                mo_diff_list += [self.DiffThree(mo_name, None, mo_name, None, None)]
                mo_operation_download = None
                continue
            
            if mo_operation_download != "delete":
                mo_diff_list += [self.DiffThree(mo_name, mo_name, mo_operation_download, None, None)]
            if len(mo_diff_list) != 0:
                only_in_cm_upload1.update({mo_name: mo_diff_list})
        if len(only_in_cm_upload1) != 0 :
            diff_dict.update({"Deleted": only_in_cm_upload1})
        
        #mo_names_only_in_upload2 are managed objects which are created
        mo_names_only_in_upload2 = mo_names_upload2 - mo_names_upload1
        for mo_name in mo_names_only_in_upload2:
            mo_diff_list = []
            mo_download = self.find_subelement_with_attr_value(
                    cm_download, "managedObject", "distName", mo_name)
            if mo_download == None:
                mo_diff_list += [self.DiffThree(mo_name, None, None, mo_name, None)]
                mo_operation_download = None
                continue
            else:
                mo_operation_download = mo_download.get("operation")
                
            mo_upload2 = self.find_subelement_with_attr_value(
                    cm_upload2, "managedObject", "distName", mo_name)
            mo_history = self.find_subelement_with_attr_value(
                    cm_history, "managedObject", "distName", mo_name)
            if mo_operation_download == "create" or mo_operation_download == "update":
                print "Checking parameters in download and finalUpload"
                mo_diff_list += self.compare_four_plans_mos(pddbData, None, mo_download, mo_upload2, mo_history)
            else:
                mo_diff_list += [self.DiffThree(mo_name, None, mo_operation_download, mo_name, None)]
            if len(mo_diff_list) != 0:
                only_in_cm_upload2.update({mo_name: mo_diff_list})
        if len(only_in_cm_upload2) != 0 :
            diff_dict.update({"Created": only_in_cm_upload2})
            
        return diff_dict
    
    def analyse_config_management_result(self, diff_dict_up1_up2, diff_dict_down_up2):
        for mo in diff_dict_up1_up2["common"].iterkeys():
            if mo in diff_dict_down_up2["common"].iterkeys():
                different_list = diff_dict_up1_up2["common"][mo] - diff_dict_down_up2["common"][mo]
                if len(different_list) != 0:
                    return False
        return True           
    
    def compare_plans_cmdata_into_dict(self, cmdata1, cmdata2, distName="distName"):
        """
        Compares two cmData elements
        Returns: Dict of Diffs
        """
        mo_names1 = self._get_plan_mo_names(cmdata1, distName)
        mo_names2 = self._get_plan_mo_names(cmdata2, distName)
        print mo_names1
        print mo_names2
        diff_list = {}
        common_diff_list = {}
        only_in_cm1 = {}
        only_in_cm2 = {}

        common_mo_names = mo_names1 & mo_names2
        for mo_name in common_mo_names:
            mo1 = self.find_subelement_with_attr_value(
                cmdata1, "managedObject", distName, mo_name)
            mo2 = self.find_subelement_with_attr_value(
                cmdata2, "managedObject", distName, mo_name)
            mo_diff_list = self.compare_plan_managed_objects(mo1, mo2)
            if len(mo_diff_list) != 0:
                common_diff_list.update({mo_name: mo_diff_list})
        if len(common_diff_list) != 0 :
            diff_list.update({"common": common_diff_list})

        mo_names_only_in_1 = mo_names1 - mo_names2
        for mo_name in mo_names_only_in_1:
            mo1 = self.find_subelement_with_attr_value(
                cmdata1, "managedObject", distName, mo_name)
            mo_diff_list = [self.Diff(mo_name, mo_name, None)]
            if len(mo_diff_list) != 0:
                only_in_cm1.update({mo_name: mo_diff_list})
        if len(only_in_cm1) != 0 :
            diff_list.update({"only_in_cm1": only_in_cm1})

        mo_names_only_in_2 = mo_names2 - mo_names1
        for mo_name in mo_names_only_in_2:
            mo1 = self.find_subelement_with_attr_value(
                cmdata2, "managedObject", distName, mo_name)
            mo_diff_list = [self.Diff(mo_name, None, mo_name)]
            if len(mo_diff_list) != 0:
                only_in_cm2.update({mo_name: mo_diff_list})
        if len(only_in_cm2) != 0 :
            diff_list.update({"only_in_cm2": only_in_cm2})

        return diff_list
    
    def compare_plans_cmdata(self, cmdata1, cmdata2, distName="distName"):
        """
        Compares two cmData elements
        Returns: list of Diffs
        """
        mo_names1 = self._get_plan_mo_names(cmdata1, distName)
        mo_names2 = self._get_plan_mo_names(cmdata2, distName)
        diff_list = []

        common_mo_names = mo_names1 & mo_names2
        for mo_name in common_mo_names:
            mo1 = self.find_subelement_with_attr_value(
                cmdata1, "managedObject", distName, mo_name)
            mo2 = self.find_subelement_with_attr_value(
                cmdata2, "managedObject", distName, mo_name)
            diff_list += self.compare_plan_managed_objects(mo1, mo2)

        mo_names_only_in_1 = mo_names1 - mo_names2
        for mo_name in mo_names_only_in_1:
            mo1 = self.find_subelement_with_attr_value(
                cmdata1, "managedObject", distName, mo_name)
            diff_list.append(self.Diff(mo_name, mo_name, None))

        mo_names_only_in_2 = mo_names2 - mo_names1
        for mo_name in mo_names_only_in_2:
            mo1 = self.find_subelement_with_attr_value(
                cmdata2, "managedObject", distName, mo_name)
            diff_list.append(self.Diff(mo_name, None, mo_name))

        return diff_list

    def compare_plan_managed_objects(self, mo1, mo2):
        """
        Compares two managedObject elements
        Returns: list of Diffs
        """
        diff_list = []
        diff_list += self.compare_plan_p_elements(mo1, mo2)
        diff_list += self.compare_plan_list_elements(mo1, mo2)

        return diff_list
        
    def compare_plans_mos(self, cmdata1, cmdata2, dist_name, new_param_list=[]):
        """
        Compares two cmData elements
        new_param_list conatins all the new parameters which belongs to the compared managedObject
        Returns: list of Diffs
        """
        mo1 = self.find_subelement_with_attr_value(
            cmdata1, "managedObject", "distName", dist_name)
        mo2 = self.find_subelement_with_attr_value(
            cmdata2, "managedObject", "distName", dist_name)
        diff_list = []
        diff_list += self.compare_plan_managed_objects(mo1, mo2)
        return diff_list


    def compare_plan_list_elements(self, object1, object2):
        """
        <list name="RncOptions">
          <p>0</p>
          <p>5</p>
        </list>
        <list name="MACLogicalChPriority">
          <item>
            <p name="MACLogChPriSRB1">1</p>
            <p name="MACLogChPriSRB2">1</p>
          </item>
        </list>
        """
        list_names1 = self._get_plan_list_element_names(object1)
        list_names2 = self._get_plan_list_element_names(object2)
        diff_list = []

        common_list_names = list_names1 & list_names2
        for list_name in common_list_names:
            list1 = self.find_subelement_with_attr_value(
                object1, "list", "name", list_name)
            list2 = self.find_subelement_with_attr_value(
                object2, "list", "name", list_name)
            if list1.find("item") is not None:
                diff_list += self.compare_plan_item_list_elements(list1, list2, list_name)
            else:
                #diff_list += self.compare_plan_scalar_list_elements(list1, list2)
                diff_list += self.compare_plan_p_list_elements(list1, list2)

        list_names_only_in_1 = list_names1 - list_names2
        for list_name in list_names_only_in_1:
            list1 = self.find_subelement_with_attr_value(
                object1, "list", "name", list_name)
            diff_list.append(self.Diff(list_name, list_name, None))

        list_names_only_in_2 = list_names2 - list_names1
        for list_name in list_names_only_in_2:
            list2 = self.find_subelement_with_attr_value(
                object2, "list", "name", list_name)
            diff_list.append(self.Diff(list_name, None, list_name))

        return diff_list

    def compare_plan_scalar_list_elements(self, list1, list2):
        """
        <list name="RncOptions">
          <p>0</p>
          <p>5</p>
        </list>

        Returns: list of Diffs
        """
        diff_list = []
        list_name = list1.get("name")

        list_values_1 = []
        for p in list1.iter("p"):
            list_values_1.append(p.text)

        list_values_2 = []
        for p in list2.iter("p"):
            list_values_2.append(p.text)

        length = min(len(list_values_1), len(list_values_2))

        # parameters in both lists
        for i in range(0, length):
            if list_values_1[i] != list_values_2[i]:
                diff_list.append(
                    self.Diff(list_name, list_values_1[i], list_values_2[i]))

        # parametesr in list1 but not in list2
        for i in range(length, len(list_values_1)):
            diff_list.append(self.Diff(list_name, list_values_1[i], None))

        # parametesr in list2 but not in list1
        for i in range(length, len(list_values_2)):
            diff_list.append(self.Diff(list_name, None, list_values_2[i]))

        return diff_list
    
    def compare_plan_p_list_elements(self, list1, list2):
        """
        <list name="RncOptions">
          <p>0</p>
          <p>5</p>
        </list>

        Returns: list of Diffs
        """
        diff_list = []
        list_name = list1.get("name")

        list_values_1 = set()
        for p in list1.iter("p"):
            list_values_1.add(p.text)

        list_values_2 = set()
        for p in list2.iter("p"):
            list_values_2.add(p.text)

        # parameters in both lists
        common_p_list = list_values_1 & list_values_2
        p_only_in_list1 = list_values_1 - common_p_list
        # parametesr in list1 but not in list2
        if len(p_only_in_list1) > 0: 
            for p in p_only_in_list1:
                diff_list.append(self.Diff(list_name, p, None))
        
        # parametesr in list2 but not in list1
        p_only_in_list2 = list_values_2 - common_p_list
        if len(p_only_in_list2) > 0: 
            for p in p_only_in_list2:
                diff_list.append(self.Diff(list_name, None, p))

        return diff_list

    def compare_plan_item_list_elements(self, list1, list2, parent=""):
        """
        <list name="MACLogicalChPriority">
          <item>
            <p name="MACLogChPriSRB1">1</p>
            <p name="MACLogChPriSRB2">1</p>
          </item>
        </list>

        Returns: list of Diffs
        """
        diff_list = []
        list_name = list1.get("name")

        item_elems_1 = []
        for item in list1.iter("item"):
            item_elems_1.append(item)

        item_elems_2 = []
        for item in list2.iter("item"):
            item_elems_2.append(item)

        length = min(len(item_elems_1), len(item_elems_2))

        # items in both lists
        for i in range(0, length):
            diff_list += self.compare_plan_p_elements(item_elems_1[i],
                                                      item_elems_2[i],
                                                      list_name)

        # items in list1 but not in list2
        for i in range(length, len(item_elems_1)):
            diff_list.append(self.Diff(list_name, "item", None))

        # items in list2 but not in list1
        for i in range(length, len(item_elems_2)):
            diff_list.append(self.Diff(list_name, None, "item"))

        return diff_list

    def compare_plan_p_elements(self, object1, object2, parent=""):
        """
        <p name="PageRep1stInterv">11</p>
        <p name="PageRep2ndInterv">20</p>

        Returns: list of Diffs
        """
        p_names1 = self._get_plan_p_element_names(object1)
        p_names2 = self._get_plan_p_element_names(object2)
        diff_list = []

        common_p_names = p_names1 & p_names2
        for p_name in common_p_names:
            p1 = self.find_subelement_with_attr_value(
                object1, "p", "name", p_name)
            p2 = self.find_subelement_with_attr_value(
                object2, "p", "name", p_name)
            diff = self.compare_element_text(p1, p2, parent)
            if diff is not None:
                diff_list.append(diff)

        p_names_only_in_1 = p_names1 - p_names2
        for p_name in p_names_only_in_1:
            p1 = self.find_subelement_with_attr_value(
                object1, "p", "name", p_name)
            diff_list.append(self.Diff(p1.get("name"), p1.text, None, parent))

        p_names_only_in_2 = p_names2 - p_names1
        for p_name in p_names_only_in_2:
            p2 = self.find_subelement_with_attr_value(
                object2, "p", "name", p_name)
            diff_list.append(self.Diff(p2.get("name"), None, p2.text, parent))

        return diff_list

    def compare_element_attributes_all(self, elem1, elem2):
        """
        Compares all the attributes of elem1 and elem2.
        Returns: list of Diff
        """
        diff_list = []

        attributes1 = set(elem1.keys())
        attributes2 = set(elem2.keys())

        # Check all attributes found from elem1
        for attr in attributes1:
            val1 = elem1.get(attr)
            val2 = elem2.get(attr)
            if (val1 != val2):
                diff_list.append(
                    self.Diff(elem1.tag + ":" + attr, val1, val2))

        # Check if any attributes are found from elem2, which are not found
        # from elem1
        diff_set = attributes2 - attributes1
        for attr in diff_set:
            val2 = elem2.get(attr)
            diff_list.append(self.Diff(elem1.tag + ":" + attr, None, val2))

        return diff_list

    def compare_element_attributes(self, elem1, elem2, attr_list):
        """
        Compares the given attributes of elem1 and elem2
        Returns: list of Diff
        """
        diff_list = []

        for attr in attr_list:
            val1 = elem1.get(attr)
            val2 = elem2.get(attr)
            if (val1 != val2):
                diff_list.append(
                    self.Diff(elem1.tag + ":" + attr, val1, val2))

        return diff_list

    def compare_element_text(self, elem1, elem2, parent=""):
        """
        Compares the element text.
        Returns: Diff or None
        """
        if elem1.text != elem2.text:
            name = elem1.get("name")
            if (name is not None):
                diff = self.Diff(name, elem1.text, elem2.text, parent)
            else:
                diff = self.Diff(elem1.tag, elem1.text, elem2.text, parent)
            return diff
        return None

    def find_subelement_with_attr_value(self, element, tag, attr, val):
        """
        Returns the subelement with the given tag and attribute value.
        """
        for e in element.findall(tag):
            if e.get(attr) == val:
                return e

        return None

    def _get_plan_elements_with_attr(self, obj, tag, attr):
        elems = set()
        for elem in obj.findall(tag):
            elems.add(elem.get(attr))
        return elems

    def _get_plan_p_element_names(self, obj):
        """
        Returns the set of p names from the given object
        """
        if obj == None:
            return None
        return self._get_plan_elements_with_attr(obj, "p", "name")

    def _get_plan_list_element_names(self, obj):
        """
        Returns the set of list names from the given object
        """
        return self._get_plan_elements_with_attr(obj, "list", "name")

    def _get_plan_mo_names(self, cmdata, distname="distName"):
        """
        Returns the set of managedObject names from the given cmData
        """
        if cmdata == None:
            return None
        return self._get_plan_elements_with_attr(cmdata, "managedObject", distname)

    def compare_plan_cmdata_and_obj(self, obj, cmdata):
        """
        Returns a list of differences.
        """
        diff_list = []
        
        # object id parameter
        # <managedObject class="COCO" distName="COCO-1" version="RN7.0" operation="update">
        dist_name = cmdata.find('managedObject').get("distName")
        obj_id = dist_name.split('-')[-1]
        print "obj_id = " + obj_id
        p = obj.getObjectIdParam()
        if p is not None:
            param = p.getName()
            value = p.getVal()
            if obj_id != value:
                print 'diff',param,value,obj_id
                diff_list.append(self.Diff(param, value, obj_id))        
        
        # simple parameters
        for p in cmdata.iterfind('managedObject/p'):
            param = p.get("name")
            value = p.text
            if value is None:
                value = ''
            try:
                obj_value = obj.getParam(param)[0].getVal()
            except AttributeError as e:
                print 'Error',param,'is a list???'
                for p in obj.getParam(param):
                    print p.__class__.__name__
                    print p.getVal()
                raise e
            except IndexError as e:
                print param,'is missing from jondoe output???',obj.getParam(param)
                diff_list.append(self.Diff(param, None, value))
                continue
                #raise e
            if value != obj_value:
                print 'diff',param,'val in XML=',value,'val in jondoe print=',obj_value
                diff_list.append(self.Diff(param, obj_value, value))
            print param
                
        # struct and list parameters
        for l in cmdata.iterfind('managedObject/list'):
            parent_name = l.get("name")
            print 'name', parent_name
            items = l.iterfind('item')
            class NotFoundParam:
                def getVal(self):
                    return 'Param Not Found'
                def __str__(self):
                    return self.getVal()

            if items is not None:
                #struct / struct list
                for i in items:
                    for p in i.findall('p'):
                        param = "%s/%s"%(parent_name,p.get("name"))
                        value = p.text
                        params = obj.getParam(param)
                        par = NotFoundParam()
                        for par in params:
                            if value == par.getVal():
                                break
                        else:
                            print 'diff',p.get("name"),value,str(par)
                            diff_list.append(self.Diff(p.get("name"), value, par.getVal(), parent_name))
                        print param
            else:
                # list
                params = obj.getParam(parent_name)
                obj_values = []
                for p in params:
                    obj_values.append(p.getVal())

                for p in items.findall('p'):
                    value = p.text
                    if value not in obj_value:
                        diff_list.append(self.Diff(param, value, obj_value))
                    print param
        return diff_list

    def get_cmdata_from_file(self, file_name):
        f = open(file_name)
        plan_text = string.replace(f.read(),'RNC-1',TestResources.getResources('RNC-ID'))
        plan = self.get_cmdata_elem_from_text(plan_text)
        print '*DEBUG* %s' % plan_text
        return plan
            
    def remove_element_from_cmdata(self, cmdata, distName):
        mo = self.find_subelement_with_attr_value(
                cmdata, "managedObject", "distName", distName)
        print mo
        cmdata.remove(mo)
        
    def remove_other_elements_from_cmdata(self, cmdata, distName_to_keep):
        for mo in cmdata.findall("managedObject"):
            if mo.get("class") != distName_to_keep:
                print "removing mo "+str(mo.get("class"))
                cmdata.remove(mo)

    def _get_mo_item(self, plan_xml, dist_name):
        plan = self.get_cmdata_elem_from_text(plan_xml)
        if plan is None:
            raise AssertionError('Invalid plan file, cmData not found')

        for mo in plan.findall('managedObject'):
            if mo.get('distName') == dist_name:
                return mo
        else:
            raise AssertionError('Managed Object %s not found from plan' % dist_name)

    def get_plan_list_item_count(self, plan_xml, dist_name, list_name):
        mo = self._get_mo_item(plan_xml, dist_name)
        for l in mo.iter('list'):
            if l.get('name') == list_name:
                count = 0
                i = 0
                while i < l.iter('item'):
                    i += 1
                    count += 1
                return count
        else:
            raise AssertionError('List param %s not found' % list_name)

    def get_mo_param_value(self, managedObject, paramName):
        if managedObject == None:
            return None
        paramDict = self.get_mo_param_dict(managedObject)
        if paramName not in paramDict.iterkeys():
            return None
        paramType, parentParam = paramDict[paramName]
        if paramType == "p":
                paramValue = self.get_mo_p_param_value(managedObject, paramName)
        elif paramType == "p-list":
                paramValue = self.get_mo_p_list_param_value(managedObject, paramName)
        elif paramType == "item-list":
            paramObject = self.find_subelement_with_attr_value(managedObject, "list", "name", paramName)
            paramValue = self.get_mo_item_list_param_value(paramObject, paramName, paramName)
        return paramValue

    def get_mo_bi_param_value(self, pddbData, managedObject, paramName):
        if (pddbData == None) or (managedObject == None):
            return None
        paramDict = self.get_mo_param_dict(managedObject)
        if paramName not in paramDict.iterkeys():
            return None
        paramType, parentParam = paramDict[paramName]
        paramObject = pddbData.getParamObject(managedObject.get("class"), paramName)
        if paramObject == None:
            return None
        paramValue = None
        if paramType == "p":
            if paramObject.getParamInterfaceDirection() == "bi":
                paramValue = self.get_mo_p_param_value(managedObject, paramName)
        elif paramType == "p-list":
            if paramObject.getParamInterfaceDirection() == "bi":
                paramValue = self.get_mo_p_list_param_value(managedObject, paramName)
        elif paramType == "item-list":
            paramObject = self.find_subelement_with_attr_value(managedObject, "list", "name", paramName)
            paramValue = self.get_mo_item_list_bi_param_value(pddbData, managedObject, paramObject, paramName)
        return paramValue

    def get_mo_param_default_value(self, pddbData, managedObject, paramName):
        valueSet = set()
        itemString = ""
        itemList = []
        paramObject = pddbData.getParamObject(managedObject, paramName)
        if paramObject == None:
            return None

        childParams = paramObject.getChildParams()
        if len(childParams) !=0:
            for childParam in childParams:
                childParamObject = pddbData.getParamObject(managedObject, childParam, paramName)
                param_ui_value = childParamObject.getDefaultValue()
                param_internal_value = childParamObject.getParamInternalValue(param_ui_value)
                param_special_value = childParamObject.getSpecialValue()
                print "ui_value, internal_value, special_value", param_ui_value, param_internal_value, param_special_value
                """
                if param_special_value == param_ui_value:
                    continue
                """
                if param_internal_value != None:
                    itemString += "(" + childParamObject.getName() + "=" + str(int(param_internal_value)) + ")"
                    itemList.append(childParamObject.getName() + "=" + str(int(param_internal_value)))
                else:
                    itemString += "(" + childParamObject.getName() + "=" + param_ui_value + ")"
                    itemList.append(childParamObject.getName() + "=" + param_ui_value)
            itemList.sort()
            itemTuple = tuple(itemList)
            valueSet.add(itemTuple)
            return valueSet
        else:
            param_ui_value = paramObject.getDefaultValue()
            param_internal_value = paramObject.getParamInternalValue(param_ui_value)
            param_special_value = paramObject.getSpecialValue()
            """
            if param_special_value == param_ui_value:
                return None
            """
            print "ui_value, internal_value param_special_value", param_ui_value, param_internal_value, param_special_value
            if param_internal_value != None:
                return str(int(param_internal_value))
            else:
                return param_ui_value
    
    def get_mo_p_param_value(self, managedObject, param_name):
        for p in managedObject.iter('p'):
            if p.get('name') == param_name:
                return p.text
        print 'Parameter %s not found from plan' % param_name
    
    def get_mo_p_list_param_value(self, managedObject, list_name):
        value_set = set()
        for l in managedObject.iter('list'):
            if l.get('name') == list_name:
                for p in l.iter('p'):
                    value_set.add(p.text)
        """
        if len(value_set) == 0:
            value_set = None
        """
        return value_set
    
    def get_mo_item_p_list_param_value(self, managedObject, list_name, param_name, element_index = 0):
        for l in managedObject.iter('list'):
            if l.get('name') == list_name:
                for i,item in enumerate(l.iter('item')):
                    if i != int(element_index):
                        continue
                    for p in item.iter('p'):
                        if p.get('name') == param_name:
                            return p.text
                    print 'Parameter %s not found from plan' % param_name
        print 'List param %s not found' % list_name

    def get_mo_item_list_bi_param_value(self, pddbData, managedObject, paramObject, list_name):
        string_list = []
        value_list = []
        value_set = set()
        item_content = ""
        pddbParamObject = pddbData.getParamObject(managedObject.get("class"), list_name)
        if pddbParamObject == None:
            return None
        childParams = pddbParamObject.getChildParams()
        if len(childParams) !=0:
            for childParam in childParams:
                childParamObject = pddbData.getParamObject(managedObject.get("class"), childParam, list_name)
        for l in paramObject.iter('list'):
            if l.get('name') == list_name:
                for item in l.iter('item'):
                    item_list = []
                    for p in item.iter('p'):
                        childParamName = p.get('name')
                        childParamObject = pddbData.getParamObject(managedObject.get("class"), childParamName, list_name)
                        paramFeatureStatus = self.get_param_feature_status(pddbData, managedObject.get("class"), childParamName)
                        if paramFeatureStatus == True:
                            if childParamObject.getParamInterfaceDirection() == "bi":
                                item_content += "(" + p.get('name') + "=" + p.text + ")"
                                item_list.append(p.get('name') + "=" + p.text)
                    item_list.sort()
                    item_tuple = tuple(item_list)
                    string_list.append(item_content)    
                    value_list.append(item_list)
                    value_set.add(item_tuple)
        value_list.sort()
        #return value_list
        return value_set
    
    def get_mo_item_list_param_value(self, managedObject, list_name, param_name):
        string_list = []
        value_list = []
        value_set = set()
        item_content = ""
        for l in managedObject.iter('list'):
            if l.get('name') == list_name:
                for item in l.iter('item'):
                    item_list = []
                    for p in item.iter('p'):
                        item_content += "(" + p.get('name') + "=" + p.text + ")"
                        item_list.append(p.get('name') + "=" + p.text)
                    item_list.sort()
                    item_tuple = tuple(item_list)
                    string_list.append(item_content)    
                    value_list.append(item_list)
                    value_set.add(item_tuple)
        string_list.sort()
        value_list.sort()
        #return value_list
        return value_set
        
    def get_mo_item_list_as_dict_param_value(self, managedObject, list_name, param_name):
        value_list = []
        item_dict = {}
        for l in managedObject.iter('list'):
            if l.get('name') == list_name:
                for item in l.iter('item'):
                    for p in item.iter('p'):
                        item_dict.update({p.get('name'): p.text})
                    value_list.append(item_dict)    
        return value_list
    
    def get_plan_p_param_value(self, plan_xml, dist_name, param_name):
        mo = self._get_mo_item(plan_xml, dist_name)
        for p in mo.iter('p'):
            if p.get('name') == param_name:
                return p.text
        raise AssertionError('Parameter %s not found from plan' % param_name)

    def get_plan_list_param_value(self, plan_xml, dist_name, list_name, param_name, element_index = 0):
        mo = self._get_mo_item(plan_xml, dist_name)
        for l in mo.iter('list'):
            if l.get('name') == list_name:
                for i,item in enumerate(l.iter('item')):
                    if i != int(element_index):
                        continue
                    for p in item.iter('p'):
                        if p.get('name') == param_name:
                            return p.text
                    else:
                        raise AssertionError('Parameter %s not found from plan' % param_name)
                else:
                    raise AssertionError('List %s has only %d elements' % (list_name, i))
#            else:
#                print 'Some other item',l.get('name')
        else:
            raise AssertionError('List param %s not found' % list_name)

    def get_rnc_feature_status(self, pddbData, uploadFileText):
        
        if pddbData == None or uploadFileText == None:
            return None
        uploadFileText = uploadFileText.replace("\r\n","")
        uploadPlanDoc = dom.parseString(uploadFileText)
        enabledOptionsText, neId, isAda = getRncOptions(uploadPlanDoc, pddbData, "UploadPlanText")
        pddbData.setOptions(enabledOptionsText, isAda)
        return pddbData
       
    def check_xml_file_parse(self, file_name):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        new_dir = plan_generate.plan_generate().get_new_dir(base_dir)
        path_and_file_name = new_dir+file_name
        pa = False
        try:
            ET.parse(file_name)
            pa = 'True'
            print pa
        except Exception,e:
            pa = False
        if pa == False:
            raise AssertionError('%s' % e)


def test_print_diff_dict():
    f1 = open("RNWPLAND_COMBINE_ADJI_create.XML")
    f2 = open("RNWPLAND_COMBINE_ADJI_create1.XML")
    plan1 = XML_utils().get_cmdata_elem_from_text(f1.read())
    plan2 = XML_utils().get_cmdata_elem_from_text(f2.read())
    #diff_list = XML_utils().compare_plans_cmdata(plan1, plan2)
    #diff_list = XML_utils().compare_plans_mos(plan1,plan2,"RNC-1/RNAC-1")

    diff_list_all = XML_utils().compare_plans_cmdata_into_dict(plan1, plan2)
    XML_utils().print_diff_dict(diff_list_all)

def test_check_config_management_result():
    initialUploadFileName = "InitialUpload.XML"
    downloadActivationFileName = "DownloadActivation.XML"
    finalUploadFileName = "FinalUpload.XML"
    f1 = open(initialUploadFileName)
    f2 = open(downloadActivationFileName)
    f3 = open(finalUploadFileName)

    plan1 = f1.read()
    plan2 = f2.read()
    plan3 = f3.read()

    f1.close()
    f2.close()
    f3.close()
    
    pddbReport = "PDDB_REP_mcRNCR_QNCB.14.26.4_11.WR.mips.rmp.XML"
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
    pddbData = XML_utils().get_rnc_feature_status(pddbData, plan3)
    """
    if finalUploadFileName != None:
        uploadPlanDoc = dom.parse(finalUploadFileName)
        managedObjects = uploadPlanDoc.documentElement.getElementsByTagName('managedObject')
    
    enabledOptionsText, neId, isAda = getRncOptions(uploadPlanDoc, pddbData, finalUploadFileName)
    pddbData.setOptions(enabledOptionsText, isAda)
    """
    diff_list_all = XML_utils().check_config_management_result(pddbData, plan1, plan2, plan3, None, "HistoryUpload.XML")
    XML_utils().print_diff_dict(diff_list_all) 
    
def test_get_mo_params():
    f1 = open("InitialUpload.XML")
    plan1 = f1.read()
    f1.close()
    
    param_names = []
    cmdata = XML_utils().get_cmdata_elem_from_text(plan1)
    mo_names = XML_utils()._get_plan_mo_names(cmdata)
    for mo_name in mo_names:
        print "MO: ", mo_name
        managedObject = XML_utils()._get_mo_item(plan1, mo_name)
        param_names = XML_utils().get_mo_param_names(managedObject)
        for param_name in param_names:
            param_type, parentParam = XML_utils().get_mo_param_dict(managedObject)[param_name]
            param_value = XML_utils().get_mo_param_value(managedObject, param_name)
            print param_name, param_type, parentParam, param_value

def test_get_expected_params():
    pddbReport = "PDDB_REP_cRNCQX151495.XML"
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
    downCouldHaveParams = pddbData.getExpectedParametersWithInterfaceDirection("RNHSPA") 
    upExpectedParams = pddbData.getExpectedParametersWithInterfaceDirection("RNHSPA", "uni-up")
    print downCouldHaveParams
    print upExpectedParams
    for param in upExpectedParams:
        if param == "AQMDelayThresholdTime":
            print "found"
    for param, parentParam in pddbData.getParamList("RNHSPA"):
        if param == "AQMDelayThresholdTime":
            print "found in paramList:"
            
def test_createPlan(creationMode):
    f1 = open("InitialUploadOrigin.XML")
    f2 = open("DownloadActivation.XML")
    f3 = open("FinalUploadOrigin.XML")
    plan1 = f1.read()
    plan2 = f2.read()
    plan3 = f3.read()
    f1.close()
    f2.close()
    f3.close()
    
    pddbReport = "PDDB_REP_mcRNCR_QNCBD.15.14.95_2.WR.mips.dvb.XML"
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
    
    excludedObjects = ['RNC', 'RNAC', 'RNPS', 'RNHSPA', 'RNRLC', 'RNTRM', 'RNMOBI', 'RNFC', 'RNCERM', 'COSITE', 'COSRNC', 'CBCI', 'IUO', 'IPQM', 'IUCS', 'IUCSIP', 'IUPS', 'IUPSIP', \
                       'IUR', 'CMOB', 'COCO', 'IPNB', 'PREBTS', 'PFL', 'FMCS', 'FMCI', 'FMCG', 'FMCL', 'HOPS', 'HOPI', 'HOPG', 'HOPL', 'TQM', 'WRAB', 'WAC', 'VBTS', 'VCEL', 'WBTS', \
                       'WCEL', 'ADJS', 'ADJI', 'ADJG', 'ADJL', 'ADJE', 'WSMLC', 'WLCSE', 'WANE', 'WSG', 'RNCSRV', 'BKPRNC', 'PRNC', 'DATSYN', 'WDEV']
    excludedObjectsCOCO = ["COCO", "RNCSRV", "PRNC", "BKPRNC", "DATSYN"]
    planGenerator = CreatePlan.CreatePlan(pddbData, "InitialUpload.XML", excludedObjectsCOCO, "1")
    planGenerator.creationPlan(creationMode)         
               
"""
This main function is for comparing two plan files on command line:
"""
def main():

    '''
    if (sys.argv.__len__() != 3):
        print "Usage: script <plan.xml> <plan.xml>"
        exit(1)
    else:
        plan_file_1 = sys.argv[1]
        plan_file_2 = sys.argv[2]
    '''
    testResource = TestResources.getAndSetResources('10.69.33.47')
    print testResource
    testResource.update({"test":"It's OK"})
    print TestResources.getResources("test")
    """
    testResource = TestResources.getAndSetResources('10.56.116.8')
    print testResource
    testResource.update({"test":"It's not OK"})
    print TestResources.getResources("test")
    """
    #testResource = TestResources.getAndSetResources('10.69.33.47')
    print testResource
    print TestResources.getResources("test")
    
    print TestResources.current_resources.getRes()
    
    #test_check_config_management_result()
    #test_get_expected_params()
    #test_get_mo_params()
    #test_createPlan("max")
    """  
    if ( len(diff_list_all) == 0 ):
        print ( "These plan files are similar!" )
    else:
        print ( "These plan files are different!" )
        for diff_type in diff_list_all.iterkeys():
            if ( len(diff_list_all[diff_type]) == 0 ):
                continue
            print "Diff Obj:", diff_type
            if diff_type == "common":
                for mo in diff_list_all[diff_type].iterkeys():
                    if ( len(diff_list_all["common"][mo]) == 0 ):
                        continue
                    else:
                        print "MO:", mo
                        XML_utils().print_diff_list(diff_list_all["common"][mo])
            else:
                XML_utils().print_diff_list(diff_list_all[diff_type])
    """
    
    '''
    print "diff per MO"
    mo_list = ['CMOB', 'IPNB', 'IPQM', 'IUO', 'IUR', 'PFL', 'TQM', 'WANE', 'WRAB', 'WSMLC']
    for ma_object in mo_list:
        dist_name = dist_name_dict[ma_object]
        print 'dist_name: ', dist_name
        diff_list = XML_utils().compare_plans_mos(plan1,plan2,dist_name)
    
    
        if ( len(diff_list) == 0 ):
            print ( "These plan files are similar!" )
        else:
            print ( "These plan files are different!" )
            XML_utils().print_diff_list(diff_list)
    '''

if __name__ == "__main__":
    main()