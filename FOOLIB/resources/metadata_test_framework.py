try:
    from comm.communication import connections as il_connections
    from flexi_platform.fphaslib import get_all_recovery_group_names as get_all_the_recovery_group_names
    from flexi_platform.fphaslib import show_managed_object_state as show_manage_object_states
except:
    pass
import atexit
import re
import TestResources
import os
import time
from parameter_utils import parameter_utils
import paramiko
from profiling_utils import profiling_utils
import log_utils
import gzip
import sys
import random
import XML_utils
import string
import plan_generate
import PDDBData
from xml.sax import handler, make_parser, saxutils
from xml.sax.handler import feature_namespaces
from xml.sax._exceptions import SAXParseException
from Definitions import *
from Common import *

org_execute_mml = None

try:
    # If this fails then IPA MMl cannot be used
    #Get if from
    # svn co https://svne1.access.nsn.com/isource/svnroot/ipatap/ipata/ipamml/trunk/src/ ipamml
    # and set PYTHONPATH correctly
    import IpaMml.connections
    import STE
    import Utils.ftp_lib
    import IpaMml.units_lib
    import IpaMml.pif_lib.sdh_protection 
    import IpaMml.broadband_admin_lib
except:
    pass

class ParameterNotFoundException(Exception):
    pass

class ObjStruct:
    """
    This class is used for parsing the object struct contents from JONDOE's command output
    """
    def __init__(self):
        self.params = []

    def add(self, param):
        self.params.append(param)

    def getParam(self, name):
        res = []
        for p in self.params:
            if p.getName() == name:
                res.append(p)

        return res

    def getObjectIdParam(self):
        for p in self.params:
            if p.__class__ == ObjectIdParam:
                return p

    def __str__(self):
        s = ''
        for p in self.params:
            s += str(p) + '\n'
        return s

class Param:
    """
    This class is used for parsing object struct fields from JONDOE's command output
    """
    def __init__(self, name, typeOfParam = None):
        self.name = name
        self.value = None
        self.type = typeOfParam

    def addVal(self, val):
        self.value = val

    def getName(self):
        return self.name

    def getVal(self):
        return str(self.value)

    def __str__(self):
        return self.name + '=' + str(self.value)

class Bits(Param):
    def __init__(self, name):
        Param.__init__(self, name)
        self.count = 0
        self.value = 0

    def addVal(self, bit):
        val = int(bit) << self.count
        self.value = self.value | val
        self.count += 1

class ObjectIdParam(Param):
    def __init__(self,name):
        Param.__init__(self, name)

