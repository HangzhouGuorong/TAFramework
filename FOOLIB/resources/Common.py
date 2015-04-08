## @package CMtools
#    Tools for CM testing.
#    \file Common.py

#ifndef _COMMON_
#define _COMMON_

from Definitions import *
import sys

## \brief Print name of the entered method.
#
#    \param msg trace message
def debugTrace(msg):
    if DEBUG:
        print msg + sys._getframe(1).f_code.co_name


## \brief Print debug message to console.
#
#    \param msg debug message
def debugPrint(msg):
    if DEBUG:
        print msg


## \brief Read RNC options from upload plan.
#
#    \param uploadPlanDoc upload plan as XML document
#    \param pddbData instance of PDDBData class
#    \param uploadPlan upload plan file anme
#    \return list of enabled options, NE id and if NE is ADA or not
def getRncOptions(uploadPlanDoc, pddbData, uploadPlan):
    enabledOptionsText = []
    neId = ""
    rncOptions = False
    rncOpt = False
    paramObject = pddbData.getParamObject('RNC', 'RncOptions')
    for managedObject in uploadPlanDoc.documentElement.getElementsByTagName('managedObject'):
        #print "object:", managedObject.getAttribute('class')
        if managedObject.getAttribute('class') == 'RNC' or managedObject.getAttribute('class') == 'IADA':
            neId = managedObject.getAttribute('distName')
            if neId == "":
                print ERROR_MSG
                sys.exit("Can't find distName from RNC/IADA object")
            neId = neId.replace('PLMN-PLMN/', '')
            neId = "NE-" + neId
            #RncOptions parameter is removed from ADA PDDB with CR#E0682, no need to check options
            if managedObject.getAttribute('class') == 'IADA':
                return [], neId, True
            paramNodes = managedObject.getElementsByTagName('list')
            for paramNode in paramNodes:
                if paramNode.getAttribute('name') == 'RncOptions':
                    rncOptions = True
                    options = paramNode.getElementsByTagName('p')
                    for option in options:
                        #map option enum value to text value
                        optionText = paramObject.getEnumerationTextValue(option.firstChild.nodeValue)
                        if optionText.strip() == 'Reserved':
                            print ERROR_MSG
                            print "option %s is \'%s\' in PDDB, should not be used in upload plan" % (option.firstChild.nodeValue, optionText)
                        else:
                            enabledOptionsText.append( optionText )
        # CR E0709 - RncOptions parameter is replaced by RNCOPT object
        elif managedObject.getAttribute('class') == 'RNCOPT':
            rncOpt = True
            #print "RNCOPT found"
            for option in managedObject.getElementsByTagName('p'):
                name = option.getAttribute('name')
                paramObject = pddbData.getParamObject('RNCOPT', name)
                if paramObject == None:
                    print ERROR_MSG
                    sys.exit("option not defined in PDDB: "+name)
                fullName = paramObject.getFullName()
                if fullName.strip() == 'Reserved':
                    print ERROR_MSG
                    print "option %s is \'%s\' in PDDB, should not be used in upload plan" % fullName
                    continue
                if fullName.find('Status') != -1:
                        print ERROR_MSG
                        sys.exit("Option has wrong full name, no \'status\': "+fullName)
                #for example: "HSUPA 2.0 Mbps status" => HSUPA 2.0 Mbps
                fullName = fullName[0:-7]
                fullName = fullName.strip()
                if option.firstChild.nodeValue == '1':
                    #print "enabled option found:", fullName, ' = ', option.firstChild.nodeValue
                    enabledOptionsText.append(fullName)
                else:
                    #print "disabled/configured option found:", fullName, '=', option.firstChild.nodeValue
                    pass
            break #RNC/IADA is always first object, RNCOPT is after it, nothing more to check from upload plan

    if rncOptions and rncOpt:
        print ERROR_MSG
        sys.exit("PDDB contains both \'RncOptions\' parameter and \'RNCOPT\' object")

    if rncOptions == False and rncOpt == False: 
        print ERROR_MSG
        print "Neither parameter \'RncOptions\' or object \'RNCOPT\' found from", uploadPlan
        sys.exit()
    return enabledOptionsText, neId, False


#endif