class metadata_test_framework():

    class ObjectInfoClass():
        """
        This base class represents one object type and information related to it:
        - name of the database (mcRNC), name of the database file (cRNC),
        - list of objects, which are required to be created before this object can be created,
        - can the object be deleted with a plan operation or not,
        etc.
        The information is used by test case setup keywords.
        """
        def __init__(self,obj_name,actdb=None,newdb=None,dbid=None,actfile=None,newfile=None,delete_with_plan=True,required_objects=["RNC_all"],mcRNC_only=False,cRNC_only=False):
            if actdb is None:
                self.actdb = "act_"+obj_name.lower()
            else:
                self.actdb = actdb
            if dbid is None:
                self.dbid = obj_name.lower()+"_id"
            else:
                self.dbid = dbid
            if newdb is None:
                self.newdb = "new_"+obj_name.lower()
            else:
                self.newdb = newdb

            self.actfile = actfile
            self.newfile = newfile
            self.delete_with_plan = delete_with_plan
            self.required_objects = required_objects
            self.obj_name = obj_name
            self.cRNC_only = cRNC_only
            self.mcRNC_only = mcRNC_only

        def object_exists_in_db(self,db="act"):
            """
            Returns True or False
            """
            if TestResources.ismcRNC():
                prompt = [r"\[.*@.*\]\s*[#$]|Password:|.*\s*DBRNWHSB=# "]
                old_prompt = il_connections.set_prompt(prompt)
                il_connections.execute_mml_without_check('zdbrnw')
                if ( db == "act" ):
                    output = il_connections.execute_mml_without_check('select %s from %s;'%(self.dbid,self.actdb))
                else:
                    output = il_connections.execute_mml_without_check('select %s from %s;'%(self.dbid,self.newdb))
                il_connections.execute_mml_without_check('\\q')
                il_connections.set_prompt(old_prompt)
                if "(0 rows)" in output:
                    return False
                else:
                    return True
            else:
                if ( db == "act" ):
                    output = IpaMml.connections.execute_mml_without_check( "ZDFB:OMU,%d:%s:0,0;" % (0, self.actfile))
                else:
                    output = IpaMml.connections.execute_mml_without_check( "ZDFB:OMU,%d:%s:0,0;" % (0, self.newfile))
                if "00000000  R" in output:
                    return True
                else:
                    return False

    class ObjectInfoClass_IU(ObjectInfoClass):
        """
        This is the base class for IUSC, IUSP, IUCSIP and IUPSIP Object Info Classes
        """
        ###
        # DB check does not work correctly because IUCS/IUPS and IUPSIP/IUCSIP are using
        # the same DB file so we actually do not know which object is stored there
        def object_exists_in_db(self, db='act'):
            if db == 'act':
                output = metadata_test_framework().direct_obj_inquire(self.moid)
                if "<p name='status'>Error</p>" in output:
                    return False
                else:
                    return True
            else:
                if TestResources.ismcRNC():
                    prompt = [r"\[.*@.*\]\s*[#$]|Password:|.*\s*DBRNWHSB=# "]
                    old_prompt = il_connections.set_prompt(prompt)
                    il_connections.execute_mml_without_check('zdbrnw')
                    output = il_connections.execute_mml_without_check('select cn_domain from %s where cn_domain=%d;'%self.newdb,self.domain)
                    il_connections.execute_mml_without_check('\\q')
                    il_connections.set_prompt(old_prompt)
                    if "(0 rows)" in output:
                        return False
                    else:
                        return True
                else:
                    output = IpaMml.connections.execute_mml_without_check( "ZDFB:OMU,%d:%s:0;" % (0, self.newfile))
                    if "00000000  R" in output:
                        return True
                    else:
                        return False

    class ObjectInfoClass_IUCS(ObjectInfoClass_IU):
        """
        Object Info Class for IUCS.
        """
        moid='RNC-1/IUCS-1'
        domain = 0

    class ObjectInfoClass_IUPS(ObjectInfoClass_IU):
        """
        Object Info Class for IUCS.
        """
        moid='RNC-1/IUPS-1'
        domain = 1

    class ObjectInfoClass_IUCSIP(ObjectInfoClass_IU):
        """
        Object Info Class for IUCSIP
        """
        moid='RNC-1/IUCS-1/IUCSIP-1'
        domain = 0

    class ObjectInfoClass_IUPSIP(ObjectInfoClass_IU):
        """
        Object Info Class for IUPSIP
        """
        moid='RNC-1/IUPS-1/IUPSIP-1'
        domain = 1

    class ObjectInfoClass_WCEL(ObjectInfoClass):
        """
        Object Info Class for WCEL
        """
        def object_exists_in_db(self,db="act"):
            """
            Returns True or False
            """
            if TestResources.ismcRNC():
                prompt = [r"\[.*@.*\]\s*[#$]|Password:|.*\s*DBRNWHSB=# "]
                old_prompt = il_connections.set_prompt(prompt)
                il_connections.execute_mml_without_check('zdbrnw')
                if ( db == "act" ):
                    output = il_connections.execute_mml_without_check('select wbts_id,lcr_id,cid from %s where wbts_id=1;'%self.actdb)
                else:
                    output = il_connections.execute_mml_without_check('select wbts_id,lcr_id,cid from %s where wbts_id=1;'%self.newdb)
                il_connections.execute_mml_without_check('\\q')
                il_connections.set_prompt(old_prompt)
                if "(0 rows)" in output:
                    return False
                else:
                    return True
            else:
                if ( db == "act" ):
                    output = IpaMml.connections.execute_mml_without_check( "ZDFB:OMU,%d:%s:0,0;" % (0, self.actfile))
                else:
                    output = IpaMml.connections.execute_mml_without_check( "ZDFB:OMU,%d:%s:0,0;" % (0, self.newfile))
                if "00000000  R" in output:
                    return True
                else:
                    return False

    class ObjectInfoClass_WSMLC(ObjectInfoClass):
        """
        Object Info Class for WSMLC
        """
        def object_exists_in_db(self,db="act"):
            """
            WSMLC has no wsmlc_id in db, use wsmlc_data instead. Returns True or False.
            """
            if TestResources.ismcRNC():
                prompt = [r"\[.*@.*\]\s*[#$]|Password:|.*\s*DBRNWHSB=# "]
                old_prompt = il_connections.set_prompt(prompt)
                il_connections.execute_mml_without_check('zdbrnw')
                if ( db == "act" ):
                    output = il_connections.execute_mml_without_check('select count(wsmlc_data) from %s;' % self.actdb)
                else:
                    output = il_connections.execute_mml_without_check('select count(wsmlc_data) from %s;' % self.newdb)
                il_connections.execute_mml_without_check('\\q')
                il_connections.set_prompt(old_prompt)
                if "     0" in output:
                    return False
                else:
                    return True
            else:
                if ( db == "act" ):
                    output = IpaMml.connections.execute_mml_without_check( "ZDFB:OMU,%d:%s:0;" % (0, self.actfile))
                else:
                    output = IpaMml.connections.execute_mml_without_check( "ZDFB:OMU,%d:%s:0;" % (0, self.newfile))
                if "00000000  R" in output:
                    return True
                else:
                    return False

    class ObjectInfoClass_VBTS(ObjectInfoClass):
        """
        Object Info Class for VBTS
        """
        def object_exists_in_db(self,db="act"):
            """
            VBTS has no vbts_id in db, use wsmlc_data instead. Returns True or False.
            """
            if TestResources.ismcRNC():
                prompt = [r"\[.*@.*\]\s*[#$]|Password:|.*\s*DBRNWHSB=# "]
                old_prompt = il_connections.set_prompt(prompt)
                il_connections.execute_mml_without_check('zdbrnw')
                if ( db == "act" ):
                    output = il_connections.execute_mml_without_check('select count(vbts_data) from %s;' % self.actdb)
                else:
                    output = il_connections.execute_mml_without_check('select count(vbts_data) from %s;' % self.newdb)
                il_connections.execute_mml_without_check('\\q')
                il_connections.set_prompt(old_prompt)
                if "     0" in output:
                    return False
                else:
                    return True
            else:
                if ( db == "act" ):
                    output = IpaMml.connections.execute_mml_without_check( "ZDFB:OMU,%d:%s:0;" % (0, self.actfile))
                else:
                    output = IpaMml.connections.execute_mml_without_check( "ZDFB:OMU,%d:%s:0;" % (0, self.newfile))
                if "00000000  R" in output:
                    return True
                else:
                    return False

    class ObjectInfoClass_CMOB(ObjectInfoClass):
        """
        Object Info Class for CMOB
        """
        def object_exists_in_db(self,db="act"):
            """
            Returns True or False
            """
            if TestResources.ismcRNC():
                prompt = [r"\[.*@.*\]\s*[#$]|Password:|.*\s*DBRNWHSB=# "]
                old_prompt = il_connections.set_prompt(prompt)
                il_connections.execute_mml_without_check('zdbrnw')
                if ( db == "act" ):
                    output = il_connections.execute_mml_without_check('select cmob_id from %s where cmob_id=4;'%self.actdb)
                else:
                    output = il_connections.execute_mml_without_check('select cmob_id from %s where cmob_id=4;'%self.newdb)
                il_connections.execute_mml_without_check('\\q')
                il_connections.set_prompt(old_prompt)
                if "(0 rows)" in output:
                    return False
                else:
                    return True
            else:
                if ( db == "act" ):
                    output = IpaMml.connections.execute_mml_without_check( "ZDFB:OMU,%d:%s:3;" % (0, self.actfile))
                else:
                    output = IpaMml.connections.execute_mml_without_check( "ZDFB:OMU,%d:%s:3;" % (0, self.newfile))
                if "00000000        R" in output:
                    return True
                else:
                    return False

    objectInfo = {"RNC":    ObjectInfoClass("RNC",actdb="act_rncgen",newdb="new_rncgen",delete_with_plan=False,actfile="09F20001",newfile="09F20101",required_objects=[]),
                  "RNFC":   ObjectInfoClass("RNFC",delete_with_plan=False,actfile="09F200F5",newfile="09F201F5",required_objects=["RNC"]),
                  "RNMOBI": ObjectInfoClass("RNMOBI",delete_with_plan=False,actfile="09F200F7",newfile="09F201F7",required_objects=["RNC"]),
                  "RNAC":   ObjectInfoClass("RNAC",delete_with_plan=False,actfile="09F200F1",newfile="09F201F1",required_objects=["RNC"]),
                  "RNRLC":  ObjectInfoClass("RNRLC",delete_with_plan=False,actfile="09F200F3",newfile="09F201F3",required_objects=["RNC"]),
                  "RNPS":   ObjectInfoClass("RNPS",delete_with_plan=False,actfile="09F200F2",newfile="09F201F2",required_objects=["RNC"]),
                  "RNHSPA": ObjectInfoClass("RNHSPA",delete_with_plan=False,actfile="09F200F6",newfile="09F201F6",required_objects=["RNC"]),
                  "RNTRM":  ObjectInfoClass("RNTRM",delete_with_plan=False,actfile="09F200F4",newfile="09F201F4",required_objects=["RNC"]),
                  "WBTS":   ObjectInfoClass("WBTS",actfile="09F20002",newfile="09F20102",required_objects=["TQM", "WSMLC"]),
                  "WCEL":   ObjectInfoClass_WCEL("WCEL",actdb="act_wcel",newdb="new_wcel",actfile="09F20003",newfile="09F20103",dbid="wbts_id,lcr_id,cid",required_objects=["WBTS", "FMCS","FMCL","FMCI","FMCG","IUO","IUCS","WRAB"]),
                  "COCO":   ObjectInfoClass("COCO",actfile="09F20004",newfile="09F20104",cRNC_only=True),
                  "ADJI":   ObjectInfoClass("ADJI",actfile="09F2000C",newfile="09F2010C",required_objects=["WCEL", "HOPI"]),
                  "ADJS":   ObjectInfoClass("ADJS",actfile="09F2000B",newfile="09F2010B",required_objects=["WCEL", "HOPS"]),
                  "ADJG":   ObjectInfoClass("ADJG",actfile="09F2000D",newfile="09F2010D",required_objects=["WCEL", "HOPG"]),
                  "FMCS":   ObjectInfoClass("FMCS",actfile="09F2000E",newfile="09F2010E"),
                  "FMCI":   ObjectInfoClass("FMCI",actfile="09F2000F",newfile="09F2010F"),
                  "FMCG":   ObjectInfoClass("FMCG",actfile="09F20010",newfile="09F20110"),
                  "FMCL":   ObjectInfoClass("FMCL",actfile="09F200F8",newfile="09F201F8"),
                  "HOPS":   ObjectInfoClass("HOPS",actfile="09F20011",newfile="09F20111"),
                  "HOPI":   ObjectInfoClass("HOPI",actfile="09F20012",newfile="09F20112"),
                  "HOPG":   ObjectInfoClass("HOPG",actfile="09F20013",newfile="09F20113"),
                  "WLCSE":  ObjectInfoClass("WLCSE",actfile="09F20016",newfile="09F20116",required_objects=["WSMLC"]),
                  "WSMLC":  ObjectInfoClass_WSMLC("WSMLC",actfile="09F20015",newfile="09F20115"),
                  "WSG":    ObjectInfoClass("WSG",actfile="09F20017",newfile="09F20117",required_objects=["WANE"]),
                  "WANE":   ObjectInfoClass("WANE",actfile="09F20018",newfile="09F20118"),
                  "CMOB":   ObjectInfoClass_CMOB("CMOB",actfile="09F2001C",newfile="09F2011C"),
                  "IPQM":   ObjectInfoClass("IPQM",actfile="09F200E0",newfile="09F201E0"),
                  "IUR":    ObjectInfoClass("IUR",actfile="09F200E1",newfile="09F201E1"),
                  "WRAB":   ObjectInfoClass("WRAB",actfile="09F200E3",newfile="09F201E3"),
                  "ADJD":   ObjectInfoClass("ADJD",actfile="09F200E4",newfile="09F201E4",required_objects=["WCEL", "HOPS"]),
                  "IPNB":   ObjectInfoClass("IPNB",actfile="09F200E5",newfile="09F201E5"),
                  "TQM":    ObjectInfoClass("TQM",actfile="09F200E7",newfile="09F201E7"),
                  "VBTS":   ObjectInfoClass_VBTS("VBTS",actfile="09F200E8",newfile="09F201E8"),
                  "VCEL":   ObjectInfoClass("VCEL",actfile="09F200E9",newfile="09F201E9",dbid="wac_id",required_objects=["VBTS", "WRAB", "FMCI", "FMCG", "FMCS", "HOPI", "HOPG", "HOPS","WAC"]),
                  "ADJL":   ObjectInfoClass("ADJL",actfile="09F200C7",newfile="09F201C7",required_objects=["WCEL", "HOPL"]),
                  "HOPL":   ObjectInfoClass("HOPL",actfile="09F200C8",newfile="09F201C8"),
                  "IUO":    ObjectInfoClass("IUO",actfile="09F200D1",newfile="09F201D1"),
                  "PFL":    ObjectInfoClass("PFL",actfile="09F200D7",newfile="09F201D7"),
                  "WAC":    ObjectInfoClass("WAC",actfile="09F200FA",newfile="09F201FA"),
                  "PRNC":   ObjectInfoClass("PRNC",delete_with_plan=False,actfile="09F2030D",newfile="09F2040D"),
                  "RNCSRV": ObjectInfoClass("RNCSRV",delete_with_plan=False,actfile="09F2030F",newfile="09F2040F",actdb="act_rncserv",newdb="new_rncserv",dbid="rncserv_id"),
                  "DATSYN": ObjectInfoClass("DATSYN",delete_with_plan=False,actfile="09F20310",newfile="09F20410"),
                  "BKPRNC": ObjectInfoClass("BKPRNC",actfile="09F2030E",newfile="09F2040E"),
                  "PREBTS": ObjectInfoClass("PREBTS",actfile="09F200F9",newfile="09F201F9",cRNC_only=True),
                  "ADJE":   ObjectInfoClass("ADJE",actfile="09F20311",newfile="09F20411",required_objects=["ADJL"]),
                  "WDEV":   ObjectInfoClass("WDEV",actfile="09F20315",newfile="09F20415"),
                  "RNCERM": ObjectInfoClass("RNCERM",mcRNC_only=True),
                  "CBCI":   ObjectInfoClass("CBCI",actdb="act_cbc",newdb="new_cbc",actfile="09F200D3",newfile="09F201D3",dbid="cbc_id",required_objects=["IUO"]),
                  "IUCSIP": ObjectInfoClass_IUCSIP("IUCSIP",actdb="act_iuip",newdb="new_iuip",actfile="09F200D2",newfile="09F201D2",dbid="iuip_id",required_objects=["IUCS","IPQM"]),
                  "IUPSIP": ObjectInfoClass_IUPSIP("IUPSIP",actdb="act_iuip",newdb="new_iuip",actfile="09F200D2",newfile="09F201D2",dbid="iuip_id",required_objects=["IUPS","IPQM"]),
                  "IUCS":   ObjectInfoClass_IUCS("IUCS",actdb="act_iu",newdb="new_iu",actfile="09F200E2",newfile="09F201E2",dbid="iu_item_id",required_objects=["IUO"]),
                  "IUPS":   ObjectInfoClass_IUPS("IUPS",actdb="act_iu",newdb="new_iu",actfile="09F200E2",newfile="09F201E2",dbid="iu_item_id",required_objects=["IUO","IUCS"]),
                 }
    
    featureInfo = { 0   : "Inter System Handover",
                    1   : "Location Services - RTT",
                    2   : "IMSI Based Handover",
                    3   : "WCDMA 1900",
                    4   : "Multiple Core Networks Support",
                    5   : "Multi-operator RAN",
                    6   : "Service Area Broadcast",
                    7   : "Emergency Inter System Handover",
                    8   : "HSDPA, ChSw, UL DPCHSch, ResumpT and DirRRCConSetu",
                    9   : "WCDMA 850",
                    10  : "Enhanced Priority Based Scheduling and OLC",
                    11  : "Configurable Ranges for User Throughput Counters",
                    12  : "UE based A-GPS",
                    13  : "Network based A-GPS",
                    14  : "Intelligent Emergency Inter System Handover",
                    15  : "Connectivity Support for 512 BTSs",
                    16  : "Load and Service Based Handover",
                    17  : "Power Balancing",
                    18  : "Support for Tandem/Transcoder Free Operation",
                    19  : "AMR Codec Sets [12.2, 7.95, 5.90, 4.75] & [5.90, 4.75]",
                    20  : "Wideband AMR Codec Set [12.65, 8.85, 6.6]",
                    21  : "Throughput Based Optimisation of PS Algorithm",
                    22  : "Flexible Upgrade of NRT DCH Data Rate",
                    23  : "Route Selection",
                    24  : "WCDMA 1.7/2.1GHz",
                    25  : "WCDMA 1.7 and 1.8GHz",
                    26  : "Radio Network Access Regulation",
                    27  : "HSDPA Mob, SHO, SCC and Soft/softer HO for DPCH",
                    28  : "HSPA+ over Iur",
                    29  : "HSDPA with AMR ",
                    30  : "WCDMA 900",
                    31  : "Extended Cell \"60km\"",
                    32  : "Flexible Connection of VPCs for WBTS",
                    33  : "Wireless Priority Service",
                    34  : "Full WCDMA 1900 UARFCN range",
                    35  : "Transport Bearer Tuning",
                    36  : "Path Selection",
                    37  : "HSDPA Dynamic Resource Allocation",
                    38  : "HSDPA 10 Codes",
                    39  : "HSDPA 15 Codes",
                    40  : "HSDPA layering for UEs in common channels",
                    41  : "HSDPA Code multiplexing",
                    42  : "16 kbps Return Ch DCH Data Rate Support for HSDPA",
                    43  : "HSDPA 48 users per cell",
                    44  : "Flexible IU",
                    45  : "Dynamic Scheduling for HSDPA with Path Selection",
                    46  : "Dynamic Scheduling for NRT DCH with Path Selection",
                    47  : "Emergency Call Redirect to GSM",
                    48  : "HSUPA with simultaneous AMR voice call",
                    49  : "HSUPA Basic 3 users per BTS",
                    50  : "HSUPA Basic 12 users per BTS",
                    51  : "HSUPA Basic 24 users per BTS",
                    52  : "RNC GUI for BTS Connection Resources",
                    53  : "Connectivity Support for 600 BTSs",
                    54  : "RNC Iu Link Break Protection",
                    55  : "HSDPA 10 Mbps per User",
                    56  : "HSPA Inter RNC Cell Change",
                    57  : "HSUPA 2.0 Mbps",
                    58  : "Extended Cell \"35 km\"",
                    59  : "Extended Cell \"180km\"",
                    60  : "Capacity license for the number of carriers",
                    61  : "IP based Iu-CS",
                    62  : "IP based Iu-PS",
                    63  : "HSDPA Congestion Control",
                    64  : "IP Based Iur",
                    65  : "SAS Centric Iupc",
                    66  : "Automated Definition of Neighbouring Cell",
                    67  : "Detected Set Reporting and Measurements",
                    68  : "Detected Set Reporting Based SHO",
                    69  : "NodeB RAB Reconfig Support",
                    70  : "QoS Aware HSPA Scheduling",
                    71  : "Streaming QoS for HSPA",
                    72  : "HSUPA Basic 60 users per BTS",
                    73  : "NRT Multi-RABs on HSPA",
                    74  : "HSDPA 14 Mbps per User",
                    75  : "IP Based Iub",
                    76  : "Dual Iub",
                    77  : "HSDPA inter-frequency handover",
                    78  : "Directed Retry of AMR call",
                    79  : "HSDPA 64 Users per Cell",
                    80  : "LCS Support in Drift RNC",
                    81  : "Iub Transport QOS",
                    82  : "Secure BTS Management Interface",
                    83  : "UTRAN-GAN Interworking",
                    84  : "LCS periodical reporting",
                    85  : "LCS Shape Conversion",
                    86  : "Satellite Iub",
                    87  : "Inter-frequency Handover over Iur",
                    88  : "I-BTS Sharing",
                    89  : "Multi-Operator Core Network",
                    90  : "CS Voice Over HSPA",
                    91  : "Power Saving Mode for BTS",
                    92  : "Fractional DPCH",
                    93  : "HSUPA 5.8 Mbps",
                    94  : "HSUPA 2ms TTI",
                    95  : "HSDPA 64QAM",
                    96  : "Continuous Packet Connectivity",
                    97  : "Broadcast of A-GPS Assistance Data",
                    98  : "HSPA Transport Fallback",
                    99  : "Position Information in Subscriber Trace Report",
                    100 : "24 kbps Paging Channel",
                    101 : "HSPA 72 Users Per Cell",
                    102 : "BTS Auto Connection",
                    103 : "Common Channel Setup",
                    104 : "MIMO",
                    106 : "Dual-Cell HSDPA 42Mbps",
                    107 : "LTE Interworking-Cell Reselection to LTE",
                    108 : "LTE Interworking-ISHO from LTE",
                    109 : "HSUPA 16QAM",
                    110 : "HSPA 128 users",
                    111 : "Multi-Band Load Balancing",
                    112 : "HS-FACH",
                    114 : "Bandwidth utilization classes counters for IP",
                    120 : "RNC2600 Capacity Increase for Smartphones",
                    121 : "Inter Circle Roaming",
                    122 : "PCAP for CellID Measurement Method",
                    123 : "Enhanced Virtual Antenna Mapping",
                    124 : "Fast Dormancy Profiling",
                    125 : "HSPA conversational QoS",
                    126 : "Smart LTE Layering",
                    127 : "Layering in RRC Connection Release",
                    128 : "Application Aware RAN",
                    129 : "Dual Band HSDPA 42 Mbps",
                    130 : "Fast Cell_PCH Switching",
                    131 : "3GPP Rel8 CBS ETWS support",
                    132 : "Fast HSPA Mobility",
                    133 : "AMR with DCH \"0, 0\" Support for Iur",
                    134 : "Optimised push to talk experience",
                    135 : "UE Periodic Measurement Report",
                    136 : "Automatic Access Class Restriction",
                    137 : "Selective BTS Resource Re-balancing in mcRNC",
                    138 : "SAB Support with 2 SCCPCHs",
                    139 : "Femto Handover Control",
                    140 : "Terminal Battery Drain Prevention in Cell Broadcas",
                    141 : "Mass Event Handler",
                    142 : "Voice Call Priorization during High Traffic Load",
                    143 : "High Speed Cell FACH Uplink",
                    144 : "CPC for 128 HSPA Users",
                    145 : "RRC connection Setup Redirection",
                    146 : "RNC Resiliency",
                    147 : "DC-HSUPA",
                    148 : "Multi-Cell HSDPA",
                    149 : "RABActFail and AccessFail due to UE after StateTra",
                    150 : "MultiRAB Handling with Ericsson in SRNS Relocation",
                    151 : "Improved CS CallSetup Attempts Starting FACH/PCH",
                    152 : "MultiRABSRNS Relocation Incompatibility with Huaw ",
                    153 : "UEs Handling Measurement Events e6f/e6g Incorectly",
                    154 : "Load Based AMR Codec Selection Causing Mute Call",
                    155 : "Data Session Profiling",
                    156 : "WCDMA and GSM Layer Priorities",
                    157 : "HSUPA CM for LTE and IF Handover",
                    158 : "Measurement Based LTE Layering",
                    159 : "Smart LTE Handover",
                    182 : "Point-to-Point Iu-pc Interface",
                    224 : "Subscriber Trace",
                    225 : "AMR Codec Set for 2G-3G TrFO",
                    226 : "BTS load based AACR",
                    227 : "In-Bearer Application Optimization",
                    228 : "CSFB with RIM",
                    232 : "RACH capacity increase" 
                }

    def get_object_info(self,obj):
        """
        Returns the ObjectInfoClass instance.
        """
        try:
            return self.objectInfo[obj]
        except:
            raise AssertionError('No support for object %s, yet?'%obj)

    def object_exists_in_db(self,obj,db="act"):
        """
        Returns True or False
        """
        object_info = self.get_object_info(obj)
        return object_info.object_exists_in_db(db)

    def create_atm_interface_if_needed(self):
        """
        Create ATM interface 1 which is needed in coco test
        Assuming that NPS1,0 is available, though could work
        also with other type of interface cards.
        """
        interfaces = IpaMml.broadband_admin_lib.interrogate_atm_interface(interface_id_or_range="1")
        if '1' in interfaces:
            return

        #check interface type(NIP1, A2SU; NPS1; NPS1P)
        units = IpaMml.units_lib.get_units("","FULL")
        if 'NIP1-0' in units:
            interface_type = 'NIP1-0'
            IpaMml.units_lib.unit_should_be_in_state('A2SU-0', 'WO-EX')
        elif 'NPS1P-0' in units:
            interface_type = 'NPS1P-0'
            IpaMml.units_lib.unit_should_be_in_state('NPS1P-1', 'SP-EX')
        else:
            interface_type = 'NPS1-0'
        
        IpaMml.units_lib.unit_should_be_in_state(interface_type, 'WO-EX')
        u = IpaMml.units_lib.get_units(interface_type.replace("-",","))
        keys = u.keys()
        keys.sort()
        for k in keys:
            if 'SET-' in k:
                set_nbr = k[4:]
                break
        else:
            raise AssertionError('No NIP1/NPS1/NPS1P sets???')
        # Phy id 3
        if interface_type == 'NPS1P-0':
            IpaMml.pif_lib.sdh_protection._create_SDH_protection_group('1','0','8')
            IpaMml.pif_lib.create_phyTTP_on_PROTGROUP('3', '1')
        else:
            IpaMml.pif_lib.create_phyTTP_on_SET('3', set_nbr)
        # atm interface id 1 to phy 3
        IpaMml.broadband_admin_lib.create_atm_interface('1' ,'UNI', '3')
        IpaMml.broadband_admin_lib.create_access_profile('1','8','8')

    def remove_vpi_vci_from_use(self,interface,vpi,vci):
        if TestResources.ismcRNC():
            return
        IpaMml.connections.execute_mml_without_check( "ZLCS:%s,%s,%s:LOCK;"%(interface,vpi,vci) )
        IpaMml.connections.execute_mml_without_check( "ZLCD:%s,%s,%s;"%(interface,vpi,vci) )

    def metadata_connect_to_ipa(self, ipaddress='10.16.28.89', username = 'SYSTEM', passwd = 'SYSTEM'):
        """
        Connect to cRNC test bench.
        """
        IpaMml.connections.connect_to_ipa(host=ipaddress, user=username, passwd=passwd)
        IpaMml.connections._get_current_connection()

    def metadata_disconnect_from_ipa(self):
        """
        Disconnect from cRNC test bench.
        """
        IpaMml.connections.disconnect_from_ipa()

    def metadata_connect_to_mc(self, ipaddress='10.16.51.11', username='root', passwd='password'):
        """
        Connect to mcRNC test bench.
        """

        self._metadata_connection = il_connections.connect_to_il(ipaddress, user = username, passwd = passwd)
        # Modify the MML execution routine to one
        # that catches the exception so that the Robot
        # does not fail
        global org_execute_mml
        org_execute_mml = il_connections.execute_mml
        il_connections.execute_mml = self.my_exec_mml
        # Increase the command execution timeout
        # This may need to be modified so that the run_test keyword
        # would set this according to the wait time
        il_connections.set_mml_timeout('1200sec')

    def setResouceVariables(self, varsOfResource):
        TestResources.setVariables(varsOfResource)

    def metadata_connect(self):
        """
        Connect to metadata test bench.
        After connection the user can execute command line commands using
        connections.execute_mml function.
        
        | Input Parameters | Man. | Description |
        No input parameters needed
        
        Following lines needs to be added in CM/Common/FOOLIB/resources/TestResources.py:
        
        cRNC: 
        classicTestResource('10.68.145.82', {'IPADDRESS': '10.68.145.82', 'IPADDRESS1': '10.68.145.83', 'OMSIPADDRESS': '10.68.145.180', 'RNC-ID': 'RNC-63', 'RNC-NAME': 'cRNC-63'}),
        
        mcRNC:
        mcTestResource('10.69.44.137', {'IPADDRESS': '10.69.44.137', 'IPADDRESS1': '10.69.44.138', 'OMSIPADDRESS': '10.68.145.180', 'RNC-ID': 'RNC-76', 'RNC-NAME': 'mcRNC-76'}),


        """
        atexit.register(self.metadata_disconnect)
        self._metadata_connected = True
        print '*INFO* Connnected to metadata testbench'
        res = TestResources.getResources()
        if TestResources.ismcRNC():
            self.metadata_connect_to_mc(res['IPADDRESS'], res['USERNAME'], res['PASSWORD'])
        else:
            self.metadata_connect_to_ipa(res['IPADDRESS'], res['USERNAME'], res['PASSWORD'])

    def start_profilation(self):
        """
        Start profiling, if the PROFILATION variable in resources is 'Y'.
        Otherwise this keyword has no effects.
        """
        activate_profilation = TestResources.getResources('PROFILATION')
        if(activate_profilation == 'Y'):
            if TestResources.ismcRNC():
                profiling_utils().init_profiling_mc()
                profiling_utils().start_profiling_mc()
            else:
                IpaMml.connections.execute_mml_without_check("ZAFB:2005:OMU;", 'Y')
                self.execute_service_terminal_commands(['ZL:6','ZLEL:6:,W0-BLCODE/PRQFILGX.IMG','Z6S:RAY','Z6S:PAB','Z6S:FOO','Z6S:ZHU'])
                self.execute_service_terminal_commands(['Z6P:FOO','Z6P:RAY','Z6P:PAB','Z6P:ZHU'])

    def stop_profilation(self):
        """
        Stop profiling, if the PROFILATION variable in resources is 'Y'.
        Otherwise this keyword has no effects.
        """      
        output = ""
        profilation_active = TestResources.getResources('PROFILATION')
        if(profilation_active == 'Y'):
            if TestResources.ismcRNC() == False:
                self.execute_service_terminal_commands(['Z6S:FOO','Z6S:ZHU','Z6S:RAY','Z6S:PAB'])
                output = self.execute_service_terminal_commands(['Z6V:FOO','Z6V:ZHU','Z6V:RAY','Z6V:PAB'])
                IpaMml.connections.execute_mml_without_check("ZAFU:2005:OMU;")
            else:
                profiling_utils().stop_profiling_mc()
                output = profiling_utils().get_profiling_result_mc()

        return output

    def metadata_suite_setup(self):
        """
        Test bench specific setups and other stuff
        """
        if TestResources.ismcRNC():
            self.run_cmd('export LD_LIBRARY_PATH=%s' % TestResources.getResources('LIBRARY_PATH') )
            # By default only error (and higher) level IL logs are forwarded to syslog
            #self.run_cmd('fsclish -c "set troubleshooting app-log rule rule-id default keep level notice unit OMU-0"')
        else:
            self.prevent_rnwdb_updates_to_disk()
            self.unlink_crnc_extensions()
            self.execute_service_terminal_commands(['ZL:5', 'ZLEL:5:,W0-BLCODE/JONDOEQX.IMG'])

            load_xml = TestResources.getResources('AUTOLOAD_XML')
            if(load_xml == 'Y'):
                if(os.path.exists("test_files")):
                    self.ftp_put_a_file("test_files", TestResources.getResources('XML_PATH'))


    def metadata_suite_teardown(self):
        pass

    def set_connection_timeout(self, val):
        il_connections.set_mml_timeout(val)

    def metadata_disconnect_mc(self):
        """
        Disconnect from mcRNC test bench
        """
        if hasattr(self, '_metadata_connection'):
            il_connections.disconnect_from_il()
            del self._metadata_connection
            print '*INFO* disconnected from metadata testbench'
        global org_execute_mml
        if org_execute_mml != None:
            il_connections.execute_mml = org_execute_mml
            org_execute_mml = None

    def metadata_disconnect(self):
        """
        Disconnect from metadata test bench.
        """
        print 'Disconnecting'
        if TestResources.ismcRNC():
            self.metadata_disconnect_mc()
        else:
            self.metadata_disconnect_from_ipa()

    def ftp_get_a_file(self, remote_name, local_name):
        """
        Get a file from the curent cRNC test bench using ftp
        """
        ftp_url = "ftp://" + TestResources.getResources('IPADDRESS') + remote_name
        username = TestResources.getResources('USERNAME')
        password = TestResources.getResources('PASSWORD')
        Utils.ftp_lib.download_from_ftp_to_local(ftp_url, local_name, 'bin', username, password)

    def ftp_put_a_file(self, local_name, remote_name):
        """
        Put a file to the current cRNC test bench using ftp.
        """
        ftp_url = "ftp://" + TestResources.getResources('IPADDRESS') + remote_name
        username = TestResources.getResources('USERNAME')
        password = TestResources.getResources('PASSWORD')
        print "url='%s' local_name='%s'" % (ftp_url, local_name)
        Utils.ftp_lib.upload_to_ftp_from_local(ftp_url, local_name, 'bin', username, password)


    def copy_rnc_xml_files(self, host, usrname, pwd, rnc_id='', isoms=''):
        """
        This keyword check if xml files in mcRNC.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        print base_dir
        old_dir = plan_generate.plan_generate().get_old_dir(base_dir)
        print old_dir
        new_dir = plan_generate.plan_generate().get_new_directory_of_topology(base_dir)
        print new_dir
        new_rnc_id = rnc_id
        print new_rnc_id
        oms_file=new_rnc_id+'RNWTopology.XML.gz'
        oms_xml_file = new_rnc_id+'RNWTopology.XML'
        # oms_file = 'RNWTopology.XML'
        # i=0
        # for k in 'RNWTopology.XML':
        #     rnc_id[3+i]=oms_file[i]
        #     i=i+1
        # oms_file = rnc_id
        print oms_file
        local_modified_time_file_path = plan_generate.plan_generate().get_modified_time_file_path(new_dir)
        if os.path.exists(local_modified_time_file_path):
            os.remove(local_modified_time_file_path)
        if not isoms:
            remote_dir = '/mnt/QNOMU/topology'
            remote_modified_time_file_path = '/mnt/QNOMU/topology/RNWTopology.XML.gz'
            # xml_command='ls -l RNWTopology.XML'
            # print os.popen(xml_command)
            # val = os.system("ls -al RNWTopology.XML.gz")
            val = 1
            # print val
            if val:
                os.remove('%s/RNWTopology.XML' % new_dir)
            try:
                #output = self.run_cmd('ls %s' %remote_modified_time_file_path)
                print base_dir, remote_modified_time_file_path
                #self.sftp_get_a_file(local_modified_time_file_path, remote_modified_time_file_path)
            except:
                print 'remote modified time file %s not found on mcRNC' % remote_modified_time_file_path
            #copy_list = plan_generate.plan_generate().check_copy_needed(old_dir, new_dir, new_rnc_id)
            #print copy_list
        #     #if len(copy_list) > 0:
            if 1 > 0:
                print "start copying..."
                output = self.check_directory_exist(remote_dir)
                print output
                if 'No such file or directory' in output:
                    self.run_cmd('mkdir %s' %remote_dir)
                for file_name in 'RNWTopology.XML.gz':
                    if (':' in new_dir):
                        local_path = "%s\\%s"%(new_dir, 'RNWTopology.XML.gz')
                    else:
                        local_path = "%s/%s"%(new_dir, 'RNWTopology.XML.gz')
                    remote_path = "%s/%s"%(remote_dir, 'RNWTopology.XML.gz')
                    print local_path, remote_path
                #     self.sftp_put_a_file(local_path, remote_path)
                #self.sftp_put_a_file(local_modified_time_file_path, remote_modified_time_file_path)
                #self.get_xml_file(host, usrname, pwd, remote_path, local_path)
                #self.sftp_get_a_file_from_rnc(local_path, remote_path)
                server = '10.69.251.43'
                username = 'root'
                password = 'root'
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                ssh.connect(server, username=username, password=password)
                sftp = ssh.open_sftp()

                sftp.get(remote_path, local_path)

                sftp.close()
                ssh.close()


                print "complete copy"
                xml_file = self.extract(local_path)
                print xml_file
                print "complete extract"
        else:
            remote_dir = '/var/mnt/local/omsdata/OMSftproot/topology_upload_files'
            remote_modified_time_file_path = '/var/mnt/local/omsdata/OMSftproot/topology_upload_files/%s' % oms_file
            print remote_modified_time_file_path
            val = os.system("ls -al %s" %oms_xml_file)
            print val
            new_dir_file =new_dir+'/'+oms_xml_file
            print new_dir_file
            if val:
                os.remove('%s' % new_dir_file)
            # if '152RNWTopology.XML':
            #     os.remove('%s/152RNWTopology.XML' % new_dir)
            try:
                #output = self.run_cmd('ls %s' %remote_modified_time_file_path)
                print base_dir, remote_modified_time_file_path
                #self.sftp_get_a_file(local_modified_time_file_path, remote_modified_time_file_path)
            except:
                print 'remote modified time file %s not found on mcRNC' % remote_modified_time_file_path
            #copy_list = plan_generate.plan_generate().check_copy_needed(old_dir, new_dir, new_rnc_id)
            #print copy_list
        #     #if len(copy_list) > 0:
            if 1 > 0:
                print "start copying..."
                output = self.check_directory_exist(remote_dir)
                print output
                # if 'No such file or directory' in output:
                #     self.run_cmd('mkdir %s' %remote_dir)
                for file_name in '152RNWTopology.XML.gz':
                    if (':' in new_dir):
                        local_path = "%s\\%s"%(new_dir, '152RNWTopology.XML.gz')
                    else:
                        local_path = "%s/%s"%(new_dir, '152RNWTopology.XML.gz')
                    remote_path = "%s/%s"%(remote_dir, '152RNWTopology.XML.gz')
                    print local_path, remote_path
                #     self.sftp_put_a_file(local_path, remote_path)
                #self.sftp_put_a_file(local_modified_time_file_path, remote_modified_time_file_path)
                #self.get_xml_file(host, usrname, pwd, remote_path, local_path)
                self.sftp_get_a_file_from_oms(local_path, remote_path)
                print "complete copy"
                xml_file = self.extract(local_path)
                print xml_file
                print "complete extract"
        return xml_file

    def copy_oms_xml_files(self, host, usrname, pwd, rnc_id='', isoms=''):
        """
        This keyword check if xml files in mcRNC.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        print base_dir
        old_dir = plan_generate.plan_generate().get_old_dir(base_dir)
        print old_dir
        new_dir = plan_generate.plan_generate().get_new_directory_of_topology(base_dir)
        print new_dir
        new_rnc_id = rnc_id
        print new_rnc_id
        oms_file=new_rnc_id+'RNWTopology.XML.gz'
        oms_xml_file = new_rnc_id+'RNWTopology.XML'
        # oms_file = 'RNWTopology.XML'
        # i=0
        # for k in 'RNWTopology.XML':
        #     rnc_id[3+i]=oms_file[i]
        #     i=i+1
        # oms_file = rnc_id
        print oms_file
        local_modified_time_file_path = plan_generate.plan_generate().get_modified_time_file_path(new_dir)
        if os.path.exists(local_modified_time_file_path):
            os.remove(local_modified_time_file_path)
        if not isoms:
            remote_dir = '/mnt/QNOMU/topology'
            remote_modified_time_file_path = '/mnt/QNOMU/topology/RNWTopology.XML.gz'
            # xml_command='ls -l RNWTopology.XML'
            # print os.popen(xml_command)
            # val = os.system("ls -al RNWTopology.XML.gz")
            # print val
            # if val:
            #     os.remove('%s/RNWTopology.XML' % new_dir)
            try:
                #output = self.run_cmd('ls %s' %remote_modified_time_file_path)
                print base_dir, remote_modified_time_file_path
                #self.sftp_get_a_file(local_modified_time_file_path, remote_modified_time_file_path)
            except:
                print 'remote modified time file %s not found on mcRNC' % remote_modified_time_file_path
            #copy_list = plan_generate.plan_generate().check_copy_needed(old_dir, new_dir, new_rnc_id)
            #print copy_list
        #     #if len(copy_list) > 0:
            if 1 > 0:
                print "start copying..."
                output = self.check_directory_exist(remote_dir)
                print output
                if 'No such file or directory' in output:
                    self.run_cmd('mkdir %s' %remote_dir)
                for file_name in 'RNWTopology.XML.gz':
                    if (':' in new_dir):
                        local_path = "%s\\%s"%(new_dir, 'RNWTopology.XML.gz')
                    else:
                        local_path = "%s/%s"%(new_dir, 'RNWTopology.XML.gz')
                    remote_path = "%s/%s"%(remote_dir, 'RNWTopology.XML.gz')
                    print local_path, remote_path
                #     self.sftp_put_a_file(local_path, remote_path)
                #self.sftp_put_a_file(local_modified_time_file_path, remote_modified_time_file_path)
                #self.get_xml_file(host, usrname, pwd, remote_path, local_path)
                self.sftp_get_a_file_from_rnc(local_path, remote_path)
                print "complete copy"
                xml_file = self.extract(local_path)
                print xml_file
                print "complete extract"
        else:
            remote_dir = '/var/mnt/local/omsdata/OMSftproot/topology_upload_files'
            remote_modified_time_file_path = '/var/mnt/local/omsdata/OMSftproot/topology_upload_files/%s' % oms_file
            print remote_modified_time_file_path
            # val = os.system("ls -al %s" %oms_xml_file)
            val = 1
            # print val
            new_dir_file =new_dir+'/'+oms_xml_file
            print new_dir_file
            if val:
                os.remove('%s' % new_dir_file)
            # if '152RNWTopology.XML':
            #     os.remove('%s/152RNWTopology.XML' % new_dir)
            try:
                #output = self.run_cmd('ls %s' %remote_modified_time_file_path)
                print base_dir, remote_modified_time_file_path
                #self.sftp_get_a_file(local_modified_time_file_path, remote_modified_time_file_path)
            except:
                print 'remote modified time file %s not found on mcRNC' % remote_modified_time_file_path
            #copy_list = plan_generate.plan_generate().check_copy_needed(old_dir, new_dir, new_rnc_id)
            #print copy_list
        #     #if len(copy_list) > 0:
            if 1 > 0:
                print "start copying..."
                output = self.check_directory_exist(remote_dir)
                print output
                # if 'No such file or directory' in output:
                #     self.run_cmd('mkdir %s' %remote_dir)
                for file_name in '152RNWTopology.XML.gz':
                    if (':' in new_dir):
                        local_path = "%s\\%s"%(new_dir, '152RNWTopology.XML.gz')
                    else:
                        local_path = "%s/%s"%(new_dir, '152RNWTopology.XML.gz')
                    remote_path = "%s/%s"%(remote_dir, '152RNWTopology.XML.gz')
                    print local_path, remote_path
                #     self.sftp_put_a_file(local_path, remote_path)
                #self.sftp_put_a_file(local_modified_time_file_path, remote_modified_time_file_path)
                #self.get_xml_file(host, usrname, pwd, remote_path, local_path)
                #self.sftp_get_a_file_from_oms(local_path, remote_path)
                server = '10.68.157.184'
                username = 'root'
                password = 'root'
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                ssh.connect(server, username=username, password=password)
                sftp = ssh.open_sftp()

                sftp.get(remote_path, local_path)

                sftp.close()
                ssh.close()
                print "complete copy"
                xml_file = self.extract(local_path)
                print xml_file
                print "complete extract"
        return xml_file

    def extract(self, file_name):
        cmd = "gzip -d %s" %file_name
        xml_file = file_name.strip().lstrip().rstrip('.gz')
        os.popen(cmd)
        return xml_file

    def get_xml_file(self, host, usrname, pwd, remote_name, local_name):
        '''
        Get a xml file from mcRNC or OMS for topology test.
        '''
        server = host
        username = 'root'
        password = pwd
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh.connect(server, username=username, password=password)
        sftp = ssh.open_sftp()

        #sftp.get(remote_name, local_name)

        sftp.close()
        ssh.close()

    def sftp_get_a_file_from_rnc(self, local_name, remote_name):
        """
        Get a file from the current mcRNC test bench using ssh and sftp.
        """
        server = '10.69.251.43'
        username = 'root'
        password = 'root'
        #os.system("scp -r %s %s@%s:%s" % (local_name, user_name, server, remote_name))
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh.connect(server, username=username, password=password)
        sftp = ssh.open_sftp()

        sftp.get(remote_name, local_name)

        sftp.close()
        ssh.close()

    def sftp_get_a_file_from_oms(self, local_name, remote_name):
        """
        Get a file from the current mcRNC test bench using ssh and sftp.
        """
        server = '10.68.157.184'
        username = 'root'
        password = 'root'
        if local_name:
            os.remove(local_name)
        #os.system("scp -r %s %s@%s:%s" % (local_name, user_name, server, remote_name))
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh.connect(server, username=username, password=password)
        sftp = ssh.open_sftp()

        sftp.get(remote_name, local_name)

        sftp.close()
        ssh.close()


    def sftp_get_a_file(self, local_name, remote_name):
        """
        Get a file from the current mcRNC test bench using ssh and sftp.
        """
        server = TestResources.getResources('IPADDRESS')
        username = TestResources.getResources('USERNAME')
        password = TestResources.getResources('PASSWORD')
        #os.system("scp -r %s %s@%s:%s" % (local_name, user_name, server, remote_name))
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh.connect(server, username=username, password=password)
        sftp = ssh.open_sftp()

        sftp.get(remote_name, local_name)

        sftp.close()
        ssh.close()
        
    def sftp_put_a_file(self, local_name, remote_name):
        """
        Put a file to the current mcRNC test bench using ssh and sftp.
        """
        server = TestResources.getResources('IPADDRESS')
        username = TestResources.getResources('USERNAME')
        password = TestResources.getResources('PASSWORD')
        #os.system("scp -r %s %s@%s:%s" % (local_name, user_name, server, remote_name))
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh.connect(server, username=username, password=password)
        sftp = ssh.open_sftp()

        if(os.path.isdir(local_name)):
            for item in os.listdir(local_name):
                if(not os.path.isdir(os.path.join(local_name, item))):
                    sftp.put(os.path.join(local_name, item), "%s/%s" % (remote_name, item))
        else:
            sftp.put(local_name, remote_name)

        sftp.close()
        ssh.close()
        
    def upload_generated_file(self, local_name, remote_path="", remote_name=""):
        """
        Upload a file or directory from local host to test bench
        Recursive upload of directories is not supported
        """
        if(remote_path == ""):
            remote_path = TestResources.getResources('XML_PATH')

        if(local_name.find("/") != -1):
            tmp_name = local_name.rsplit( "/", 1)[1]
        else:
            tmp_name = local_name
            
        if(remote_name == ""):
            filename = tmp_name
        else:
            filename = remote_name

        if(os.path.isfile(local_name)):
            remote_name = remote_path + "/" + filename
        else:
            remote_name = remote_path
        
        base_dir = os.path.dirname(local_name)
        tmp_dir = plan_generate.plan_generate().get_new_dir(base_dir)
        tmp_name = os.path.join(tmp_dir, tmp_name)
        
        plan_generate.plan_generate().generate_a_plan_file(local_name, tmp_name)

        self.create_remote_dir_on_rnc()
        
        if TestResources.ismcRNC():
            self.sftp_put_a_file(tmp_name, remote_name)
        else:
            self.ftp_put_a_file(tmp_name, remote_name)
            
    def upload_a_file(self, local_name, remote_path="", remote_name=""):
        """
        Upload a file or directory from local host to test bench
        Recursive upload of directories not supported
        """
        if(remote_path == ""):
            remote_path = TestResources.getResources('XML_PATH')
        if not self.is_directory_exist_on_rnc(remote_path):
            self.create_remote_dir_on_rnc(remote_path)
        
        if(remote_name == ""):
            if(local_name.find("/") != -1):
                filename = local_name.rsplit( "/", 1)[1]
            else:
                filename = local_name
        else:
            filename = remote_name

        if(os.path.isfile(local_name)):
            remote_name = remote_path + "/" + filename
        else:
            remote_name = remote_path

        print "local_name, remote_name", local_name, remote_name
        if TestResources.ismcRNC():
            self.sftp_put_a_file(local_name, remote_name)
        else:
            self.ftp_put_a_file(local_name, remote_name)

    def type_a_file(self, fname):
        """
        Generic Type a file KW for getting a file content
        using cat remotely over ssh in mcRNC and in CRNC by
        downloading files over FTP inspecting the contents locally
        """
        if TestResources.ismcRNC():
            return self.run_cmd('cat ' + fname)
        else:
            local_file = "_tmp_" + fname.rsplit( "/", 1)[1]
            self.ftp_get_a_file(fname, local_file)

            with open(local_file, 'r') as content_file:
                output = content_file.read()

            os.remove(local_file)

            return output

    def delete_a_file(self, fname):
        """
        Generic Delete a file KW for removing a file from the test bench disk.
        """
        if TestResources.ismcRNC():
            return self.run_cmd('rm -rf ' + fname)
        else:
            ipa_cmd = 'ZPS:unlink,%s' % fname
            output = self.execute_service_terminal_commands(['ZL:P', 'ZLP:P,POM', ipa_cmd])
            self.execute_service_terminal_commands(['ZL:P'])
            return output

    def foolib_mem_files_check(self, unit=None):
        """
        Tests if there are any existing FOOLIB's work files, i.e. object trees.
        Raises an exception, if such a file is found.
        """
        if TestResources.ismcRNC():
            output = self.run_cmd('ls /dev/shm')
            if '_f0338' in output:
                raise AssertionError('FOOLIB memory files exist')
        else:
            ipa_cmd = 'ZFF'
            count = 10
            while count > 0:
                output = self.execute_service_terminal_commands(['ZL:F', 'ZLP:F,FUT', ipa_cmd], unit = unit)
                self.execute_service_terminal_commands(['ZL:F'], unit = unit)
                if 'FOOLIB' not in output:
                    return
                time.sleep(1)
                count = count - 1
            raise AssertionError('FOOLIB memory files exist')

    def _open_service_terminal(self, unit):
        """
        Sometimes STE.open_service_terminal does not find prompt
        """
        retry_count = 3
        while retry_count > 0:
            retry_count = retry_count - 1
            try:
                STE.open_service_terminal(unit)
                return
            except RuntimeError as e:
                if str(e) == 'no STE prompt found':
                    continue
                else:
                    break
        raise e

    def execute_service_terminal_commands(self, commands, answers="", unit=None):
        """
        Executes service terminal command(s) in given computer unit
        """
        if unit is None:
            unit = TestResources.getResources('UNIT')
        if not hasattr(commands, '__iter__'):
            commands = [commands]

        unit = unit.replace('-',',')
        self._open_service_terminal(unit)
        output = ""

        try:
            for c in commands:
                output = output + IpaMml.connections.execute_mml_without_check('%s' % c, answers)
        finally:
            STE.close_service_terminal()

        return output

    def run_cmd(self, cmd, ext = ''):
        """
        Excecute a CLI command in mcRNC
        """
        exec_cmd = cmd + " " + ext
        result = il_connections.execute_mml(exec_cmd)
        return result

    def run_jondoe_cmd(self, cmd):
        """
        Executes a JONDOE command in the current test bench.
        | Input Paramaters | Man. | Description |
        | cmd              | Yes  | Command to be run with jondoe |
        | Returned Value   |
        Command execution result is returned
        """
        if TestResources.ismcRNC():
            jdoe_path = TestResources.getResources('JONDOE_PATH')
            exec_cmd = "ilcliru.sh omu %s/jondoe -- " % (jdoe_path) + cmd
            return il_connections.execute_mml(exec_cmd)
        else:
            self.execute_service_terminal_commands(['ZL:5', 'ZLEL:5:,W0-BLCODE/JONDOEQX.IMG'])
            self.execute_service_terminal_commands('ZLEL:5:,W0-BLCODE/JONDOEQX.IMG','Y')
            unit = TestResources.getResources('UNIT')
            unit = unit.replace('-',',')
            ipa_cmd = 'Z5C:%s' % cmd.replace(' ', ',')

            STE.open_service_terminal(unit)

            try:
                output = IpaMml.connections.execute_mml_without_check("%s" % ipa_cmd)
            finally:
                STE.close_service_terminal()

            return output

    def unlink_crnc_extensions(self):
        """
        Unlink all service terminal extensions.
        """
        unit = TestResources.getResources('UNIT')
        unit = unit.replace('-',',')
        STE.open_service_terminal(unit)

        try:
            output = IpaMml.connections.execute_mml_without_check("ZL?")
            for line in output.split('\n'):
                if(line.find(".....") != -1):
                    cmd_letter = line[0]
                    if(cmd_letter != "G" ):
                        IpaMml.connections.execute_mml_without_check("ZL:%s" % cmd_letter)
        finally:
            STE.close_service_terminal()

    def my_exec_mml(self,s,*answers):
        """
        Execute MML command and catch the exception if it fails.
        If we do not catch the exception then Robot test will crash.
        """
        try:
            # The org_execute_mml points to connections.execute_mml
            il_connections.execute_mml_without_check('date "+%a %b %d %H:%M:%S.%N %Z %Y"')
            ret =  org_execute_mml(s,*answers)
            return ret
        except Exception,e:
            raise AssertionError('execute_mml command %s fails: %s' % (s,str(e)))


    def get_param_obj(self, line, parent, obj):
        """
        Get the parameter object (class instance), returns parent for the next element if any.
        Used when parsing JONDOE's command output.
        """

        # Object id param, like this: obj.obj_id (OBJId) (object_id)                 = 1
        #match = re.match(' obj\..*\((\S*)\).*= (.*)', line)
        match = re.match(' obj\..*\((\S.*)\)\s*\((\S.*)\)\s*= (.*)', line)
        try:
            if  match.group(2) == "object_id":
                print "MATCHING " + match.group(1) + " " + match.group(2) + " " + match.group(3)
                p = ObjectIdParam(match.group(1))
                p.addVal(match.group(3))
                obj.add(p)
                return None
        except AttributeError:
            pass

        # Simple param, like this obj.wcel_range (CellRange)                        = 0
        match = re.match(' obj\..*\((\S*)\).*= (.*)', line)
        try:
            p = Param(match.group(1))
            p.addVal(match.group(2))
            obj.add(p)
            print 'adding simple ', match.group(1),match.group(2)
            return None
        except AttributeError:
            pass

        # Was not simple parameter try more complex
        # where the actual parameters are childs of this line
        # like obj.uraids (URAId) (list)
        match = re.match('.*obj\..*\((\S.*)\)\s*\((\S.*)\)\s*\Z', line)
        try:
            if match.group(2) in ('list', 'struct', 's_list'):
                p = Param(match.group(1), match.group(2))
                print 'adding list/struct/struct list ', match.group(1)
                parent = p
            elif match.group(2) == 'bits':
                if re.match('   .*obj\..*\((\S.*)\)\s*\((\S.*)\)\s*\Z', line) != None:
                    # This is a child bits struct
                    name = '/'.join((parent.getName(),match.group(1)))
                else:
                    name = match.group(1)
                print 'adding bits ', name
                p = Bits(name)
            else:
                raise AssertionError('Unknown line %s' % line)
            obj.add(p)
            return parent
        except AttributeError:
            pass
        # no, this must be a child element
        # child (struct and list) elements
        match = re.match('  [ ]+obj\..*\((\S*)\).*= (.*)', line )
        try:
            if parent.type == 'list':
                name = match.group(1)
                print 'adding list elem ', match.group(1)
            else:
                # Struct type element, we join the name with parent name
                name =  '/'.join((parent.getName(), match.group(1)))
                print 'adding struct child ', parent.getName(), match.group(1),match.group(2)
            p = Param(name)
            p.addVal(match.group(2))
            obj.add(p)
            return parent
        #except AttributeError as a:
        except AttributeError:
            pass

        # Was not a struct or list child element, try bits
        # For bits

        match = re.match('  [ ]+obj\.[^()]+= (.*)', line)
        try:
            if len(obj.params) and isinstance(obj.params[-1],Bits):
                obj.params[-1].addVal(match.group(1))
                print 'adding bits', match.group(1)
                return parent
        except AttributeError:
            pass
        print 'No match',line
        return None

    def get_obj_from_jondoe_output(self, output):
        """
        Returns an object with field values initialized from the jondoe output

        Output:
         obj.wcel_range (CellRange)                        = 0
         obj.sac (SAC)                                = 1
         obj.hcs_prio (HCS)                           = 0

        Returns an object:
         obj.CellRange = 0
         obj.SAC =1
         obj.HCS_PRIO = 0
        """

        obj = ObjStruct()

        parent = None

        for line in output.split('\n'):
            line = line.strip('\r')
            parent = self.get_param_obj(line, parent, obj)
        return obj

    def get_param_info_data(self, o_name, p_name, parent_name=""):
        """
        Returns the JONDOE command output from command "param",
        which contains the parameter information from FOOLIB.
        """
        if ( parent_name == "" ):
            content = self.run_jondoe_cmd("param -O %s -N %s"%(o_name,p_name))
        else:
            content = self.run_jondoe_cmd("param -O %s -N %s -p %s"%(o_name,p_name,parent_name))
        if 'display_param_info_by_name error' in content:
            raise ParameterNotFoundException('Parameter not found')
        return content

    def get_param_infos_from_diff_list(self, o_name, diff_list, logmon_handle=None):
        """
        Gets parameter info using jondoe and stores that info to the diff list items, also
        removes all unknown parameters from the diff list
        """
        unknown_params = []
        for diff in diff_list:
            try:
                param_info_data = self.get_param_info_data(o_name, diff.name, diff.parent_name)
                foo_param = parameter_utils().get_param_info(param_info_data)
                diff.param_info = foo_param   # Store info
            except ParameterNotFoundException:
                unknown_params.append(diff)

        for diff in unknown_params:
            diff_list.remove(diff)
            if logmon_handle is not None:
                log_utils.log_utils().remove_log_pattern(logmon_handle, '.*param %s/%s not found' % (diff.parent_name, diff.name))

    def remove_ignored_param_diffs(self, diff_list, ignored_params):
        """
        We can ignore any difference
        """
        if not hasattr(ignored_params, '__iter__'):
            ignored_params = [ignored_params]

        remove_these = []
        for diff in diff_list:
            if diff.name in ignored_params:
                remove_these.append(diff)

        for diff in remove_these:
            if diff in diff_list:
                diff_list.remove(diff)

    def remove_dl_ul_only_diffs(self, diff_list):
        """
        Removes the differences, which are caused because the parameter is of type uploadOnly or downloadOnly
        If the parameter is uploadOnly --> don't care about its value in the UL plan
        If the paranmeter is downloadOnly --> parameter should not exist in the UL plan
        Assumption: diffs are in order: 1) dl 2) ul
        Note! Assumes that get_param_infos_from_diff_list is called before this
        """
        remove_these = []
        for diff in diff_list:
            print str(diff)
            foo_param = diff.param_info
            if ( parameter_utils().is_param_upload_only(foo_param)):
                remove_these.append(diff)
            elif ( parameter_utils().is_param_download_only(foo_param)) and (diff.val2 == None):
                remove_these.append(diff)
        for diff in remove_these:
            diff_list.remove(diff)

    def remove_oms_only_diffs(self, diff_list):
        """
        Removes the differences, which are caused by oms-only parameters.
        """
        remove_these = []
        for diff in diff_list:
            print str(diff)
            foo_param = diff.param_info
            if ( parameter_utils().is_param_oms_only(foo_param)):
                remove_these.append(diff)
        for diff in remove_these:
            diff_list.remove(diff)

    def remove_deleted_diffs(self, diff_list, checkfeatures=None):
        """
        Removes parameters which should have been deleted from tree
        Note! Assumes that get_param_infos_from_diff_list is called before this
        """
        remove_these = []
        for diff in diff_list:
            print str(diff)
            foo_param = diff.param_info
            if checkfeatures is not None and not parameter_utils().check_feature_conditions(foo_param, checkfeatures):
                remove_these.append(diff)
        for diff in remove_these:
            diff_list.remove(diff)

    def remove_extra_list_items(self, diff_list):
        """
        Removes the differences, which are caused because the list parameter does not have any count field
        Assumption: diffs are in order: 1) dl 2) ul
        """
        remove_these = []
        for diff in diff_list:
            print str(diff)
            foo_param = diff.param_info
            if parameter_utils().is_param_list_without_count_field(foo_param):
                #print ("NO COUNT FIELD!")
                def_val = parameter_utils().get_param_default_value(foo_param)
                if ( diff.val1 == None ) and ( str(diff.val2) == def_val or str(diff.val2) == "0"):  # scalar list
                    #print "This can  be removed!"
                    remove_these.append(diff)
                elif ( diff.val1 == None and foo_param.pddb_type == "complex" and diff.val2 == "item" ):  # struct list
                    #print "This can  be removed!"
                    remove_these.append(diff)

        for diff in remove_these:
            diff_list.remove(diff)

    def check_default_values(self, o_name, cmdata):
        """
        Check the defaul value of all parameter in the UL plan
        """

        # simple parameters
        for p in cmdata.iterfind('managedObject/p'):
            self.check_p_def_value(o_name, "", p.get("name"), p.text)

        for l in cmdata.iterfind('managedObject/list'):
            parent_name = l.get("name")
            if len(l.getiterator('item')) > 0:
                for i in l.iterfind('item'):
                    for p in i.findall('p'):
                        self.check_p_def_value(o_name, parent_name, p.get("name"), p.text)
            else:
                for p in l.findall('p'):
                    self.check_p_def_value(o_name, "", parent_name, p.text)

    def check_p_def_value(self, o_name, parent_name, p_name, p_value):
        """
        Checks if the given parameter value is the default value.
        If not, raises an exception.
        """
        param_info_data = self.get_param_info_data(o_name, p_name, parent_name)
        foo_param = parameter_utils().get_param_info(param_info_data)
        def_val = parameter_utils().get_param_default_value(foo_param)

        #print "Param=%s Value=%s Default=%s" % (p_name, p_value, def_val)
        if def_val != "-" and def_val != p_value:
            raise AssertionError('Default value MISMATCH for %s: def_val=%s value=%s' % (p_name, def_val, p_value))

    def upload_plan(self, task_id=None, return_plan_content=True):
        """
        This keywords executes plan upload using fsclish (mcRNC) or RUOSTE service terminal (cRNC).
        It returns the contents of the plan file as string.
        """
        if task_id is None:
            task_id = self.generate_task_id()

        if TestResources.ismcRNC():
            output = self.run_cmd('fsclish -c "set cli unsupported-vendor-mode on eiltonodslemac"'
                                  ' -c "start radio-network rnw-plan-operation upload task-id %s"'
                                  %task_id )
            self.calculate_time(output)
            plan_content = self.run_cmd('zcat /mnt/QNOMU/plan/RNWPLANU.XML.gz')
        else:
            self.execute_service_terminal_commands(['ZL:M','ZLP:M,MAS','ZMD:W0-PLATMP/RNWPLANU.Z'])
            output = self.execute_service_terminal_commands(['ZL:3', 'ZLEL:3:,W0-BLCODE/RUOSTEQX.IMG','Z3MPE','Z3MPU:%s'%task_id],'Y')
            if output.find('RNW Plan upload completed successfully')==-1 or output.find('Uploaded RNW Plan file: /RUNNING/PLATMP/RNWPLANU.Z')==-1:
                raise AssertionError("upload operation failed")
            self.calculate_time(output)
            self.ftp_get_a_file("/RUNNING/PLATMP/RNWPLANU.Z", "RNWPLANU.Z")
            f = gzip.open('RNWPLANU.Z', 'rb')
            plan_content = f.read()
            f.close()

        self.rnw_plan_operation_log_should_contain(task_id, "Plan Upload", "Finished", "Success")

        if return_plan_content:
            return plan_content
        else:
            return output
    
    def my_setup(self, loglevel="info"):
        """
        This keyword set and get info of test environment
        """
        self.mcRNC_set_log_level(loglevel)
        self.get_RNC_PDDB_metadata()
        self.get_system_prb_info()
        self.get_system_uptime()
        self.ensure_unit0_working()
        self.add_RNCIPAddress()
    
    def mcRNC_set_log_level(self, level="info"):
        """
        This keyword sets log level to default info
        """
        if TestResources.ismcRNC():
            print "Setting log level"
            output = self.run_cmd('fsclish -c "set troubleshooting app-log rule rule-id default keep level %s "' %level)
            return output
        else:
            print "Skipping setting log in cRNC"

    def get_system_prb_info(self, sys_prbs=["50A","506","524","523","4EE","A0F","04FA","04EF","050B","02F7","054E","03C6"]):
        """
        This keyword get the system prb info
        """
        if sys_prbs == None:
            return 
        print "System prb: %s" % sys_prbs
        output = ""
        
        if TestResources.ismcRNC():
            output += il_connections.execute_mml_without_check("rpm -qa | grep pac_ray")
            output += il_connections.execute_mml_without_check("rpm -qa | grep pab")
            output += il_connections.execute_mml_without_check("rpm -qa | grep foo")
            output += il_connections.execute_mml_without_check("rpm -qa | grep vex")
            output += il_connections.execute_mml_without_check("rpm -qa | grep rak")
            output += il_connections.execute_mml_without_check("rpm -qa | grep rez")
            output += il_connections.execute_mml_without_check("rpm -qa | grep rek")
            output += il_connections.execute_mml_without_check("rpm -qa | grep pac_reu")
        else:
            for sys_prb in sys_prbs:
                output += self.execute_service_terminal_commands(["ZSXPI:%s" % sys_prb])
        print output
    
    def get_system_build(self):
        """
        This keyword get the system build version
                   0 OMU-0    QX151480   NW      QX 15.14-80          
        """
        if TestResources.ismcRNC():
            cmd = "fsswcli -l"
            output = il_connections.execute_mml(cmd)
            build = output
        else:
            output = IpaMml.connections.execute_mml_without_check("ZWQO:RUN::OMU,0:;")
            r = re.search('\s+(\w+)\s+OMU-0\s+(\w+)\s+(\w+)\s+(\w+)', output)
            if r is None:
                return 'unknown'
            else:
                build = r.group(2)
        print "System build:", string.strip(build)
        return build
        
    def get_system_uptime(self):
        """
        This keyword get the system uptime
        """
        if TestResources.ismcRNC():
            cmd = "uptime"
            output = il_connections.execute_mml(cmd)
            print "System uptime:", string.split(string.strip(output), ',')[0]
        else:
            output = IpaMml.connections.execute_mml_without_check("ZAHP::NR=0688:2010-01-01;")
            print output
                
    def ensure_unit0_working(self, unit=""):
        """
        This keyword ensures unit is in working state.
        """
        print "Ensure unit0 is working."
        if unit == "":
            unit = TestResources.getResources('UNIT')

        if TestResources.ismcRNC():
            cmd = "fshascli -s %s" % unit
            cmd_switch = "fshascli -WnF /CFPU-1/QNOMU*"
            output = il_connections.execute_mml(cmd)
            print output
            if ("role(ACTIVE)" not in output):
                try:
                    output = il_connections.execute_mml(cmd_switch)
                except:
                    pass
        else:
            units = IpaMml.units_lib.get_units(unit, mode="")
            print units
            if (units.state.find("WO") == -1):
                self._change_omu_state('WO')

    def check_clear_rnwdb_thoroughly_needed(self):
        """
        This keyword check if clear rnwdb thoroughly needed
        """
        if self.check_rnc_id_match() == False:
            print "RNC-ID not match, clear rnwdb thoroughly needed"
            return True
        if (self.all_RNC_objects_exist_in_db() == False) and (self.one_RNC_object_exist_in_db() == True) :
            print "One of RNC objects exist but not all RNC objects exist, clear rnwdb thoroughly needed"
            return True
        if self.get_prnc_mode() == "Backup":
            print "PRNC mode is Backup, clear rnwdb thoroughly needed"
            return True
        return False
    
    def is_directory_exist_on_rnc(self, dir_path):
        """
        if directory exist on RNC, return True
        """
        testResource = TestResources.current_resources.getRes()
        if "REMOTE_PATH" in testResource.iterkeys():
            if dir_path in testResource["REMOTE_PATH"]:
                return True
        output = self.check_directory_exist(dir_path)
        if 'No such file or directory' not in output:
            if "REMOTE_PATH" in testResource.iterkeys():
                dir_path_list = testResource["REMOTE_PATH"]
                dir_path_list.append(dir_path)
            else:
                dir_path_list = [dir_path]
            testResource.update({"REMOTE_PATH": dir_path_list})
            return True

        return False
    
    def check_directory_exist(self, dir_path):
        """
        This keyword check if the directory exist on RNC.
        Command 'ls' will be run on RNC 
        """
        output = ""
        try:
            if TestResources.ismcRNC():
                output = self.run_cmd('cd %s' %dir_path)
            else:
                check_file_command = "ZPS:ls,%s;" % dir_path
                output = self.execute_service_terminal_commands(["ZL:P;", "ZLP:P,POM;", check_file_command])
        except:        
            output = 'Directory %s not exist. No such file or directory' %dir_path
        print '*DEBUG* %s' %output
        return output
    
    def create_remote_dir_on_rnc(self, remote_dir=None):
        if remote_dir == None:
            remote_dir = TestResources.getResources("XML_PATH")
        if TestResources.ismcRNC():
            output = self.check_directory_exist(remote_dir)
            if 'No such file or directory' in output:
                output = self.run_cmd('mkdir %s' %remote_dir)
        else:
            IpaMml.connections.execute_mml_without_check("ZIAA:PROFILE::::FTP=W;","Y")
            check_file_command = "ZPS:ls,%s;" % remote_dir
            output = self.execute_service_terminal_commands(["ZL:P;", "ZLP:P,POM;", check_file_command])
            if "No such file or directory" in output:
                create_dir_command = "ZPS:mkdir,/RUNNING/CI,0755"
                output = self.execute_service_terminal_commands(["ZL:P;", "ZLP:P,POM;", create_dir_command])
        testResource = TestResources.current_resources.getRes()
        if "REMOTE_PATH" in testResource.iterkeys():
            dir_path_list = testResource["REMOTE_PATH"]
            dir_path_list.append(remote_dir)
        else:
            dir_path_list = [remote_dir]
        testResource.update({"REMOTE_PATH": dir_path_list})
        
    def copy_test_files_ifneeded(self):
        """
        This keyword check if test files in cRNC or mcRNC are up to date.
        If not up to date or not exist, then copy test files to test bed.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        old_dir = plan_generate.plan_generate().get_old_dir(base_dir)
        new_dir = plan_generate.plan_generate().get_new_dir(base_dir)
        new_rnc_id = TestResources.getResources('RNC-ID')
        local_modified_time_file_path = plan_generate.plan_generate().get_modified_time_file_path(new_dir)
        if os.path.exists(local_modified_time_file_path):
            os.remove(local_modified_time_file_path)
        if TestResources.ismcRNC():
            remote_dir = '/mnt/backup/ci'
            remote_modified_time_file_path = '/mnt/backup/ci/last_modified_time.txt'
            try:
                #output = self.run_cmd('ls %s' %remote_modified_time_file_path)
                print local_modified_time_file_path, remote_modified_time_file_path
                self.sftp_get_a_file(local_modified_time_file_path, remote_modified_time_file_path)
            except:
                print 'remote modified time file %s not found on mcRNC' % remote_modified_time_file_path
            copy_list = plan_generate.plan_generate().check_copy_needed(old_dir, new_dir, new_rnc_id)
            if len(copy_list) > 0:
                print "start copying..."
                output = self.check_directory_exist(remote_dir)
                if 'No such file or directory' in output:
                    self.run_cmd('mkdir %s' %remote_dir)
                for file_name in sorted(copy_list.iterkeys()):
                    if (':' in new_dir):
                        local_path = "%s\\%s"%(new_dir, file_name)
                    else:
                        local_path = "%s/%s"%(new_dir, file_name)
                    remote_path = "%s/%s"%(remote_dir, file_name)
                    print local_path, remote_path
                    self.sftp_put_a_file(local_path, remote_path)
                self.sftp_put_a_file(local_modified_time_file_path, remote_modified_time_file_path)
        else:
            remote_dir = '/RUNNING/CI'
            remote_modified_time_file_path = '/RUNNING/CI/last_modified_time.txt'
            #check_file_command = "ZPS:ls,%s;" % remote_modified_time_file_path
            #output = self.execute_service_terminal_commands(["ZL:P;", "ZLP:P,POM;", check_file_command])
            IpaMml.connections.execute_mml_without_check("ZIAA:PROFILE::::FTP=W;","Y")
            IpaMml.connections.execute_mml_without_check("ZW7L::ON;")
            try:
                print local_modified_time_file_path, remote_modified_time_file_path
                self.ftp_get_a_file(remote_modified_time_file_path, local_modified_time_file_path)
            except:
                print 'remote modified time file %s not found on cRNC' % remote_modified_time_file_path
            copy_list = plan_generate.plan_generate().check_copy_needed(old_dir, new_dir, new_rnc_id)
            if len(copy_list) > 0:
                print "start copying..."
                check_file_command = "ZPS:ls,%s;" % remote_dir
                output = self.execute_service_terminal_commands(["ZL:P;", "ZLP:P,POM;", check_file_command])
                if "No such file or directory" in output:
                    self.ftp_put_a_file(new_dir, remote_dir)
                else:
                    for file_name in sorted(copy_list.iterkeys()):
                        if (':' in new_dir):
                            local_path = "%s\\%s"%(new_dir, file_name)
                        else:
                            local_path = "%s/%s"%(new_dir, file_name)
                        remote_path = "%s/%s"%(remote_dir, file_name)
                        print local_path, remote_path
                        self.ftp_put_a_file(local_path, remote_path)
                    self.ftp_put_a_file(local_modified_time_file_path, remote_modified_time_file_path)
            
    def prevent_rnwdb_updates_to_disk(self):
        """
        This keyword prevents RAQUEL database updates to disk in cRNC (could be part of load project).
        No effects in mcRNC.
        """
        if not TestResources.ismcRNC():
            IpaMml.connections.execute_mml_without_check("ZDBP:RAQUEL,0:DISK:;")

    def allow_rnwdb_updates_to_disk(self):
        """
        This keyword allows RAQUEL database updates to disk in cRNC (store the queued as well?)
        No effects in mcRNC.
        """
        if not TestResources.ismcRNC():
            IpaMml.connections.execute_mml_without_check("ZDBR:RAQUEL,0:DISK:;")

    def _del_all_objs_from_db(self):
        """
        Deletes all objects from the database in mcRNC.
        """
        old_prompt = self._start_zdbrnw_session()

        for db in ['act']:
            for obj in self.objectInfo.keys():
                self._zdbrnw_delete_object(db, obj)

        self._end_zdbrnw_session(old_prompt)

    def check_rnc_id_match(self):
        real_rnc_id = self.get_RNC_id_in_db()
        env_rnc_id = int(TestResources.getResources('RNC-ID')[4:])
        if (real_rnc_id != 0) and (real_rnc_id != env_rnc_id):
            print "Real RNC-ID %d doesn't match with Planned RNC-ID %d" %(real_rnc_id, env_rnc_id)
            return False
        else:
            return True

    def get_all_unit_state(self):
        """
        This keyword get all unit states
        """
        if TestResources.ismcRNC():
            RG = get_all_the_recovery_group_names() 
            if not RG[0].startswith('/'): RG.pop(0)
            #command='fsclish -c "show has state managed-object %s"' %(' '.join(RG))
            units = show_manage_object_states(' '.join(RG))
        else:
            units = IpaMml.units_lib.get_units("", mode="")
        print units
        return units

    def wait_mml_connection_after_restart(self):
        counter = 0
        res = TestResources.getResources()
        while counter < 10:
            try:
                time.sleep(30)
                self.metadata_connect_to_ipa(res['IPADDRESS'], res['USERNAME'], res['PASSWORD'])
                print '*INFO* metadata_connect_to_ipa succeeds'
                break
            except:
                print '*INFO* metadata_connect_to_ipa fails'
                pass
            counter += 1

    def wait_rnwdb_normal(self):
        
        if TestResources.ismcRNC():
            return
        counter = 0
        while counter < 5:
            output = string.replace(IpaMml.connections.execute_mml_without_check("ZDBS:RAQUEL,0;"), '\r', '')
            lines = string.split(output, '\n')
            print lines
            rnwdb_normal = False
            wo_state = ''
            sp_state = ''
            for line in lines:
                if (re.match('RAQUEL', line)):
                    print line
                    m = re.match(r"(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)", line)
                    if (m.group(3) == 'WO'): 
                        wo_state = m.group(4)
                        #wo_sub_state = m.group(5)
                    elif (m.group(3) == 'SP'):
                        sp_state = m.group(4)
                        #sp_sub_state = m.group(5)
            #if wo_state == 'NORMAL' and sp_state == 'NORMAL':
            if sp_state == 'NORMAL':
                rnwdb_normal = True
                print '*INFO* rnwdb sp normal'
                print wo_state
                break
            time.sleep(300)
            counter += 1
        if rnwdb_normal == False:
            print '*INFO* rnwdb not normal'

    def wait_system_startup(self, units):
        counter = 0
        while counter < 40:
            new_units = self.get_all_unit_state()
            print new_units
            all_unit_restored = True
            if TestResources.ismcRNC():
                for unit in new_units:
                    if ((units[unit].admin == "UNLOCKED") and (new_units[unit].admin != "UNLOCKED")) or \
                       ((units[unit].opt == "ENABLED") and (new_units[unit].opt != "ENABLED")) or \
                       ((units[unit].usage == "ACTIVE") and (new_units[unit].usage != "ACTIVE")) :
                        all_unit_restored = False
                        break                
            else:
                for unit_name in new_units.iterkeys():
                    if ('EX' in units[unit_name].state) and ('EX' not in new_units[unit_name].state):
                        all_unit_restored = False
                        break

            if all_unit_restored == True:
                print '*INFO* all units restored'
                break
            time.sleep(30)
            counter += 1
        if all_unit_restored == False:
            print '*INFO* all units not restored'
 
    def restart_system(self):
        try:
            # execute the command
            # keyword always answer "Y" for any confirmation. 
            setattr(IpaMml.connections._get_current_connection(), 'loss_expected', True)
            output = IpaMml.connections.execute_mml("ZUSS::TOT;", "Y", "Y")
            
            for i in range(30):
                time.sleep(1)
                IpaMml.connections.execute_mml_without_check('\n')
            return i, output
        except EOFError :
            hasattr(IpaMml.connections._get_current_connection(), 'loss_expected') and delattr(IpaMml.connections._get_current_connection(), 'loss_expected')
            return ''
           
    def clear_rnwdb_thoroughly(self):
        """
        This keyword clear rnwdb throughly
        """
        if TestResources.ismcRNC():
            il_connections.execute_mml_without_check("cd /root")
            il_connections.execute_mml_without_check("cp /opt/nsn/pac_rnwdb_e1/config/schemas/delete_DBRNW.sql /root")
            il_connections.execute_mml_without_check("chmod 777 delete_DBRNW.sql")
            il_connections.execute_mml_without_check("sed -i 's/DBRNW/DBRNWHSB/g' delete_DBRNW.sql")
            il_connections.execute_mml_without_check("export ODBCSYSINI=/opt/nsn/SS_PostgresClient/etc/")
            il_connections.execute_mml_without_check("export LD_LIBRARY_PATH=$LD_LIBRARY_PTAH:/opt/nsn/SS_Postgres/lib/")
            il_connections.execute_mml_without_check("/opt/nsn/SS_Postgres/bin/psql -h CFPU-0 -p 5433 -U _qnrnwdbman template1 -f delete_DBRNW.sql")
            units = self.get_all_unit_state()
            il_connections.execute_mml_without_check("fshascli -rnF /QNOMU")
            self.wait_system_startup(units)
            
        else:
            output = self.execute_service_terminal_commands(['ZL:P','ZLP:M,MAS','ZMM:W0-EFILES/RAQ*.*,W0-LFILES/'])
            if "FILES NOT FOUND" not in output:
                self.execute_service_terminal_commands(['ZL:P','ZLP:M,MAS','ZMD:W0-LFILES/DBARAQQX.IMG','ZMD:W0-LFILES/DBIRAQQX.IMG'])
                units = self.get_all_unit_state()
                self.restart_system()
                self.wait_mml_connection_after_restart()
                self.wait_system_startup(units)
            else:
                print "W0-EFILES/RAQ*.* don't exist"
            

    def clear_rnwdb(self):
        """
        This keyword clears the radio network database
        """
        # WCEL must be deleted separately with a plan, because
        # if it is just removed from the DB there will be references to it
        # in some program blocks
        self.delete_object_hierarchy_down_to('WCEL', False)

        if TestResources.ismcRNC():
            # Not using zcluster-id.sh because it so soooooo slow
            #output = self.run_cmd('/root/zcluster-id.sh -s 1 --cleardb --force')
            #time.sleep(40) # 26 seconds was too short in prinsessa...
            self._del_all_objs_from_db()
        else:
            # Load RAQUEL database from disk (assuming it's empty)
            count = 5
            db_is_empty = False
            while count > 0 and not db_is_empty:
                count = count - 1
                db_is_empty = True
                IpaMml.connections.execute_mml_without_check("ZDBM:RAQUEL,0:IMM:;", "Y")
                # sometimes SP OMU update fails, which results FILE_FULL errors
                # Check both units and release records if needed
                time.sleep(2)
                if self.RNC_object_exists_in_db(omu_index = 0) or self.RNC_object_exists_in_db(omu_index = 1):
                    self._free_record("9F20001")
                    db_is_empty = False
                # Check also newdb
                if self.RNC_object_exists_in_db(file_id = '9F20101', omu_index = 0) or self.RNC_object_exists_in_db(file_id = '9F20101', omu_index = 1):
                    self._free_record("9F20101")
                    db_is_empty = False
                """
                for obj in ['PRNC', 'BKPRNC', 'RNCSRV', 'DATSYN', 'PREBTS']:
                    self.delete_object_from_db(obj, True)
                """
        return True
                    
    def _start_zdbrnw_session(self):
        """
        Executes zdbrnw command and stays there,
        @return: old prompt
        """
        prompt = [r"\[.*@.*\]\s*[#$]|Password:|.*\s*DBRNWHSB=# "]
        old_prompt = il_connections.set_prompt(prompt)
        il_connections.execute_mml_without_check('zdbrnw')
        return old_prompt

    def _end_zdbrnw_session(self, prompt):
        """
        Exits from zdbrnw session and sets the given prompt.
        """
        il_connections.execute_mml_without_check('\\q')
        il_connections.set_prompt(prompt)

    def _zdbrnw_delete_object(self, db, objectToDelete):
        """
        Deletes the given object from the database. 
        """
        object_info = self.get_object_info(objectToDelete)
        if object_info.cRNC_only:
            return
        if db == "act":
            il_connections.execute_mml_without_check('delete from %s;' % object_info.actdb)
        else:
            il_connections.execute_mml_without_check('delete from %s;' % object_info.newdb)

    def _mcrnc_delete_from_db(self, db, objectToDelete):
        """
        db should be either "act" or "new"
        """
        # Some object tables have name which is not the same as the obj_name
        old_prompt = self._start_zdbrnw_session()
        self._zdbrnw_delete_object(db, objectToDelete)
        self._end_zdbrnw_session(old_prompt)

    def _free_record(self, file_id, record_nbr=0):
        """
        Frees the given record from the given file by sending a request message to FEMSER.
        """
        # Using FIHAND
        #IpaMml.connections.execute_mml_without_check( "ZDFR:OMU,0:9F200F1,0:;", "YF ")
        #Using FEMSER, because FIDAS stucks the robot sometimes, prompt not found
        # XXX could use FUTILI command for this
        self.execute_service_terminal_commands("ZOS:*,7000,90,,,,,2176,,,XD0,XD%s,XD%s,0" % (file_id, record_nbr))

    def _crnc_del_from_db(self, objectToDelete, record_nbr=0, delete_also_newdb=False):
        # Release the record from act and new databases
        self._free_record(self.objectInfo[objectToDelete].actfile, record_nbr)
        if delete_also_newdb:
            self._free_record(self.objectInfo[objectToDelete].newfile, record_nbr)

    def delete_object_from_db(self, objectToDelete, delete_also_newdb=False):
        """
        This keyword deletes the given object from the database, if it exists there
        """
        if objectToDelete == 'RNC':
            self.clear_rnwdb()

        if self.object_exists_in_db(objectToDelete,db="act"):
            obj_info = self.objectInfo[objectToDelete]
            if obj_info.delete_with_plan & self.all_RNC_objects_exist_in_db():
                # Assuming delete plan exists for all objs
                self.download_plan('RNWPLAND_%s_delete.XML' % objectToDelete.upper())
            else:
                if TestResources.ismcRNC():
                    if not obj_info.cRNC_only:
                        self._mcrnc_delete_from_db("act", objectToDelete)
                        if delete_also_newdb:
                            self._mcrnc_delete_from_db("new", objectToDelete)
                else:
                    if not obj_info.mcRNC_only:
                        self._crnc_del_from_db(objectToDelete)

    def _download_plan(self, plan_file, should_succeed=True, activate=True, task_id=None, should_activation_succeed=True):
        """
        This keyword executes plan download using fsclish commands (mcRNC) or RUOSTE service terminal extension (cRNC).
        """

        if TestResources.ismcRNC():
            self.run_cmd("rm -f /mnt/backup/%s"%plan_file)
            self.run_cmd("cp -f %s/%s /mnt/backup/%s"%(TestResources.getResources('XML_PATH'),plan_file,plan_file))
            if activate:
                activate_str = 'auto-activate -activate'
            else:
                activate_str = ''
            output = self.run_cmd('fsclish -c "set cli unsupported-vendor-mode on eiltonodslemac"'
                                  ' -c "start radio-network rnw-plan-operation download %s task-id %s verbose -verbose planfile /mnt/backup/%s"'
                                  % (activate_str, task_id, plan_file))
        else:
            # copy the file to PLATMP directory (RUOSTE would do it anyway) and
            # use a shorter file name, because RUOSTE only accepts file names max 42 characters
            self.execute_service_terminal_commands(['ZL:P','ZLP:P,POM','ZPS:cp,%s/%s,/RUNNING/PLATMP/RNWPLAND.XML'%(TestResources.getResources('XML_PATH'),plan_file)])
            if activate:
                activate_str = 'A'
            else:
                activate_str = ''
            output = self.execute_service_terminal_commands(['ZL:3', 'ZLEL:3:,W0-BLCODE/RUOSTEQX.IMG','Z3MPE','Z3MPD%sF:W0-PLATMP/RNWPLAND.XML,445566,%s'%(activate_str,task_id)],'Y')

        return output

    def download_plan(self, plan_file, should_succeed=True, activate=True, task_id=None, should_activation_succeed=True):
        """
        This keyword executes plan download using fsclish commands (mcRNC) or RUOSTE service terminal extension (cRNC).
        It also activates the plan, if parameter activate has value True.
        It returns the output of the command.
        | Input Paramaters | Man. | Description |
        | plan_file        | Yes  | Full path to plan file |
        | should_succeed   | No   | Download should succeed or not |
        | activate         | No   | Activate the plan or not |
        | task_id          | No   | Identifies to the task |
        | should_activation_succeed   | No  | Activation should succeed or not |
        
        | Return Value     |
        The operation result is returned
        """
        if task_id is None:
            task_id = self.generate_task_id()

        count = 6
        while count > 0:
            output = self._download_plan(plan_file, should_succeed, activate, task_id, should_activation_succeed)
            if output.find("OPERATION IS ONGOING") == -1 and output.find("OPERATION IS GOING ON") == -1 and output.find("RNW DATABASE IS RESERVED") == -1:
                break
            time.sleep(5)
            count = count - 1

        # Check the operation status from the output
        if should_succeed:
            if "RNW Plan download completed successfully" not in output:
                raise AssertionError("download operation failed")
            if activate:
                if should_activation_succeed:
                    if "RNW Plan activation completed successfully" not in output:
                        raise AssertionError("activation operation failed")
                else:
                    if "RNW Plan activation completed successfully" in output:
                        raise AssertionError("activation operation succeeded")
        else:
            if "RNW Plan download completed successfully" in output:
                raise AssertionError("download operation succeeded")
        self.calculate_time(output)
        # Check the rnw operation log
        if should_succeed:
            self.rnw_plan_operation_log_should_contain(task_id, "Plan Download", "Finished", "Success")
            if activate:
                if should_activation_succeed:
                    self.rnw_plan_operation_log_should_contain(int(task_id)+1, "Plan Activation", "Finished", "Success")
                else:
                    self.rnw_plan_operation_log_should_contain(int(task_id)+1, "Plan Activation", "Aborted", "Failure")  # XXX
        else:
            self.rnw_plan_operation_log_should_contain(task_id, "Plan Download", "Aborted", "Failure")

        return output

    def _direct_activate(self, plan_file, should_succeed=True, task_id=None, delete_incoming_adj="no"):
        """
        This keyword executes direct activation of the plan using test version of ruoste CLI (mcRNC)
        or RUOSTE service terminal extension (cRNC).
        """
        if TestResources.ismcRNC():
            self.run_cmd("rm -f /mnt/backup/%s"%plan_file)
            self.run_cmd("cp -f %s/%s /mnt/backup/%s"%(TestResources.getResources('XML_PATH'),plan_file,plan_file))
            #plan_path = TestResources.getResources('XML_PATH')
            TestResources.getResources('XML_PATH')
            output = self.run_cmd('fsclish -c "set cli unsupported-vendor-mode on eiltonodslemac"'
                                  ' -c "start radio-network direct-activation task-id %s da-xml-file /mnt/backup/%s verbose -verbose delete-incoming-adj %s"'
                                  % (task_id, plan_file, delete_incoming_adj))
        else:
            # copy the file to PLATMP directory (RUOSTE would do it anyway) and
            # use a shorter file name, because RUOSTE only accepts file names max 42 characters
            self.execute_service_terminal_commands(['ZL:P','ZLP:P,POM','ZPS:cp,%s/%s,/RUNNING/PLATMP/RNWPLAND.XML'%(TestResources.getResources('XML_PATH'),plan_file)])
            if delete_incoming_adj == "no":
                output = self.execute_service_terminal_commands(['ZL:3', 'ZLEL:3:,W0-BLCODE/RUOSTEQX.IMG','Z3MPE','Z3MD:W0-PLATMP/RNWPLAND.XML,,%s'%task_id],'Y')
            else:
                output = self.execute_service_terminal_commands(['ZL:3', 'ZLEL:3:,W0-BLCODE/RUOSTEQX.IMG','Z3MPE','Z3MDIF:W0-PLATMP/RNWPLAND.XML,,%s'%task_id],'Y')

        return output

    def direct_activate(self, plan_file, should_succeed=True, task_id=None, delete_incoming_adj="no"):
        """
        This keyword executes direct activation of the plan using test version of ruoste CLI (mcRNC)
        or RUOSTE service terminal extension (cRNC).
        | Input Paramaters | Man. | Description |
        | plan_file        | Yes  | Full path to plan file |
        | should_succeed   | No   | Direct Activation should succeed or not |
        | task_id          | No   | Identifies to the task |
        | delete_incoming_adj   | No  | Delete the incoming ADJx or not |
        
        | Return Value     |
        The operation result is returned
        """
        if task_id is None:
            task_id = self.generate_task_id()

        count = 6
        while count > 0:
            output = self._direct_activate(plan_file, should_succeed, task_id, delete_incoming_adj)
            if output.find("OPERATION IS ONGOING") == -1 and output.find("OPERATION IS GOING ON") == -1 and output.find("RNW DATABASE IS RESERVED") == -1:
                break
            time.sleep(5)
            count = count - 1

        if should_succeed and "Completed" not in output:
            raise AssertionError("direct activation operation failed")
        elif not should_succeed and "Completed" in output:
            raise AssertionError("direct activation operation succeeded")

        # Check the rnw operation log
        if should_succeed:
            self.rnw_plan_operation_log_should_contain(task_id, "Direct Activation", "Finished", "Success")
        else:
            self.rnw_plan_operation_log_should_contain(task_id, "Direct Activation", "Aborted", "Failure")

        return output

    def activate_plan(self, task_id = None):
        """This keyword activate a plan with task_id
        | Input Paramaters | Man. | Description |
        | task_id          | No   | Identifies to task |
        | Return Value     |
        Plan activation result is returned
        """        
        if task_id is None:
            task_id = self.generate_task_id()

        if TestResources.ismcRNC():
            output = self.run_cmd('fsclish -c "set cli unsupported-vendor-mode on eiltonodslemac"'
                                  ' -c "start radio-network rnw-plan-operation activate verbose -verbose"')
            if "RNW Plan activation completed successfully" not in output:
                raise AssertionError('Activation failed')
            return output
        else:
            output = self.execute_service_terminal_commands(['ZL:3', 'ZLEL:3:,W0-BLCODE/RUOSTEQX.IMG','Z3MPE','Z3MPAF:445566,%s'%(task_id)], 'Y')
            if 'RNW Plan activation completed successfully' not in output:
                raise AssertionError('Plan activation error')
            self.rnw_plan_operation_log_should_contain(task_id, "Plan Activation", "Finished", "Success")

            return output

    def ismcRNC(self):
        """
        Returns True or False
        """
        return TestResources.ismcRNC()

    def set_raktor_test_mode(self, on_or_off):
        """
        Set RAKTOR optionality test mode on or off
        """
        if on_or_off.upper() == 'ON':
            mode = '8'
        else:
            mode = '0'
        if self.ismcRNC():
            # RAKTOR test mode on
            il_connections.execute_mml('ilcliru.sh OMU dmxsend -- -h 92,\*,4ee,0,0,1,0,6034 -b 1,%s' % mode)
        else:
            self.execute_service_terminal_commands("ZOS:92,*,4EE,,,1,,6034,,,1,%s" % mode)

    def _set_rak_opt_state(self, opt_type, feat_state):
        """
        Requests RAKTOR to change the state of the given option.
        feat_state = 'ON', 'OFF' or 'CONF'
        """
        if feat_state.upper() == 'ON':
            state = '2'
        elif feat_state.upper() == 'CONF':
            state = '1'
        else:
            state = '0'

        if self.ismcRNC():
            # RAKTOR test mode on
            il_connections.execute_mml('ilcliru.sh OMU dmxsend -- -h \*,\*,4ee,0,0,1,0,a1f9 -b %X,%s,0,0,xd0' % (int(opt_type), state))
        else:
            self.execute_service_terminal_commands("ZOS:*,*,4EE,,,1,,A1F9,,,%X,%s,XD0" % (int(opt_type), state))

    def enable_optionality(self, opt_type, feat_state='ON'):
        """
        Enable optionality using RAKTOR test mode, opt_type is the opt_type_t constant
        given in decimal format
        feat_state = 'ON' or 'CONF'
        """
        self._set_rak_opt_state(opt_type, feat_state)

    def set_all_options(self, feat_state='ON'):
        """
        Requests RAKTOR to change the state of the given option.
        feat_state = 'ON', 'OFF' or 'CONF'
        """
        if feat_state.upper() == 'ON':
            state = '2'
        elif feat_state.upper() == 'CONF':
            state = '1'
        else:
            state = '0'

        count = 0
        for opt_type in self.featureInfo.iterkeys():
            if self.ismcRNC():
                # RAKTOR test mode on
                il_connections.execute_mml('ilcliru.sh OMU dmxsend -- -h \*,\*,4ee,0,0,1,0,a1f9 -b %X,%s,0,0,xd0' % (int(opt_type), state))
            else:
                self.execute_service_terminal_commands("ZOS:*,*,4EE,,,1,,A1F9,,,%X,%s,XD0" % (int(opt_type), state))
            count += 1
            if count % 20 == 0:
                time.sleep(1)
        
    def disable_optionality(self, opt_type):
        """
        Disable optionality using RAKTOR test mode, opt_type is the opt_type_t constant
        given in decimal format
        """
        self._set_rak_opt_state(opt_type, 'OFF')

    def generate_task_id(self):
        """
        Returns a random task id.
        """
        return random.randint(1,65535)

    def rnw_plan_error_log_should_not_contain(self, task_id):
        """
        This kw checks from the rnw-plan-error-log that it does not contain the given task id.

        Task id     Operation   Object                                  Status  Recno
        ================================================================================
         * No entries found with task id 47436.
         * No history data found.
        ================================================================================
        """
        if self.ismcRNC():
            output = self.run_cmd('fsclish -c "set cli unsupported-vendor-mode on eiltonodslemac"'
                      ' -c "show radio-network rnw-plan-error-log task-id %s"'
                      % task_id )
        else:
            output = self.execute_service_terminal_commands(['ZL:3', 'ZLEL:3:,W0-BLCODE/RUOSTEQX.IMG','Z3MPE','Z3MPH:%s'%task_id],'Y')

        if "No entries found with task id %s"%task_id not in output:
            raise AssertionError('rnw plan error log contains the task id')


    def rnw_plan_error_log_should_contain(self, task_id, operation, objectShouldContain, error):
        """
        This kw checks tha t the rnw-plan-error-log contains the given task id, operation and error.

        Task id     Operation   Object                                  Status  Recno
        ================================================================================
        156517103   Modify      RNC-1/DN:RNAC-1                         Failure 8
          Error 15384:  ILLEGAL VALUES FOR RNW OBJECT PARAMETERS IN RNW PLAN
        ================================================================================
        """
        if self.ismcRNC():
            output = self.run_cmd('fsclish -c "set cli unsupported-vendor-mode on eiltonodslemac"'
                      ' -c "show radio-network rnw-plan-error-log task-id %s"'
                      % task_id )
        else:
            output = self.execute_service_terminal_commands(['ZL:3', 'ZLEL:3:,W0-BLCODE/RUOSTEQX.IMG','Z3MPE','Z3MPH:%s'%task_id],'Y')

        if "No entries found with task id %s"%task_id in output:
            raise AssertionError('rnw plan error log does not contain the task id')
        if operation not in output:
            raise AssertionError('rnw plan error log does not contain the operation')
        if error not in output:
            raise AssertionError('rnw plan error log does not contain the error')

    def get_log_entry_by_task_id(self, output, task_id):
        """
        Returns a log entry from rnw plan operation log having the given task_id.
        """
        if "No entries found with task id" in output:
            raise AssertionError('rnw plan operation log does not contain entry with task id ,%s,'%task_id)

        output = output.replace('=', '-')
        entries = output.split('--------------------------------------------------------------------------------')
        for entry in entries:
            fields = entry.split()
            try:
                if fields[1] == str(task_id):
                    return entry
            except:
                pass
        raise AssertionError('rnw plan operation log does not contain entry with task id ,%s,'%task_id)

    def rnw_plan_operation_log_should_contain(self, task_id, operation, state, status, error=None):
        """
        --------------------------------------------------------------------------------
        00000004   445566      Plan Download        Aborted       12-03-2014 07:47:32:90
                   No          Failure              112233
                   [/mnt/QNOMU/plan/RNWPLAND.XML]
                   0           0                    No            No
          Error 14449:  XML PARSING ERROR
        --------------------------------------------------------------------------------
        00000005   445567      Plan Activation      Finished      11-03-2014 13:05:36:30
                   No          Success              112233
                   []
                   0           1                    Yes           No
        --------------------------------------------------------------------------------
        """
        if self.ismcRNC():
            output = self.run_cmd('fsclish -c "set cli unsupported-vendor-mode on eiltonodslemac"'
                      ' -c "show radio-network rnw-plan-operation-log"' )
        else:
            output = self.execute_service_terminal_commands(['ZL:3', 'ZLEL:3:,W0-BLCODE/RUOSTEQX.IMG','Z3MPE','Z3MPI:%s'%task_id],'Y')

        entry = self.get_log_entry_by_task_id ( output, task_id )
        if operation not in entry:
            raise AssertionError('rnw plan operation log does not contain the operation %s'%entry)
        if state not in entry:
            raise AssertionError('rnw plan operation log does not contain the state %s'%entry)
        if status not in entry:
            raise AssertionError('rnw plan operation log does not contain the status %s'%entry)
        if error is not None and error not in entry:
            raise AssertionError('rnw plan operation log does not contain the error %s'%entry)

    def generate_empty_download_plan(self, objectPlan = None, dist_name = None, operation='create', raml_version='2.1', xmlns='raml21.xsd'):
        """
        Creates plan object for (empty) plan download
        The add_plan_param can be used to add parameters to this plan
        """
        class Plan:
            def __init__(self, objectPlan, dist_name, operation, raml_version, xmlns):
                self.header = """<?xml version="1.0" encoding="UTF-8"?>
                    <raml version="%s" xmlns="%s">
                    <cmData type="actual" scope="all" domain="RNCRNWCMPLAN" adaptationVersionMajor="RN8.0">
                    <header>
                        <log dateTime="2014-03-07T11:10:45" action="modified" user="CRNC" appInfo="cRNC OMS">cRNC plan upload</log>
                    </header>"""%(raml_version,xmlns)
                self.mo_list=[]
                self.def_object = dist_name
                if objectPlan is not None:
                    self.add_mo(objectPlan, dist_name, operation)
                self.tail = """</cmData>
                                </raml>
                            """
            def add_mo(self, objectPlan, dist_name, operation = "create"):
                class MO:
                    def __init__(self, objectPlan, dist_name, operation):
                        self.object = objectPlan
                        self.dist_name = dist_name
                        self.operation = operation
                        self.params = []
                    def __str__(self):
                        s =  '<managedObject class="%s" distName="%s" version="RN8.0" operation="%s">' % (objectPlan, dist_name, operation)
                        for p in self.params:
                            s += p
                        s += '</managedObject>'
                        return s

                self.mo_list.append(MO(objectPlan, dist_name, operation))

            def __str__(self):
                s = self.header
                for m in self.mo_list:
                    s += str(m)
                s += self.tail
                return s

            def encode(self, encoding):
                return str(self)

        return Plan(objectPlan, dist_name, operation, raml_version, xmlns)

    def add_plan_param(self, plan, param_xml, dist_name=None):
        """
        Add a parameter to the plan, param must be in top level XML format, i.e.
        <p name="this_param">value</p>
        or
        <p name="complex">
          <list
            <p name="child">v</p>
          </list>
        </p>
        """
        if dist_name is None:
            if plan.def_object is None:
                raise AssertionError('Cannot add parameter without dist name')
            dist_name = plan.def_object
        for m in plan.mo_list:
            if m.dist_name == dist_name:
                m.params.append(param_xml)
                return
        else:
            raise AssertionError('Given dist name "%s" not found form plan' % dist_name)

    def add_plan_mo(self, plan, objectPlan, dist_name, operation="create"):
        """
        Add a managedObject to the plan.
        """
        plan.add_mo(objectPlan, dist_name, operation)

    def add_role_to_ip_address(self, ip_address=None, role="ssh", iface="eth0"):
        """
        Adds the given role to the given IP address. If no IP address is given, 
        uses the IP address of the current test bench.
        """
        res_iface = TestResources.getResources('INTFACE')
        if res_iface is not None:
            iface = res_iface
        mask = TestResources.getResources('MASK')
        if mask is None:
            mask = '24'
        if role == "oms":
            if ip_address is None:
                ip_address = TestResources.getResources('IPADDRESS1')
            output = self.run_cmd('fsclish -c "show networking address owner /QNOMU"')
            if iface not in output:
                self.run_cmd('fsclish -c "add networking address /QNOMU iface %s ip-address %s/%s role %s user /QNHTTPD"' % (iface, ip_address, mask, role))
            if 'oms' not in output and 'OMS' not in output:
                self.run_cmd('fsclish -c "set networking address /QNOMU iface %s ip-address %s add-role %s"' % (iface, ip_address, role))
            if 'QNHTTPD' not in output:
                self.run_cmd('fsclish -c "set networking address /QNOMU iface %s ip-address %s add-user %s"' % (iface, ip_address, "/QNHTTPD"))
        if role == "ssh":
            if ip_address is None:
                ip_address = TestResources.getResources('IPADDRESS')
            output_ssh = self.run_cmd('fsclish -c "show networking address owner /SSH"')
            if iface not in output_ssh:
                self.run_cmd('fsclish -c "add networking address dedicated /SSH iface %s ip-address %s/%s"' % (iface, ip_address, mask))
            if 'ssh' not in output_ssh:
                self.run_cmd('fsclish -c "set networking address /SSH iface %s ip-address %s add-role %s"' % (iface, ip_address, role))

    def del_role_from_ip_address(self, ip_address=None, role="ssh", iface="eth0"):
        """
        Deletes the given role from the given IP address. If no IP address is given,
        uses the IP address of the current test bench.
        """
        if ip_address is None:
            res = TestResources.getResources()
            ip_address = res['IPADDRESS1']
        if role == "oms":
            self.run_cmd('fsclish -c "set networking address dedicated /QNOMU iface %s ip-address %s del-role %s"'%(iface, ip_address, role) )
        elif role == "ssh":
            self.run_cmd('fsclish -c "set networking address /SSH iface %s ip-address %s del-role %s"'%(iface, ip_address, role) )
            

    def configure_oms_connection(self, oms_ip_address, rnc_id, rnc_name):
        """
        RNC object not found.
        PRNC object not found.
        """
        if self.ismcRNC():
            output = self.run_cmd('fsclish -c "show radio-network omsconn"')
            #if "PRNC object not found" in output:
            self.run_cmd('fsclish -c "set radio-network omsconn omsipadd %s rncid %s rncname %s "'%(oms_ip_address, rnc_id[4:], rnc_name) )
            
        else:
            self.execute_service_terminal_commands(["ZL:3;", "ZLEL:3:,W0-BLCODE/RUOSTEQX.IMG"], "Y")
            output = self.execute_service_terminal_commands(["Z3C"])
            if "PRNC object not found" in output:
                check_file_command = "Z3CM:%s,%s" % (rnc_id[4:], oms_ip_address)
                self.execute_service_terminal_commands([check_file_command])
            #elif "RNC object not found" in output:
            check_file_command = "Z3CI:%s,%s,1,5,1" % (oms_ip_address, oms_ip_address)
            #check_file_command = "Z3CR:%s,%s" % (rnc_id[4:], oms_ip_address)
            self.execute_service_terminal_commands([check_file_command])
        self.wait_oms_connection()

    def configure_license(self):
        """
        """
        if self.ismcRNC():
            output = self.run_cmd('fsclish -c "show license all"')
            #if "PRNC object not found" in output:
        else:
            for param_class in ["2","55"]:
                output = IpaMml.connections.execute_mml_without_check("ZWOS:%s;" % param_class)
                print output
                rs = re.findall('(\w*)\s*(\w*)\s*DEACTIVATED\s*', output)
                print rs
                for featureCode, featureName in rs:
                    #featureCode = string.strip(r.group(1))
                    print "featureCode, featureName", featureCode, featureName
                    output = IpaMml.connections.execute_mml_without_check("ZWOA:%s,%s,A;"% (param_class, featureCode))
                

    def wait_oms_connection(self):
        counter = 0
        while counter < 10:
            oms_connection_ok = False
            print "waiting for oms connection...retrying %s" % counter
            if self.ismcRNC():
                if self.get_oms_conn_status() == 'ACTIVE':
                    oms_connection_ok = True
                    print '*INFO* oms connection is ok'
                    break
            else:
                output = self.execute_service_terminal_commands(["Z3CO"],"Y")
                if 'Operation succeeded' in output:
                    oms_connection_ok = True
                    print '*INFO* oms connection is ok'
                    break
            time.sleep(30)
            counter += 1
        if oms_connection_ok == False:
            print '*INFO* oms connection is not ok'

    def get_oms_conn_status(self):
        """
        CFPU-0@RNC-114                                    [2015-01-28 09:23:40 +0800]
        Connecting to CFPU-1 with active OMU...
        RNC-OMS connectivity configuration data:
        RNC ID:                             114
        ......
        RNC-OMS O&M connection status:      ACTIVE
        """
        if self.ismcRNC():
            output = self.run_cmd('fsclish -c "show radio-network omsconn"')
            r = re.search('RNC-OMS O&M connection status:\s*(\S*)', output)
            if r is None:
                return 'unknown'
            else:
                print 'RNC-OMS O&M connection status:', r.group(1)
                return r.group(1)
        else:
            output = self.execute_service_terminal_commands(["Z3CO"],"Y")
            if 'Operation succeeded' in output:
                oms_connection_ok = True
                print '*INFO* oms connection is ok'
                return "ACTIVE"
            else:
                return "INACTIVE"
        
    def add_RNCIPAddress(self):
        """
        configure role ssh to the IP address of the test bench
        In mcRNC: set radio-network omsconn omsipadd oms_ip_address rncid rnc_id rncname rnc_name
        In CRNC: "Z3CR:%s,%s,%s" % (rnc_id[4:], oms_ip_address, rnc_name)
        """
        print "Add RNC IP Address"
        rnc_ip_0 = TestResources.getResources('IPADDRESS')
        rnc_ip_1 = TestResources.getResources('IPADDRESS1')
        if self.ismcRNC():
            self.add_role_to_ip_address(rnc_ip_0, "ssh" )
            self.add_role_to_ip_address(rnc_ip_1, "oms" )
        #else:
            #IpaMml.connections.execute_mml_without_check("ZIAH:OMSUSR:PROFILE;","SYSTEM","SYSTEM")
        oms_ip_address = TestResources.getResources('OMSIPADDRESS')
        rnc_id = TestResources.getResources('RNC-ID')
        rnc_name = TestResources.getResources('RNC-NAME')
        self.configure_oms_connection(oms_ip_address, rnc_id, rnc_name)

    def add_RNCIPAddress1(self):
        """
        In mcRNC: configure role ssh to the IP address of the test bench
        In CRNC: this keyword has no effect
        """
        res = TestResources.getResources()
        if self.ismcRNC():
            self.add_role_to_ip_address(res['IPADDRESS1'], "oms" )
        else:
            pass

    def clear_RNCIPAddress(self):
        """
        In mcRNC: delete role ssh from the IP address of the test bench
        In CRNC: this keyword has no effect
        """
        res = TestResources.getResources()
        if self.ismcRNC():
            self.del_role_from_ip_address(res['IPADDRESS1'], "oms" )
        else:
            pass

    def clear_RNCIPAddress1(self):
        """
        In mcRNC: delete role ssh from the IP address of the test bench
        In CRNC: this keyword has no effect
        """
        res = TestResources.getResources()
        if self.ismcRNC():
            self.del_role_from_ip_address(res['IPADDRESS'], "QNOMU" )
        else:
            pass
    
    def suite_setup(self):
        """
        """
        
    def get_RNC_PDDB_metadata(self, forced=False):
        """
        Returns RNC_PDDB
        """
        build = str.strip(self.get_system_build())
        print build
        if TestResources.ismcRNC():
            file_path = "PDDB_REP_mcRNC.XML"
            file_path = file_path.replace("PDDB_REP_mcRNC", "PDDB_REP_mcRNC" + build)
            if os.path.exists(file_path) and (forced == False):
                print "File %s already exists"% file_path
            else:
                print "Retrieving PDDB data file from RNC..."
                self.sftp_get_a_file("PDDB_REP.GZ", "/opt/nokiasiemens/pac_pddbmdata_e1/etc/PDDB_REP.GZ")
                f = gzip.open('PDDB_REP.GZ', 'rb')
                plan_content = f.read()
                f.close()
                if os.path.exists(file_path):
                    os.remove(file_path)
                f2 = open(file_path, 'w')
                f2.write(plan_content)
                f2.close()
            pddbReport = file_path
        else:
            file_path = "PDDB_REP_cRNC.XML"
            file_path = file_path.replace("PDDB_REP_cRNC", "PDDB_REP_cRNC" + build)
            if os.path.exists(file_path) and (forced == False):
                print "File %s already exists"% file_path
            else:
                print "Retrieving PDDB data file from RNC..."
                self.ftp_get_a_file("/RUNNING/WEBFIL/PDX_REPO.GZ", "PDX_REPO.GZ")
                f1 = gzip.open('PDX_REPO.GZ', 'rb')
                plan_content = f1.read()
                f1.close()
                if os.path.exists(file_path):
                    os.remove(file_path)
                f2 = open(file_path, 'w')
                f2.write(plan_content)
                f2.close()
            pddbReport = file_path
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
        return pddbData
        
    def get_RNC_id_in_db(self, omu_index=0):
        """
        Returns RNC_ID
        if RNC_ID doesn't exist, return 0
        """
        rnc_id = 0
        if TestResources.ismcRNC():
            prompt = [r"\[.*@.*\]\s*[#$]|Password:|.*\s*DBRNWHSB=# "]
            old_prompt = il_connections.set_prompt(prompt)
            il_connections.execute_mml_without_check('zdbrnw')
            output = il_connections.execute_mml_without_check('select rnc_id from act_rncgen;')
            il_connections.execute_mml_without_check('\\q')
            il_connections.set_prompt(old_prompt)
            if "(0 rows)" not in output:
                print output
                lines = string.strip(output).split('\n')
                i = 0
                for line in lines:
                    i += 1;
                    if "rnc_id" in line:
                        line = lines[i+1]
                        rnc_id = int(string.strip(line))
                        break
        else:
            file_id = '9F20001'
            output = IpaMml.connections.execute_mml_without_check( "ZDFB:OMU,%d:%s:0;" % (omu_index, file_id))
            if "00000000  R" in output:
                new_output = IpaMml.connections.execute_mml_without_check( "ZDFD:OMU,%d:%s;" % (omu_index, file_id))
                lines = string.strip(new_output).split('\n')
                i = 0
                for line in lines:
                    i += 1;
                    if "09F20001" in line:
                        line = lines[i]
                        values = string.split(line)
                        print values[1] + values[0]
                        rnc_id = int((values[1] + values[0]), 16)
                        break
        return rnc_id
    
    def RNC_object_exists_in_db(self, file_id = '9F20001', omu_index=0):
        """
        This keyword check if there is RNC object in the RNW DB.
        Returns True or False
        """
        if TestResources.ismcRNC():
            prompt = [r"\[.*@.*\]\s*[#$]|Password:|.*\s*DBRNWHSB=# "]
            old_prompt = il_connections.set_prompt(prompt)
            il_connections.execute_mml_without_check('zdbrnw')
            output = il_connections.execute_mml_without_check('select rnc_id from act_rncgen;')
            il_connections.execute_mml_without_check('\\q')
            il_connections.set_prompt(old_prompt)
            if "(0 rows)" in output:
                return False
            else:
                print output
                return True
        else:
            output = IpaMml.connections.execute_mml_without_check( "ZDFB:OMU,%d:%s:0;" % (omu_index, file_id))
            if "00000000  R" in output:
                return True
            else:
                return False

    def all_RNC_objects_exist_in_db(self):
        """
        This keyword checks if all RNC objects are in the RNW DB
        Returns True, if all RNC objects are found, or False, if any of the RNC objects is not found.
        """
        if TestResources.ismcRNC():
            return_value = True
            objects = [("rnc_id","act_rncgen"),
                       ("rnac_id","act_rnac"),
                       ("rnfc_id","act_rnfc"),
                       ("rnhspa_id","act_rnhspa"),
                       ("rnmobi_id","act_rnmobi"),
                       ("rnps_id","act_rnps"),
                       ("rnrlc_id","act_rnrlc"),
                       ("rntrm_id","act_rntrm")]
            try:
                prompt = self._start_zdbrnw_session()
                for obj in objects:
                    output = il_connections.execute_mml_without_check('select %s from %s;'%(obj[0],obj[1]))
                    if "(0 rows)" in output:
                        return_value = False
                        break
            finally:
                self._end_zdbrnw_session(prompt)
            return return_value
        else:
            objects = ["9F20001","9F200F1","9F200F2","9F200F6","9F200F3","9F200F4","9F200F7","9F200F5"]
            for obj in objects:
                output = IpaMml.connections.execute_mml_without_check( "ZDFB:OMU,0:%s:0;"%obj)
                if "00000000  -" in output:
                    return False
            return True

    def one_RNC_object_exist_in_db(self):
        """
        This keyword checks if one of RNC object exist in the RNW DB
        Returns True, if one of RNC objects are found, or False, if no RNC objects is not found.
        """
        if TestResources.ismcRNC():
            return_value = True
            objects = [("rnc_id","act_rncgen"),
                       ("rnac_id","act_rnac"),
                       ("rnfc_id","act_rnfc"),
                       ("rnhspa_id","act_rnhspa"),
                       ("rnmobi_id","act_rnmobi"),
                       ("rnps_id","act_rnps"),
                       ("rnrlc_id","act_rnrlc"),
                       ("rntrm_id","act_rntrm")]
            try:
                prompt = self._start_zdbrnw_session()
                for obj in objects:
                    output = il_connections.execute_mml_without_check('select %s from %s;'%(obj[0],obj[1]))
                    if "(0 rows)" not in output:
                        return_value = True
                        break
            finally:
                self._end_zdbrnw_session(prompt)
            return return_value
        else:
            objects = ["9F20001","9F200F1","9F200F2","9F200F6","9F200F3","9F200F4","9F200F7","9F200F5"]
            for obj in objects:
                output = IpaMml.connections.execute_mml_without_check( "ZDFB:OMU,0:%s:0;"%obj)
                if "00000000  -" not in output:
                    return True
            return True

    def check_all_rnc_objects(self):
        if not self.all_RNC_objects_exist_in_db():
            self.create_base_config_for_object('RNC', True)
        
    def set_db_file_dump_prevention(self, prevented = True):
        """
        By default RAYMAN dumps all DB files to disk at the download start, which
        in cRNC takes a lot of time. This test mode preventes that.
        """
        if TestResources.ismcRNC():
            # Not needed in mc
            pass
        else:
            dump_prevention = TestResources.getResources('DUMP_PREVENTION')
            if(dump_prevention == 'N'):
                prevented = False
            state = 1 if prevented else 0
            self.execute_service_terminal_commands('ZOS:95,0,523,,,,,6034,,,90,%d,,,,,,,,' % state);
            self.execute_service_terminal_commands('ZOS:95,1,523,,,,,6034,,,90,%d,,,,,,,,' % state);

    def RNW_object_exists_in_db(self, obj_id, obj_file_id):
        """
        Returns True or False
        """
        if TestResources.ismcRNC():
            prompt = [r"\[.*@.*\]\s*[#$]|Password:|.*\s*DBRNWHSB=# "]
            old_prompt = il_connections.set_prompt(prompt)
            il_connections.execute_mml_without_check('zdbrnw')
            output = il_connections.execute_mml_without_check('select %s_id from act_%s;' % (obj_id, obj_id))
            il_connections.execute_mml_without_check('\\q')
            il_connections.set_prompt(old_prompt)
            if "(1 rows)" in output:
                return True
            else:
                return False
        else:
            output = IpaMml.connections.execute_mml_without_check( "ZDFB:OMU,0:%s:0;" % obj_file_id)
            if "00000000  -" in output or "00000000  R" in output:
                return False
            return True

    def create_object_hierarchy_up_to(self, obj, create_object_itself):
        """
        This keyword creates the objects, which are required by the given object.
        It also creates the given object, if create_object_itself == True.
        """
        print "--- create_object_hierarchy_up_to %s, create_object_itself %s"%(obj,str(create_object_itself))

        # First create all objects, which are requested
        if obj == "RNC_all":
            if not self.all_RNC_objects_exist_in_db():
                self.download_plan( "RNWPLAND_RNC_all_objects.XML" )
                return
        elif obj == "WCEL":   # optimization for WCEL creates all objects required by WCELL with one plan
            if not self.object_exists_in_db(obj):
                self.download_plan( "RNWPLAND_WCEL_all_objects.XML")
                if create_object_itself:
                    self.download_plan("RNWPLAND_WCEL_minimal.XML")
        else:
            object_info = self.get_object_info(obj)
            for o in object_info.required_objects:
                self.create_object_hierarchy_up_to(o, True)

            if create_object_itself:
                if not self.object_exists_in_db(obj):
                    self.download_plan("RNWPLAND_%s_minimal.XML"%object_info.obj_name)

    def _get_objects_to_be_deleted_before_this_object(self,this_obj,objects_to_be_deleted):
        """
        This keyword returns a list of objects, which should  be deleted before the given object.
        """
        for o in self.objectInfo.keys():
            object_info = self.get_object_info(o)
            if this_obj in object_info.required_objects:
                self._get_objects_to_be_deleted_before_this_object(o,objects_to_be_deleted)
                objects_to_be_deleted.append(o)

    def delete_object_hierarchy_down_to(self, obj, remain_object_itself):
        """
        This keyword deletes objects, which require the given object.
        It deletes also the given object, if remain_object_itself == False.
        """
        print "delete_object_hierarchy_down_to %s, remain_object_itself %s"%(obj,str(remain_object_itself))
        objects_to_be_deleted=[]
        self._get_objects_to_be_deleted_before_this_object(obj,objects_to_be_deleted)

        print "--- Objects_to_be_deleted=%s"%str(objects_to_be_deleted)
        for o in objects_to_be_deleted:
            self.delete_object_from_db(o)
        if not remain_object_itself:
            self.delete_object_from_db(obj)

    def create_base_config_for_object(self, obj, create_object_itself=True):
        """
        This keyword creates the base configuration for the given object:
          - deletes all other objects, which require the given object
          - creates all objects, which are required by the given object
          - creates the given object, if create_object_itself == True
        """
        if TestResources.ismcRNC():
            if self.get_object_info(obj).cRNC_only:
                return
        else:
            if self.get_object_info(obj).mcRNC_only:
                return

        if obj == "RNC":
            """
            if self.object_exists_in_db(obj):
                self.clear_rnwdb()
            if create_object_itself:
                #self.download_plan("RNWPLAND_RNC_minimal.XML")
                self.download_plan("RNWPLAND_RNC_all_objects.XML")
            """
            if self.object_exists_in_db(obj):
                self.restore_rnc_to_initial_state()
            else:
                self.download_plan("RNWPLAND_RNC_all_objects.XML")
        else:
            """
            self.create_object_hierarchy_up_to(obj, create_object_itself)
            self.delete_object_hierarchy_down_to(obj, create_object_itself)
            if create_object_itself:
                if not self.object_exists_in_db(obj):
                    self.download_plan("RNWPLAND_%s_minimal.XML"%obj)
            """
            config_plan = self.combine_mo_plan_with_dependency(obj, create_object_itself, 'create')
            self.upload_a_file(config_plan)
            self.download_plan(config_plan)

    def create_base_config_for_rncsrv(self, create_rncsrv=False):
        """
        Test case setup: creates the base config for RNCSRV object.
        """
        if TestResources.ismcRNC():
            return

        self.create_base_config_for_prnc(True, 'BACKUP')
        rncsrv_exists = self.object_exists_in_db('RNCSRV')
        if create_rncsrv and not rncsrv_exists:
            self.direct_activate('RNWPLAND_RNCSRV_minimal.XML')
        elif not create_rncsrv and rncsrv_exists:
            self.direct_activate('RNWPLAND_RNCSRV_delete.XML')

    def create_base_config_for_prnc(self, create_prnc=False, prnc_mode='PRIMARY'):
        """
        Test case setup: creates the base config for PRNC object.
        """
        if TestResources.ismcRNC():
            return

        current_prnc_mode=    self.get_prnc_mode()
        prnc_exists = self.object_exists_in_db('PRNC')
        delete_prnc = False
        if current_prnc_mode != prnc_mode:
            delete_prnc = True
        if prnc_exists and not create_prnc:
            delete_prnc = True
        if delete_prnc:
            self.clear_rnwdb();
            self.clear_prnc_info_from_r0sfle(prnc_mode)
            prnc_exists = False
        if create_prnc and not prnc_exists:
            modes = {'PRIMARY':'1','BACKUP':'2'}
            self.create_prnc(modes[prnc_mode])

    def remove_forced_cmob_objects(self):
        """
        Removes the CMOB objects directly from the database.
        Removes also the CMOB-4 object.
        RNC object must be re-created after this in order to get the forced CMOB objects back.
        """
        #obj_info = self.objectInfo["CMOB"]
        self.objectInfo["CMOB"]
        if TestResources.ismcRNC():
            self._mcrnc_delete_from_db("act", "CMOB")
            self._mcrnc_delete_from_db("new", "CMOB")
        else:
            self._crnc_del_from_db("CMOB",0)
            self._crnc_del_from_db("CMOB",1)
            self._crnc_del_from_db("CMOB",2)

    def get_modify_plan_file_name(self, obj_name, different_plans=False):
        """
        Returns the name of the test plan file used for modifying the given object.
        The test plan file can be different in mcRNC and cRNC.
        """
        if TestResources.ismcRNC() or not different_plans:
            return 'RNWPLAND_' + obj_name + '_modify.XML'
        else:
            return 'RNWPLAND_' + obj_name + '_modify_cRNC.XML'

    def isRNCObject(self, obj_name):
        """
        Returns True, if the given object is one of the RN* objects.
        """
        return obj_name.upper() in ('RNC','RNAC','RNMOBI','RNCERM','RNPS','RNHSPA','RNRLC','RNTRM','RNFC')

    def calculate_time(self, output):
        import datetime
        """
        RNW Plan download started at: 30-05-2014 10:01:28.99
        RNW Plan download completed successfully at 30-05-2014 10:01:35.55

        RNW Plan activation started at: 30-05-2014 10:01:36.55
        RNW Plan activation completed successfully at 30-05-2014 10:01:49.62

        RNW Plan upload starting at 30-05-2014 10:01:52.81
        RNW plan upload file generating started successfully.
        RNW Plan upload completed successfully at 30-05-2014 10:01:53.21
        """
        datetime_re = '([0-9][0-9])-([0-9][0-9])-([0-9][0-9][0-9][0-9]) ([0-9][0-9]):([0-9][0-9]):([0-9][0-9]).([0-9][0-9])'
        ret_output = ""

        m1 = re.search('RNW Plan download started at.*%s' % datetime_re, output)
        if m1 is not None:
            dl_start = datetime.datetime(int(m1.group(3)), int(m1.group(2)), int(m1.group(1)), int(m1.group(4)),
                                         int(m1.group(5)), int(m1.group(6)), int(m1.group(7)) * 10000)
            m2 = re.search('RNW Plan download completed successfully at %s' % datetime_re, output)
            try:
                dl_end = datetime.datetime(int(m2.group(3)), int(m2.group(2)), int(m2.group(1)), int(m2.group(4)),
                                           int(m2.group(5)), int(m2.group(6)), int(m2.group(7)) * 10000)
                print '*INFO* download time', dl_end-dl_start
                ret_output = ret_output + 'download time=' + str(dl_end-dl_start)
            except AttributeError:
                pass

        m1 = re.search('RNW Plan activation started at.*%s' % datetime_re, output)
        if m1 is not None:
            dl_start = datetime.datetime(int(m1.group(3)), int(m1.group(2)), int(m1.group(1)), int(m1.group(4)),
                                         int(m1.group(5)), int(m1.group(6)), int(m1.group(7)) * 10000)
            m2 = re.search('RNW Plan activation completed successfully at %s' % datetime_re, output)
            try:
                dl_end = datetime.datetime(int(m2.group(3)), int(m2.group(2)), int(m2.group(1)), int(m2.group(4)),
                                           int(m2.group(5)), int(m2.group(6)), int(m2.group(7)) * 10000)
                print '*INFO* activation time', dl_end-dl_start
                ret_output = ret_output + 'activation time=' + str(dl_end-dl_start)
            except AttributeError:
                pass

        m1 = re.search('RNW Plan upload starting at %s' % datetime_re, output)
        if m1 is not None:
            dl_start = datetime.datetime(int(m1.group(3)), int(m1.group(2)), int(m1.group(1)), int(m1.group(4)),
                                         int(m1.group(5)), int(m1.group(6)), int(m1.group(7)) * 10000)
            m2 = re.search('RNW Plan upload completed successfully at %s' % datetime_re, output)
            try:
                dl_end = datetime.datetime(int(m2.group(3)), int(m2.group(2)), int(m2.group(1)), int(m2.group(4)),
                                           int(m2.group(5)), int(m2.group(6)), int(m2.group(7)) * 10000)
                print '*INFO* upload time', dl_end-dl_start
                ret_output = ret_output + 'upload time=' + str(dl_end-dl_start)
            except AttributeError:
                pass

        return ret_output

    def calculate_time_to_file(self, output, filename):
        fdata = self.calculate_time(output)
        fo = open(filename, "wb")
        fo.write(fdata)
        fo.close()

        return fdata

    def direct_obj_inquire(self, moid):
        """
        Executes Direct Parameter Query using JONDOE.
        | Input Paramaters | Man. | Description |
        | moid             | Yes  | Management object identifies |        
        Returns the result (XML) as string.
        """
        output = self.run_jondoe_cmd("inquire %s" % moid)
        try:
            # return only plan XML
            return output[output.index('<raml'):output.index('/raml>') + len('/raml')]
        except ValueError:
            # Output does not contain plan xml
            return output

    def set_cons_check_disabled(self, disabled = True):
        """
        """
        if TestResources.ismcRNC():
            # Not needed in mc
            pass
        else:
            state = 1 if disabled else 0
            self.execute_service_terminal_commands('ZOS:92,0,523,,,,,6034,,,AA,%d,,,,,,,,' % state);
            self.execute_service_terminal_commands('ZOS:92,1,523,,,,,6034,,,AA,%d,,,,,,,,' % state);

    def create_prnc(self, mode, oms_ip_addr="1.2.3.4"):
        if TestResources.ismcRNC():
            pass
        else:
            rnc_id = TestResources.getResources('RNC-ID')
            oms_ip_addr = TestResources.getResources('OMSIPADDRESS')
            #output = self.execute_service_terminal_commands(['ZL:3', 'ZLEL:3:,W0-BLCODE/RUOSTEQX.IMG','Z3CM:1,%s,%s' % (ip_addr, mode)],'Y')
            self.execute_service_terminal_commands(['ZL:3', 'ZLEL:3:,W0-BLCODE/RUOSTEQX.IMG','Z3CM:%s,%s,%s' % (rnc_id[4:], oms_ip_addr, mode)],'Y')

    def create_prnc_in_backup_mode(self, ip_addr="1.2.3.4"):
        """
        Create PRNC object in backup mode
        """
        self.create_prnc('2', ip_addr)

    def delete_rncsrv_obj(self, objectRNCSRV="RNCSRV"):
        """
        Delete RNCSRV object both from DB and from Platform
        """
        if TestResources.ismcRNC():
            pass
        else:
            plan_file = "%s/RNWPLAND_%s_delete.XML" % (TestResources.getResources('XML_PATH'), objectRNCSRV.upper())
            target_dir = "/RUNNING/PLATMP/RNWPLAND.XML"
            count = 20
            while count > 0:
                self.execute_service_terminal_commands(['ZL:P','ZLP:P,POM','ZPS:cp,%s,%s' % (plan_file, target_dir)])
                output = self.execute_service_terminal_commands(['ZL:3', 'ZLEL:3:,W0-BLCODE/RUOSTEQX.IMG','Z3MPE','Z3MD:W0-PLATMP/RNWPLAND.XML,,%s'%self.generate_task_id()],'Y')
                if output.find("OPERATION IS ONGOING") == -1 and output.find("RNW DATABASE IS RESERVED") == -1:
                    return
                time.sleep(5)
                count = count - 1
            raise AssertionError('Deletion of %s failed' % objectRNCSRV)

    def _wait_until_connection_is_back(self):
        counter = 0
        while counter < 3:
            try:
                time.sleep(2)
                output = self.execute_service_terminal_commands(['ZZZ?'])
                if 'SERVICE TERMINAL MAIN LEVEL' in output:
                    return
                print 'this is output',output
            except Exception as e:
                print '*INFO* execute_mml fails',e
                pass
            counter += 1

    def _change_omu_state(self, new_state):
        """
        Change OMU-0 to new_state
        """
        class writer :
            def __init__(self, *writers) :
                self.writers = writers

            def write(self, text) :
                for w in self.writers :
                    w.write(text.replace('*WARN*',''))

        # Override print so that we do not get all *WARN* messages when telnet connection fails
        saved = sys.stdout
        sys.stdout = writer(sys.stdout)
        count = 5
        while count > 0:
            try:
                IpaMml.units_lib.set_unit_state('OMU-0', new_state, expect_loss_mml=True)
            except:
                pass
            self._wait_until_connection_is_back()
            try:
                IpaMml.units_lib.unit_should_be_in_state('OMU-0', new_state)
                sys.stdout = saved
                return
            except AssertionError:
                # For some reason state change did not happen
                time.sleep(1)
                count -= 1
                continue
        raise AssertionError('Unit state change fails')

    def get_prnc_mode(self):
        """
         2014-09-04 09:03:21.69
         BASE BUILD ENVIRONMENT : QX 14.38-70
         BASE BUILD DELIVERY : CID000QX 15.1-0
         BASE BUILD CD ID :
         BASE BUILD PACKAGE DIR : FLIPPERI
         PRNC MODE : BACKUP
         BKPRNC BUILD :
         BASE RNC LAYER4 STATUS : SCTP=NOT FILTER & TCP=NOT FILTER
         ETH PORT STATUS : CLOSE
         RNC SERVICE ID : -
         AUTO CONFIGURATION MODE : START
         AUTO CONFIGURATION INTERVAL : 10 MIN
         BPS OPERATION : -
        """
        prnc_mode = 'unknown'
        if TestResources.ismcRNC():
            output = self.run_cmd('fsclish -c "show radio-network omsconn"')
            r = re.search('PRNC mode:\s*\d (\S*)', output)
            if r is not None:
                print 'prnc mode="',r.group(1),'"'
                prnc_mode = r.group(1)[1:-1]
        else:
            output = self.execute_service_terminal_commands(['ZL:1','ZLP:1,RCB','Z1JJ'])
            r = re.search('PRNC MODE *: (\S*)', output)
            if r is not None:
                prnc_mode = string.strip(r.group(1))
                print 'prnc mode="',prnc_mode,'"'
        return prnc_mode

    def clear_prnc_info_from_r0sfle(self, requested_mode=['-','STANDARD','PRIMARY']):

        """
        R0SMAN manages reciliency info which is stored in r0sfle.xml.
        This KW patches the PRNC node in the file and does OMU-0 state changes WO -> SP -> WO
        in which situation R0SMAN reads the XML file again
        """
        if TestResources.ismcRNC():
            old_prompt = self._start_zdbrnw_session()
    
            for db in ['act']:
                for obj in ['PRNC', 'BKPRNC', 'RNCSRV', 'DATSYN']:
                    self._zdbrnw_delete_object(db, obj)
    
            self._end_zdbrnw_session(old_prompt)
        else:
            """
            if not hasattr(requested_mode, '__iter__'):
                requested_mode = [requested_mode]
            requested_mode.append('-')
            count = 3
            while (self.get_prnc_mode() not in requested_mode) and count > 0:
            """
            count = 3
            while count > 0:
                try:
                    self.ftp_get_a_file('/RUNNING/ASWDIR/R0SFLEGX.XML', 'tmp.xml')
                    f = open('tmp.xml','r')
                    data = f.read()
                    f.close()
                    data = data.replace('<PM>01</PM>','<PM>FF</PM>')
                    data = data.replace('<PM>02</PM>','<PM>FF</PM>')
                    data = data.replace('<PM>03</PM>','<PM>FF</PM>')
                    data = data.replace('<ID>0100</ID>','<ID>FFFF</ID>')
                    f = open('tmp.xml','w')
                    f.write(data)
                    f.close()
                    self.ftp_put_a_file('tmp.xml', '/RUNNING/ASWDIR/R0SFLEGX.XML')
                except Exception as e:
                    print 'Cannot update R0SFLE',e
                IpaMml.connections.execute_mml_without_check("ZDBS:RAQUEL,0;")
                self._change_omu_state('SP')
                IpaMml.connections.execute_mml_without_check("ZDBS:RAQUEL,0;")
                self._change_omu_state('WO')
                count -= 1
            for obj in ['PRNC', 'BKPRNC', 'RNCSRV', 'DATSYN', 'PREBTS']:
                self.delete_object_from_db(obj, True)

    def make_preparation_plan_for_deletion(self, ul_plan):
        # <managedObject class="RNC" version="RN7.0" distName="RNC-1" operation="create">
        prepare_plan = None
        #print ul_plan

        plan = XML_utils.XML_utils().get_cmdata_elem_from_text(ul_plan)
        if plan is None:
            raise AssertionError('Invalid plan file, cmData not found')

        for mo in plan.findall('managedObject'):
            mo_class = mo.get('class')
            mo_distname = mo.get('distName')
            '''
            if mo_class == 'RNC':
                if prepare_plan is None:
                    prepare_plan = self.generate_empty_download_plan(mo_class, mo_distname, 'update')
                else:
                    self.add_plan_mo(prepare_plan, mo_class, mo_distname, 'update')
                param_xml = """<p name="ServingOMSAdminSetting">1</p>"""
                self.add_plan_param(prepare_plan, param_xml, mo_distname)
            '''       
            if mo_class == 'RNFC':
                if XML_utils.XML_utils().get_mo_p_param_value(mo, "MOCNenabled") != "0":
                    param_xml = """<p name="MOCNenabled">0</p>"""
                    if prepare_plan is None:
                        prepare_plan = self.generate_empty_download_plan(mo_class, mo_distname, 'update')
                    else:
                        self.add_plan_mo(prepare_plan, mo_class, mo_distname, 'update')
                    self.add_plan_param(prepare_plan, param_xml, mo_distname)
                 
            if mo_class == 'RNMOBI':
                param_xml = ""
                if XML_utils.XML_utils().get_mo_p_param_value(mo, "AnchorHopiIdentifier") != "0":
                    param_xml += """<p name="AnchorHopiIdentifier">0</p>"""
                if XML_utils.XML_utils().get_mo_p_param_value(mo, "AnchorHopsIdentifier") != "0":
                    param_xml += """<p name="AnchorHopsIdentifier">0</p>"""
                if XML_utils.XML_utils().get_mo_p_param_value(mo, "AnchorFmcsIdentifier") != "0":
                    param_xml += """<p name="AnchorFmcsIdentifier">0</p>"""
                if XML_utils.XML_utils().get_mo_p_param_value(mo, "AnchorFmciIdentifier") != "0":
                    param_xml += """<p name="AnchorFmciIdentifier">0</p>"""
                #if AnchorHopiIdentifier, AnchorHopsIdentifier, AnchorFmcsIdentifier, AnchorFmciIdentifier == 1,
                if param_xml != "":
                    if prepare_plan is None:
                        prepare_plan = self.generate_empty_download_plan(mo_class, mo_distname, 'update')
                    else:
                        self.add_plan_mo(prepare_plan, mo_class, mo_distname, 'update')
                    self.add_plan_param(prepare_plan, param_xml, mo_distname)
                    
            if mo_class in ['IUCS', 'IUPS']:
                if XML_utils.XML_utils().get_mo_p_param_value(mo, "IuState") != "2":
                    param_xml = """<p name="IuState">2</p>"""
                    if prepare_plan is None:
                        prepare_plan = self.generate_empty_download_plan(mo_class, mo_distname, 'update')
                    else:
                        self.add_plan_mo(prepare_plan, mo_class, mo_distname, 'update')
                    self.add_plan_param(prepare_plan, param_xml, mo_distname)

        return prepare_plan         

    def make_delete_plan_from_upload_plan(self, ul_plan):
        # <managedObject class="RNC" version="RN7.0" distName="RNC-1" operation="create">
        mo_list=[]
        mo_type_list = self._get_mo_type_list('delete')
        #print ul_plan

        plan = XML_utils.XML_utils().get_cmdata_elem_from_text(ul_plan)
        if plan is None:
            raise AssertionError('Invalid plan file, cmData not found')

        for mo in plan.findall('managedObject'):
            mo_class = mo.get('class')
            mo_distname = mo.get('distName')
            if mo_class in ['RNC','RNAC','RNFC','RNHSPA','RNMOBI','RNPS','RNRLC','RNTRM','CMOB']:
                if mo_class == 'CMOB':
                    # To be improved later, here CMOB-1x CMOB-2x should be taken care
                    if ( not mo_distname.endswith('CMOB-1')) and ( not mo_distname.endswith('CMOB-2')) and ( not mo_distname.endswith('CMOB-3')):
                        mo_list.append((mo_class, mo_distname))
                continue
            mo_list.append((mo_class, mo_distname))

        delete_plan = None
        for mo_type in mo_type_list:
            for mo in mo_list:
                if mo[0] == mo_type:
                    if delete_plan is None:
                        delete_plan = self.generate_empty_download_plan(mo[0], mo[1], 'delete')
                    else:
                        self.add_plan_mo(delete_plan, mo[0], mo[1], 'delete')
        '''
        if delete_plan is not None:
            for mo in update_rnc_obj_list:
                if mo[0] == 'RNMOBI':
                    self.add_plan_mo(delete_plan, mo[0], mo[1], 'update')
                    param_xml = """<p name="AnchorHopiIdentifier">0</p><p name="AnchorHopsIdentifier">0</p><p name="AnchorFmcsIdentifier">0</p><p name="AnchorFmciIdentifier">0</p>"""
                    self.add_plan_param(delete_plan, param_xml, mo[1])
        '''
        return delete_plan
    
    def restore_rnc_to_initial_state(self):
        print "begin restore_rnc_to_initial_state"
        ul_xml = self.upload_plan()
        #check if preparation for deletion is needed
        #if preparation is needed, download and activate GeneratedPreparationForDeletion.XML
        prepare_xml = self.make_preparation_plan_for_deletion(ul_xml)
        if prepare_xml is not None:
            prepare_plan_text = str(prepare_xml)
            plan_generate.plan_generate().write_plan_text_to_file('GeneratedPrePlanForDeletion.XML', prepare_plan_text)
            self.upload_a_file('GeneratedPrePlanForDeletion.XML')
            self.download_plan('GeneratedPrePlanForDeletion.XML')
        delete_xml = self.make_delete_plan_from_upload_plan(ul_xml)
        obj_plan_file_list = []
        if delete_xml is not None:
            delete_plan_text = str(delete_xml)
            plan_generate.plan_generate().write_plan_text_to_file('GeneratedDeletePlan.XML', delete_plan_text)
            obj_plan_file_list.append('GeneratedDeletePlan.XML')
        base_dir = os.path.dirname(os.path.abspath(__file__))
        old_dir = plan_generate.plan_generate().get_old_dir(base_dir)
        if TestResources.ismcRNC():
            self.combine_plans('InitialRNC.xml', 'InitialRNC.XML', old_dir)
        else:
            self.combine_plans('InitialRNC_cRNC.xml', 'InitialRNC.XML', old_dir)
        obj_plan_file_list.append('InitialRNC.XML')
        self.combine_plans_without_replace_rncid(obj_plan_file_list, "RestoreRNCtoInitialState.XML")
        self.upload_a_file('RestoreRNCtoInitialState.XML')
        self.download_plan('RestoreRNCtoInitialState.XML')
                
        print "end restore_rnc_to_initial_state"

    def clean_all_objs_from_db(self):
        try:
            ul_plan = self.upload_plan()
        except:
            # Upload can fail if RNC object is not found
            return
        open('ul_plan.xml','w').write(ul_plan)
        delete_plan = self.make_delete_plan_from_upload_plan(ul_plan)
        if delete_plan is not None:
            f = open('delete_plan.xml','w')
            f.write(str(delete_plan))
            f.close()
            self.upload_a_file('delete_plan.xml')
            self.download_plan('delete_plan.xml')
        self.clear_rnwdb()
        
    def clean_all_except_rnc_objs_from_db(self):
        try:
            ul_plan = self.upload_plan()
        except:
            # Upload can fail if RNC object is not found
            return
        open('ul_plan.xml','w').write(ul_plan)
        delete_plan = self.make_delete_plan_from_upload_plan(ul_plan)
        if delete_plan is not None:
            f = open('delete_plan.xml','w')
            f.write(str(delete_plan))
            f.close()
            self.upload_a_file('delete_plan.xml')
            self.download_plan('delete_plan.xml')
        init_rnc_plan = self.combine_all_rnc_objects_plan()
        self.upload_a_file(init_rnc_plan)
        self.download_plan(init_rnc_plan)         
        return True

    def _append_if_not_included(self, array, listToAppend):
        if not hasattr(listToAppend, '__iter__'):
            listToAppend = [listToAppend]
        for i in listToAppend:
            if i not in array:
                array.append(i)

    def _get_required_objs(self, obj_name, obj_list):
        obj = self.objectInfo[obj_name]
        for r in obj.required_objects:
            if r == 'RNC_all':
                self._append_if_not_included(obj_list, ['RNC','RNAC','RNFC','RNHSPA','RNMOBI','RNPS','RNRLC','RNTRM'])
            else:
                self._get_required_objs(r, obj_list)
        self._append_if_not_included(obj_list, obj.obj_name)

    def _get_mo_type_list(self, plan_type):
        obj_list = []
        for o in self.objectInfo.values():
            if o.obj_name in obj_list:
                continue
            if o.cRNC_only and TestResources.ismcRNC():
                continue
            if o.mcRNC_only and not TestResources.ismcRNC():
                continue
            self._get_required_objs(o.obj_name, obj_list)

        if 'delete' in plan_type:
            obj_list.reverse()
        return obj_list

    def get_mo_plan_file_list(self, plan_type='', excluded_objs=[]):
        plan_file_names=[]

        obj_list = self._get_mo_type_list(plan_type)
        if plan_type != '':
            plan_type = '_'+plan_type

        for o in obj_list:
            if o not in excluded_objs:
                plan_file_names.append('RNWPLAND_%s%s.XML' % (o, plan_type))
        return plan_file_names

    def _get_mo_list_with_dependency(self, obj, plan_type):
        obj_list = []
        
        self._get_required_objs(obj, obj_list)

        if 'delete' in plan_type:
            obj_list.reverse()
        return obj_list
    
    def get_mo_list_with_dependency(self, obj='', plan_type='', excluded_objs=[]):
        plan_file_names=[]

        obj_list = self._get_mo_list_with_dependency(obj, plan_type)
        if plan_type == 'create':
            plan_type = ''
        for excluded_obj in ['RNC','RNAC','RNFC','RNHSPA','RNMOBI','RNPS','RNRLC','RNTRM']:
            if excluded_obj not in excluded_objs:
                excluded_objs.append(excluded_obj)
        if plan_type != '':
            plan_type = '_'+plan_type

        for o in obj_list:
            if o not in excluded_objs:
                plan_file_names.append('RNWPLAND_%s%s.XML' % (o, plan_type))
        return plan_file_names
    
    def combine_mo_plan_with_dependency(self, obj, include_obj_itself=False, plan_operation='create'):
        if include_obj_itself == True:
            print "include obj itself"
            sourcefiles = self.get_mo_list_with_dependency(obj, plan_operation)
        else:
            print "exclude obj itself"
            sourcefiles = self.get_mo_list_with_dependency(obj, plan_operation, [obj])
        dstfile = 'RNWPLAND_COMBINE_%s_%s.XML' % (obj, plan_operation)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        old_dir = plan_generate.plan_generate().get_old_dir(base_dir)        
        source_dir = old_dir
        if plan_operation == "modify":
            plan_operation = "update"
        self.combine_plans(sourcefiles, dstfile, source_dir, plan_operation)
        return dstfile
    
    def combine_all_rnc_objects_plan(self):
        plan_file_names=[]
        obj_list = ['RNC','RNAC','RNFC','RNHSPA','RNMOBI','RNPS','RNRLC','RNTRM']
        for o in obj_list:
            plan_file_names.append('RNWPLAND_%s.XML' % o)
        dstfile = 'RNWPLAND_COMBINE_RNC_all_objects.XML'
        base_dir = os.path.dirname(os.path.abspath(__file__))
        old_dir = plan_generate.plan_generate().get_old_dir(base_dir)        
        source_dir = old_dir
        self.combine_plans(plan_file_names, dstfile, source_dir)
        return dstfile
    
    def combine_all_mo_plan(self, plan_operation='create', excluded_objs=[]):
        if not hasattr(excluded_objs, '__iter__'):
            excluded_objs = [excluded_objs]
        dstfile = 'RNWPLAND_COMBINE_all_%s.XML' % plan_operation
        if plan_operation == 'create':
            plan_operation = ''
            for excluded_obj in ['RNCSRV','PRNC','DATSYN']:
                if excluded_obj not in excluded_objs:
                    excluded_objs.append(excluded_obj)        
        if plan_operation == 'delete':
            for excluded_obj in ['RNC','RNAC','RNFC','RNHSPA','RNMOBI','RNPS','RNRLC','RNTRM','CMOB']:
                if excluded_obj not in excluded_objs:
                    excluded_objs.append(excluded_obj)
        sourcefiles = self.get_mo_plan_file_list(plan_operation, excluded_objs)
        print sourcefiles, dstfile
        base_dir = os.path.dirname(os.path.abspath(__file__))
        old_dir = plan_generate.plan_generate().get_old_dir(base_dir)        
        source_dir = old_dir
        
        if plan_operation == '':
            plan_operation = 'create'
        if plan_operation == 'modify':
            plan_operation = 'update'
        self.combine_plans(sourcefiles, dstfile, source_dir, plan_operation)
        return dstfile

    def create_params_dict_from_template(self, param_name, param_value, param_type="scalar"):
        param_dict = {}
        param_dict.update({param_name: [param_value, param_type]})
        return param_dict

    def get_da_plan_mo_name(self, file_name):
        """
        Get mo names from plan
        """
        f = open(file_name)
        plan_text = f.read()
        plan = XML_utils.XML_utils().get_cmdata_elem_from_text(plan_text)
        print '*DEBUG* %s' % plan_text
        mo_names = XML_utils.XML_utils()._get_plan_mo_names(plan)
        return mo_names.pop()
    
    def get_mo_dict_from_file(self, source_file):
        """
        Get MO dict from plan file
        """
        mo_dict = {}
        mo_xml_f = open(source_file, 'r')
        mo_xml = mo_xml_f.read()
        mo_xml_f.close()
        new_rnc_id = TestResources.getResources('RNC-ID')
        mo_xml = plan_generate.plan_generate().replace_rnc_id_string(mo_xml, new_rnc_id)
        
        for mo in re.finditer('<managedObject class="(\S+)".*distName="(\S+)"', mo_xml):
            if mo.group(1) in mo_dict:
                if not hasattr(mo_dict[mo.group(1)], '__iter__'):
                    mo_dict[mo.group(1)]=[mo_dict[mo.group(1)]]
                mo_dict[mo.group(1)].append(mo.group(2))
            else:
                mo_dict.update({mo.group(1): [mo.group(2)]})
                
        return mo_dict

    def combine_plans(self, sourcefiles, dstfile, source_dir='test_files', plan_operation=None):
        """
        Combines multiple plans to a single XML file
        returns a dict of all MOs in the combined plan {MONAME:DISTNAME}
        Note, only one dict entry per MO type
        """
        hdr = """<raml version="2.1" xmlns="raml21.xsd">
                    <cmData type="actual" scope="all" domain="RNCRNWCMPLAN" adaptationVersionMajor="RN7.0">
                      <header>
                         <log dateTime="2012-11-06T09:18:41" action="modified" user="CRNC" appInfo="cRNC OMS">cRNC plan upload</log>
                      </header>"""

        if not hasattr(sourcefiles, '__iter__'):
            sourcefiles= [sourcefiles]

        dst = open(dstfile,'w')
        dst.write(hdr)
        mo_dict={}
        for f in sourcefiles:
            mo_xml_f = open(os.path.join(source_dir, f), 'r')
            mo_xml = mo_xml_f.read()
            mo_xml_f.close()
            new_rnc_id = TestResources.getResources('RNC-ID')
            new_oms_ip = TestResources.getResources('OMSIPADDRESS')
            mo_xml = plan_generate.plan_generate().replace_rnc_id_string(mo_xml, new_rnc_id)
            mo_xml = plan_generate.plan_generate().replace_oms_ip_string(mo_xml, new_oms_ip)
            
            if plan_operation is not None:
                mo_xml = re.sub('operation="([a-z]*")','operation="%s"' % plan_operation, mo_xml)
            for mo in re.finditer('<managedObject class="(\S+)".*distName="(\S+)"', mo_xml):
                mo_dict[mo.group(1)]=mo.group(2)
            dst.write(mo_xml[mo_xml.find('<managedObject'):mo_xml.rfind('</cmData')])
            dst.write('\n')
        dst.write('</cmData></raml>')
        return mo_dict

    def combine_plans_without_replace_rncid(self, sourcefiles, dstfile, source_dir='test_files', plan_operation=None):
        """
        Combines multiple plans to a single XML file
        returns a dict of all MOs in the combined plan {MONAME:DISTNAME}
        Note, only one dict entry per MO type
        """
        hdr = """<raml version="2.1" xmlns="raml21.xsd">
                    <cmData type="actual" scope="all" domain="RNCRNWCMPLAN" adaptationVersionMajor="RN7.0">
                      <header>
                         <log dateTime="2012-11-06T09:18:41" action="modified" user="CRNC" appInfo="cRNC OMS">cRNC plan upload</log>
                      </header>"""

        if not hasattr(sourcefiles, '__iter__'):
            sourcefiles= [sourcefiles]

        dst = open(dstfile,'w')
        dst.write(hdr)
        mo_dict={}
        for f in sourcefiles:
            mo_xml_f = open(f, 'r')
            mo_xml = mo_xml_f.read()
            mo_xml_f.close()
           
            new_oms_ip = TestResources.getResources('OMSIPADDRESS')
            mo_xml = plan_generate.plan_generate().replace_oms_ip_string(mo_xml, new_oms_ip)
            
            if plan_operation is not None:
                mo_xml = re.sub('operation="([a-z]*")','operation="%s"' % plan_operation, mo_xml)
            for mo in re.finditer('<managedObject class="(\S+)".*distName="(\S+)"', mo_xml):
                mo_dict[mo.group(1)]=mo.group(2)
            dst.write(mo_xml[mo_xml.find('<managedObject'):mo_xml.rfind('</cmData')])
            dst.write('\n')
        dst.write('</cmData></raml>')
        return mo_dict


    def create_wcel_mini_plan(self, admin_state = None, operation='create', objectWCEL = "WCEL", dist_name = "RNC-1/WBTS-1/WCEL-1"):

        params = """
                     <p name="CId">1</p>
                     <p name="LAC">1</p>
                     <p name="SAC">1</p>
                     <p name="RAC">1</p>
                     <p name="PriScrCode">1</p>
                     <p name="UARFCN">10251</p>
                     <p name="CellRange">100</p>
                     <p name="RtFmcsIdentifier">1</p>
                     <p name="NrtFmcsIdentifier">1</p>
                     <p name="RtFmcgIdentifier">1</p>
                     <p name="NrtFmcgIdentifier">1</p>
                     <p name="RtFmciIdentifier">1</p>
                     <p name="NrtFmciIdentifier">1</p>
                     <p name="EbNoSetIdentifier">1</p>
                     <p name="Tcell">1</p>
                     <list name="URAId">
                         <p>1</p>
                     </list>
                     <list name="WCELGlobalCNid">
                         <item>
                             <p name="WCELMCC">123</p>
                             <p name="WCELMNC">45</p>
                             <p name="WCELMNCLength">2</p>
                         </item>
                     </list>
                     <p name="FMCLIdentifier">1</p>
                     <p name="FMCLIdentifier">1</p>
                     <p name="AdminCellState">%s</p>
                 """ % admin_state
        dist_name = string.replace(dist_name, 'RNC-1', TestResources.getResources('RNC-ID'))
        plan = self.generate_empty_download_plan(objectWCEL, dist_name, operation)
        self.add_plan_param(plan, params)

        return plan

    def check_wcel_state(self, state):
        """
        Print out WCEL states
        """
        if TestResources.ismcRNC():
            output = il_connections.execute_mml("/opt/nokiasiemens/pac_ruoste_e1/script/mcruoste.sh -wcelstatus -wbts=1")
        else:
            output = self.execute_service_terminal_commands(['ZL:3', 'ZLEL:3:,W0-BLCODE/RUOSTEQX.IMG','Z3SA:1'],'Y')

        for line in output.split('\n'):
            if int(state) == 0:
                if(line.find("BL (U,W,I)") != -1) or (line.find("BL (U,W)") != -1):
                    return output
            if int(state) == 1:
                if(line.find("BL (W,I)") != -1):
                    return output

        raise AssertionError('WCEL state incorrect!')

    def topology_upload(self, subtopology=None):
        """
        Executes Topoliogy Upload using Ruoste.
        Returns the result XML file as string.
        """
        if TestResources.ismcRNC():
            cmd = "/opt/nokiasiemens/pac_ruoste_e1/script/start_ruoste.sh -topology"
            if subtopology is not None:
                cmd +=' -moid=%s' % subtopology
            output = il_connections.execute_mml(cmd)
            result_file = re.search('Result file generated to (\S*)', output).group(1)
            if '.gz' in result_file:
                return il_connections.execute_mml('zcat %s' % result_file)
            else:
                return il_connections.execute_mml('cat %s' % result_file)
        else:
            cmds = ['ZL:3', 'ZLEL:3:,W0-BLCODE/RUOSTEQX.IMG','Z3MPE']
            if subtopology is not None:
                cmds.append('Z3MT:/RUNNING/PLATMP/Topology.XML,%s' % subtopology)
            else:
                cmds.append('Z3MT')
            output = self.execute_service_terminal_commands(cmds,'Y')

            if 'Error' in output:
                raise AssertionError(output)

            self.ftp_get_a_file('/RUNNING/PLATMP/Topology.XML', 'Topology.XML')
            f = open('Topology.XML','r')
            xml = f.read()
            f.close()
            os.unlink('Topology.XML')
            return xml

    def start_message_monitoring(self, conditions=None):
        if TestResources.ismcRNC():
            return MsgMonitoringHandle(conditions)
        else:
            print 'crnc monitoring'
            h =  CRNCMsgMonitoringHandle(conditions)
            print 'handle',h
            return h

    def send_nbap_sctp_link_state_event(self, ipnb_id, link_id):
        data_part_str = 'XW%s,%s,3,XWFFFF,XWFFFF,XWFFFF,XWFFFF,3' % (ipnb_id.upper(), link_id.upper())
        if TestResources.ismcRNC():
            # Border test mode, not waiting ack from oms
            il_connections.execute_mml('ilcliru.sh OMU dmxsend -- -h \*,\*,a0f,2,0,1,0,92fb -b %s' % data_part_str)
        else:
            self.execute_service_terminal_commands("ZOS:*,*,A0F,2,,1,,92FB,,,%s" % data_part_str)

    def send_nbap_link_state(self, coco_id = '1', link_id = '2', new_state='3', icsu='4', change_origin='5'):
        self.send_message('A0F', '2', 'D4D3', 'XW%s,%s,%s,XW%s,%s' % (coco_id, link_id, new_state, icsu, change_origin))

    def send_wsta_modified_event(self, wbts = '1', lcel = '1', hsdpa_op_state='1', edch_op_state='1', change_origin='5'):
        bits = (22,24)  # first dword
        mask = 0
        for b in bits:
            mask |= 1 << b

        data_part_str = ','.join(
                             ('XW1', # wbts id
                              'A2', # align
                              'XD1', # lcel id
                              '%s' % hsdpa_op_state,
                              '0,0,0' +',XD0' * 9,
                              '%s' % edch_op_state,
                              '0,0,0,0,0,0,0',
                              'XD%X' % mask +',XD0' * 65,
                              'XD1', # Plan id
                              '%s' % change_origin,
                              'A3'
                              ))
        if TestResources.ismcRNC():
            # Border test mode, not waiting ack from oms
            data_part_str = data_part_str.replace('A1', '0')
            data_part_str = data_part_str.replace('A2', 'XW0')
            data_part_str = data_part_str.replace('A3', '0,0,0')
        else:
            data_part_str = data_part_str.replace('A1,', '')
            data_part_str = data_part_str.replace('A2,', '')
            data_part_str = data_part_str.replace('A3,', '')
        self.send_message('A0F', '2', 'AFEE', data_part_str)

    def _xword_to_bytes(self, strParam, byte_count):
        bytesParam=[]
        i = 0 
        while i < byte_count:
            i = i +1
            b = strParam[len(strParam)-2:len(strParam)]
            strParam = strParam[:len(strParam)-2]
            if len(b) == 0:
                bytesParam.append('0')
            else:
                bytesParam.append(b)
        return bytesParam

    def _send_from_mem(self, fam, proc, number, msg):
        bytesParam = ['0','0']  # computer
        bytesParam.extend(self._xword_to_bytes(fam, 2))
        bytesParam.extend(self._xword_to_bytes(proc, 2))
        bytesParam.extend(['0','1','0','0']) # focus, attributes, group
        bytesParam.extend(self._xword_to_bytes(number, 2))
        bytesParam.extend(self._xword_to_bytes('0', 2)) # phys computer
        for p in msg.split(','):
            if p == '':
                bytesParam.append('0')
            elif p[0:2] == 'XD':
                bytesParam.extend(self._xword_to_bytes(p[2:], 4))
            elif p[0:2] == 'XW':
                bytesParam.extend(self._xword_to_bytes(p[2:], 2))
            else:
                if len(p) > 2:
                    raise AssertionError('Invalid byte len %s' % p)
                bytesParam.append(p)
        msg_length = len(bytesParam) + 2
        bytesParam[0:0] = self._xword_to_bytes('%X' % msg_length, 2)
        fill_cmds=[]
        for i in range(0, len(bytesParam), 15):
            data_str = ','.join(bytesParam[i:i+15])
            fill_cmds.append('ZDF:G40.%X,%X,%s' % (i,i+15, data_str))
        self.execute_service_terminal_commands(fill_cmds)
        return self.execute_service_terminal_commands(['ZOSM:G40'])

    def send_message(self, fam, proc, number, data):
        """
        Send a dmx msg, fam, proc, number given as string (in hex format)
        data given comma separated
        """
        if TestResources.ismcRNC():
            il_connections.execute_mml('ilcliru.sh OMU dmxsend -- -h \*,\*,%s,%s,0,1,0,%s -b %s' % (fam,proc,number, data))
        else:
            if len(data) > 190:
                # Cannot send this long msg from cmd prompt, must fill it to mem
                out = self._send_from_mem(fam, proc, number, data)
            else:
                out = self.execute_service_terminal_commands(["ZOS:*,*,%s,%s,,1,,%s,,,%s" % (fam, proc, number, data)])
            if 'SENT MESSAGE HEADER' not in out:
                raise AssertionError('message sending failed %s' % out)

    def send_lcel_modified_event(self):
        # Setting bits for all fields in lcel_modified event (bits from lcel_t)
        bits1 = (5,8,9,26)  # first dword
        bits2 = (32,34,41,42,43,44,46) #second dword
        mask1 = 0
        for b in bits1:
            mask1 |= 1 << b
        mask2 = 0
        for b in bits2:
            mask2 |= 1 << (b - 32)

        data_part_str = ','.join(
                             ('XW1', # wbts id
                              'A2', # align
                              'XD1', # lcel id
                              '2', # hsdha capa
                              'A1', # align
                              'XW3', # dl pwr capa
                              '4', #edch capa
                              'A3',  # align
                              'XD%X,' % mask1 + 'XD%X' % mask2 + ',XD0' * 64,
                              '5', # CO
                              'A3',  #align
                              'XD6', # plan id
                              '7', # pic pool
                              '8', # pic state
                              '9', # icr capa ind
                              'A', # evam capa
                              'B', # hsrac capa
                              'C', # ench fact
                              'D', # enh ue
                              'F', # aar
                              '10', #dban
                              'A3'
                              ))
        if TestResources.ismcRNC():
            # Border test mode, not waiting ack from oms
            data_part_str = data_part_str.replace('A1', '0')
            data_part_str = data_part_str.replace('A2', 'XW0')
            data_part_str = data_part_str.replace('A3', '0,0,0')
        else:
            data_part_str = data_part_str.replace('A1,', '')
            data_part_str = data_part_str.replace('A2,', '')
            data_part_str = data_part_str.replace('A3,', '')
        self.send_message('A0F', '2', 'AFFD', data_part_str)

    def set_border_test_mode_on(self):
        """
        Activates BORDER's test mode where is does not wait for the OMS to reply
        the OMS Change Notification message.
        """
        if TestResources.ismcRNC():
            # Border test mode, not waiting ack from oms
            il_connections.execute_mml('ilcliru.sh OMU dmxsend -- -h 92,\*,a0f,2,0,1,0,6034 -b 63,1')
            il_connections.execute_mml('ilcliru.sh OMU dmxsend -- -h 20,\*,a0f,2,0,1,0,da02')
        else:
            self.execute_service_terminal_commands("ZOS:92,*,A0F,2,,1,,6034,,,63,1")
            self.execute_service_terminal_commands("ZOS:20,*,A0F,2,,1,,DA02,,,")

    def set_border_test_mode_off(self):
        """
        BORDER's test mode off: Now BORDER again waits for the OMS replies to
        OMS Change Notification messages.
        """
        if TestResources.ismcRNC():
            il_connections.execute_mml('ilcliru.sh OMU dmxsend -- -h 92,\*,a0f,2,0,1,0,6034 -b 63,0')
        else:
            self.execute_service_terminal_commands("ZOS:92,*,A0F,2,,1,,6034,,,63,0")

    def stop_message_monitoring(self, mon_handle):
        return mon_handle.stop_monitoring()

    def start_oms_change_notification_monitoring(self):
        """
        Start monitoring bs_om_relay_s messages sent by BORDER
        """
        return self.start_message_monitoring('S:(OFAM=0A0F)AND(NUM=0DA02)') # BORDER, bs_om_relay_s
        #caution, add more monitored prb will cause case fail.
        #return self.start_message_monitoring('S:(FAM=0A0F,04EE)') # BORDER, bs_om_relay_s

    def stop_oms_change_notification_monitoring(self, mon_handle):
        """
        Stop monitoring bs_om_relay_s messages sent by BORDER
        """
        mon_handle.stop_monitoring()
    
    def start_oam_message_monitoring(self):
        """
        Start monitoring oam messages
        OMU ARM=02F7, MNM=03C6, RAK=04EE, VEX=04EF, REZ=04FA, BOI=0506, RAV=050A, REK=050B, RAY=0523, PAB=0524, RBR=054E, BOR=0A0F
        """
        return self.start_message_monitoring('SR:(FAM=0A0F,04EE,050A,0523,0524)')
    
    def stop_oam_message_monitoring(self, mon_handle):
        if TestResources.ismcRNC():
            mon_handle.stop_monitoring_keep_tmp_file()
            self.sftp_get_a_file("MonitoredMessages.log", mon_handle.tmp_file)
            mon_handle.delete_tmp_file()
        else:
            mon_handle.stop_monitoring()

    def get_oms_change_event_xml(self, mon_handle, dist_name, operation):
        """
        Returns the OMS change notification event (XML, as string) sent by BORDER in bs_om_relay_s message.
        """

        search_re = 'distName="%s".*operation="%s"' % (dist_name, operation)
        for m in mon_handle.get_messages():
            d =  m.get_data_in_ascii()
            #print 'msg',d
            start_index = d.find('<?xml')
            if start_index >= 0:
                xml_str = d[start_index:d.rfind('</raml>') + len('</raml>')]
                if re.search(search_re, xml_str) is not None:
                    mon_handle.remove_message(m)
                    return xml_str
        raise AssertionError('Object %s operation %s not found from monitoring' % (dist_name, operation))

class NotADMXMessage(Exception):
    pass

class DmxMsg():
    def __init__(self, raw_data):
        """
        MONITORING TIME: 2014-08-28    15:39:15.650870    0009EE76 53FF4D23
        RECEIVED BY: 0A0F 0000 00
        BOTTOM: C000 0A0F 0000 00 00 01 00 F40C 0000 00 00 0000 00009F04
        MONITORED MESSAGE: 0016 C000 00A0 0001 00 33 0000 0001 0000
        00 0F 00 00 00 00
        """
        self.raw_data = raw_data
        self.data_part = ''
        self.monitoring_time = ''
        self.received_by = ''
        self.sent_by = ''
        self.bottom = ''
        self.monitored_msg = ''

        if raw_data.find('MONITORING TIME') != 0:
            raise NotADMXMessage('not a DMX msg')

        for l in raw_data.split('\n'):
            if 'MONITORING TIME' in l:
                self.monitoring_time = l
            elif 'RECEIVED BY' in l:
                self.received_by = l
            elif 'SENT BY' in l:
                self.sent_by = l
            elif 'BOTTOM' in l:
                self.bottom = l
            elif 'MONITORED MESSAGE' in l:
                self.monitored_msg = l
            elif l[0] in string.hexdigits and l[1] in string.hexdigits:
                self.data_part += ' ' + l

    def get_data_in_ascii(self):
        """
        Returns data part as ascii string
        """
        s = ''
        for b in self.data_part.split(' '):
            if len(b) == 0:
                continue
            try:
                char = '%c' % int(b, 16)
                if char in string.printable:
                    s += char
            except Exception as e:
                print b
                print e
                raise e
        return s

    def __str__(self):
        return self.raw_data

class MsgMonitoringHandle:
    def __init__(self, condition=None):
        """
        Only OMU is now supported
        """
        cmd = 'monster'
        self.tmp_file = '/tmp/foo_monitoring_%d.txt' % random.randint(0,999999)
        if condition is not None:
            cmd += ' -c "' + condition + '"'
        cmd +=' > %s &' % self.tmp_file
        output = il_connections.execute_mml(cmd)

        #print out.split('\n')
        self.mon_job = output.split('\n')[1].split()[0]
        self.running = True

    def _stop_and_get_data(self):
        il_connections.execute_mml_without_check('kill %%%s' % self.mon_job.strip('[]'))
        while True:
            if il_connections.execute_mml('jobs').find(self.mon_job) < 0:
                break
            time.sleep(1)

        self.running = False
        self.monitoring_data = il_connections.execute_mml('cat %s' % self.tmp_file)
        #connections.execute_mml("cp %s /tmp/messageMonitor.txt" % self.tmp_file)  
        il_connections.execute_mml('rm -f %s' % self.tmp_file)
        self.tmp_file = None

    def _stop_and_get_data_keep_file(self):
        il_connections.execute_mml_without_check('kill %%%s' % self.mon_job.strip('[]'))
        while True:
            if il_connections.execute_mml('jobs').find(self.mon_job) < 0:
                break
            time.sleep(1)

        self.running = False
        self.monitoring_data = il_connections.execute_mml('cat %s' % self.tmp_file)
        #connections.execute_mml("cp %s /tmp/messageMonitor.txt" % self.tmp_file)  
        
    def delete_tmp_file(self):
        il_connections.execute_mml('rm -f %s' % self.tmp_file)
        self.tmp_file = None

    def stop_monitoring_keep_tmp_file(self):
        if not self.running:
            raise AssertionError('Monitoring is not running')
        self._stop_and_get_data_keep_file()
        self.msgs = []
        for m in re.split('\n\n+', self.monitoring_data.replace('\r','')):
            try:
                new_msg = DmxMsg(m)
                self.msgs.append(new_msg)
            except NotADMXMessage:
                pass
        return self.msgs
        
    def stop_monitoring(self):
        if not self.running:
            raise AssertionError('Monitoring is not running')
        self._stop_and_get_data()
        self.msgs = []
        for m in re.split('\n\n+', self.monitoring_data.replace('\r','')):
            try:
                new_msg = DmxMsg(m)
                self.msgs.append(new_msg)
            except NotADMXMessage:
                pass
        return self.msgs

    def get_messages(self):
        return self.msgs

    def remove_message(self, m):
        self.msgs.remove(m)

class CRNCMsgMonitoringHandle(MsgMonitoringHandle):
    def __init__(self, condition=None, size='30000'):
        commands = ['ZOEBR::%s' % size]
        if condition is not None:
            commands.append('ZOEC::' + condition)
        commands.append('ZOEM')
        metadata_test_framework().execute_service_terminal_commands(commands)
        self.running = True

    def _stop_and_get_data(self):
        self.monitoring_data = metadata_test_framework().execute_service_terminal_commands(['ZOES', 'ZOEG','ZOEQ'])
        try:
            f2 = open("MonitoredMessages.log", 'w+')
            f2.write(self.monitoring_data)
            f2.flush()
            f2.close()
        except:
            print "can't open file MonitoredMessages.log"

def test(expected, given):
    if expected != given:
        print 'Error',expected, given

def main():

    mf = metadata_test_framework()
    TestResources.getAndSetResources('10.68.145.147')
    #TestResources.getAndSetResources('10.56.116.8')
       
    #mf.metadata_connect_to_mc('10.56.116.8',)
    mf.metadata_connect()
    #mf.copy_test_files_ifneeded()
    #mf.clear_rnwdb_thoroughly()
    #mf.wait_rnwdb_normal()    
    #print mf.get_mo_list_with_dependency('WCEL')
    #IpaMml.connections.execute_mml_without_check("ZIAH:OMSUSR:PROFILE;","SYSTEM","SYSTEM")
    #mf.get_oms_conn_status()
    mf.add_RNCIPAddress()
    """
    print mf.get_mo_dict_from_file('ADJI_modify.XML')
    mf.combine_mo_plan_with_dependency('WCEL', 'create')
    mf.combine_all_rnc_objects_plan()
    #created_file_name = mf.combine_all_mo_plan('modify')
    plan1 = XML_utils.XML_utils().get_cmdata_from_file("ADJI_modify1.XML")
    plan2 = XML_utils.XML_utils().get_cmdata_from_file("ADJI_modify.XML")

    mo_names1 = XML_utils.XML_utils()._get_plan_mo_names(plan1, 'distName')
    mo_names2 = XML_utils.XML_utils()._get_plan_mo_names(plan2, 'distName')

    diff_list_all = XML_utils.XML_utils().compare_plans_cmdata_into_dict(plan1, plan2)
    XML_utils.XML_utils().print_diff_dict(diff_list_all)
    """

    '''
    #output = 
    print mf._get_mo_type_list('create')
    print mf._get_mo_type_list('delete')
    '''
    
    #output = 
    """
LOADING PROGRAM VERSION 12.30-0

RNC       IPA2800                   2014-12-18  10:20:21

DATABASE  OCCURRENCE  WO/SP               STATE           SUBSTATE

RAQUEL    0           WO                  NORMAL          NORMAL         

RAQUEL    0           SP                  ABNORMAL        ABNORMAL  

MEMORY UPDATES        DISK UPDATES        TRANSACTION     BACK UP
PREVENTED             PREVENTED           OVERFLOW        IS ON
NO                    YES                 NO              NO             

LATEST TRANSACTIONS:
REQUESTOR`S COMPUTER  REQUESTOR`S FAMILY  TRANSACTION ID  TRANSACTION PHASE
5002                  0523                001B            EXEC SUCCESS      
5002                  04EE                0084            EXEC SUCCESS      
5002                  0523                001B            EXEC SUCCESS      
5002                  0523                001B            EXEC SUCCESS      
5002                  0523                001B            EXEC SUCCESS      

COMMAND EXECUTED


DATABASE HANDLING COMMAND <DB_>
    """

"""
    lines = string.strip(output).split('\n')
    i = 0
    for line in lines:
        i += 1;
        if "rnc_id" in line:
            line = lines[i+1]
            rnc_id = int(string.strip(line))
            print rnc_id
"""            
'''
    if True:
        TestResources.getAndSetResources('barbara')

        mf.metadata_connect_to_ipa('10.16.28.15',)
        mf.send_lcel_modified_event()
        mf.metadata_disconnect_from_ipa()
    else:

        test(['0F','A'], mf._xword_to_bytes('A0F', 2))
        test(['0F','A','0','0'],mf._xword_to_bytes('A0F', 4))
        test(['45','23','1','0'],mf._xword_to_bytes('12345', 4))
'''


if __name__=="__main__":
    main()
