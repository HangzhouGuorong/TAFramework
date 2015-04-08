import os.path
from types import MethodType, FunctionType
from ILRobotAPI import get_version
ROBOT_VERSION = get_version()

from resources.metadata_test_framework import *
from resources.parameter_utils import *
from resources.plan_generate import *
from resources.profiling_utils import *
from resources.test_framework import *
from resources.TestResources import *
from resources.XML_utils import *
from resources.log_utils import *

try:
    mod = __import__("version", globals())
    __version__ = mod.version
except:
    __version__ = "0.0.0"

class foolib:
    """
    This purpose of this class is to make it easy to utilize A-Team's TA framework.
    Those useful functions will be put into this library
    """

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self):
        self._keywords = self._scan_keywords()
        self.framework = metadata_test_framework()
        self.log_utils = log_utils()
        self.XML_utils = XML_utils()
        self.parameter_utils = parameter_utils()
        self.plan_generator = plan_generate.plan_generate()
        
    def get_common_version(self):
        """Returns the version of the underlying IL Library

        #developer_used
        """
        return __version__

    def get_keyword_names(self):
        return self._keywords.keys() + self._get_my_keywords()

    def __getattr__(self, name):
        try:
            return self._keywords[name]
        except KeyError:
            raise AttributeError

    def _get_my_keywords(self):
        return [ attr for attr in dir(self)
                 if not attr.startswith('_') and type(getattr(self, attr)) is MethodType ]

    def _scan_keywords(self):
        keywords = []
        basedir = os.path.dirname(os.path.abspath(__file__))    # CM/Common/FOOLIB
        for path in os.listdir(basedir):
            path = os.path.join(basedir, path)      # CM/Common/FOOLIB/resources
            if os.path.isdir(path):
                empty_dir=self._check_empty_dir(path)
                if empty_dir:
                    continue
                keywords += self._scan_keywords_from_dir(path)
            elif path.endswith('.py') :
                keywords += self._scan_keywords_from_file(path)
        return dict([ (kw.__name__, kw) for kw in keywords ])

    def _scan_keywords_from_file(self, path):
        mod_name = os.path.splitext(os.path.basename(path))[0]
        return self._scan_keywords_from_module(mod_name)

    def _scan_keywords_from_dir(self, path):
        mod_name = os.path.basename(path)      #resources
        return self._scan_keywords_from_module(mod_name)

    def _scan_keywords_from_module(self, name):
        mod = __import__(name, globals())
        kws = [ getattr(mod, attr) for attr in dir(mod)
                if not attr.startswith('_') ]
        
        kws = [kw for kw in kws if type(kw) in [MethodType, FunctionType]]
        #return false, if the keyword isn't defined in the module. It's used to
        #avoid the keyword be exported that importing from other module.
        def check_in_module(kw, mod):
            kw_file = os.path.abspath(kw.func_code.co_filename)
            mod_file = os.path.abspath(mod.__file__)
            (def_mod) = os.path.dirname(kw_file)
            (cur_mod) = os.path.dirname(mod_file)
            result =  (def_mod.lower() == cur_mod.lower() or def_mod.replace(cur_mod,'',1).strip(os.path.sep) in os.listdir(cur_mod))
            if result == False:
                #print kw, def_mod.lower(), "!=", cur_mod.lower()
                '''print "'%s' defined in '%s' != %s" % (kw.__name__, 
                                                           kw_file, 
                                                           mod_file)
                '''
                bn = lambda x:os.path.basename(x).lower()
                if bn(def_mod) == bn(cur_mod) and mod_file.endswith(".pyc") and not getattr(sys, 'frozen', ''):
                    print "!!!Please remove all .pyc in library path!!!"
                    sys.exit(1)
            if not getattr(sys, 'frozen', ''):
                return result
            else:
                return True

        return [ kw for kw in kws if check_in_module(kw, mod) ]

    def _check_empty_dir(self,path):
        empty=True
        files=os.listdir(path)
        for filename in files:
            if str(filename).endswith("py"):
                empty=False
        if empty:
            self._remove_pyc_in_directory(path)
        return empty

    def _remove_pyc_in_directory(self,directory):
        if str(directory).endswith('.svn'):return
        paths = os.listdir(directory)
        for path in paths:
            path = os.path.join(directory, path)
            if os.path.isdir(path):
                self._remove_pyc_in_directory(path)
            elif str(path).endswith(".pyc"):
                os.remove(path)
        paths = os.listdir(directory)
        if len(paths)==0:
            os.rmdir(directory)

    """
    ############################### Framework functions #####################################
    """
           
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
        self.framework.metadata_connect()

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
        return self.framework.download_plan(plan_file, should_succeed, activate, task_id, should_activation_succeed)
    
    def activate_plan(self, task_id = None):
        """This keyword activate a plan with task_id
        | Input Paramaters | Man. | Description |
        | task_id          | No   | Identifies to task |
        | Return Value     |
        Plan activation result is returned
        """ 
        return self.framework.activate_plan(task_id)

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
        return self.framework.direct_activate(plan_file, should_succeed, task_id, delete_incoming_adj)
    
    def direct_obj_inquire(self, moid):
        """
        This keywords executes direct object inquiry.
        It returns the contents of the inquiry as string.
        """
        return self.framework.direct_obj_inquire(moid)
    
    def upload_plan(self, task_id=None, return_plan_content=True):
        """
        This keywords executes plan upload using fsclish (mcRNC) or RUOSTE service terminal (cRNC).
        It returns the contents of the plan file as string.
        """
        return self.framework.upload_plan(task_id, return_plan_content)
            
    def topology_upload(self, subtopology=None):
        """
        Executes Topoliogy Upload using Ruoste.
        Returns the result XML file as string.
        """
        return self.framework.topology_upload(subtopology)

    def metadata_disconnect(self):
        """
        Disconnect from metadata test bench.
        """
        self.framework.metadata_disconnect()
        
    def check_rnc_id_match(self):
        """
        Check rnc_id on RNC matches the rnc_id in resources
        """
        return self.framework.check_rnc_id_match()

    def check_clear_rnwdb_thoroughly_needed(self):
        """
        Check clear rnwdb thoroughly needed
        """
        return self.framework.check_clear_rnwdb_thoroughly_needed()

    def clear_rnwdb_thoroughly(self):
        """
        This keyword clears the radio network database throughly
        """
        self.framework.clear_rnwdb_thoroughly()    
        
    def clear_rnwdb(self):
        """
        This keyword clears the radio network database
        """
        return self.framework.clear_rnwdb()
        
    def clear_all_except_rnc_objs_from_db(self):
        """
        This keyword clears all managed objects except rnc objects
        """
        return self.framework.clean_all_except_rnc_objs_from_db()       
    
    def make_delete_plan_from_upload_plan(self, ul_plan):
        """
        This keyword make delete plan from upload plan
        """
        return self.framework.make_delete_plan_from_upload_plan(ul_plan)

    def my_setup(self, loglevel="info"):
        """
        This keyword set and get info of test environment
        """
        self.framework.my_setup()
    
    def mcRNC_set_log_level(self, level="info"):
        """
        This keyword set mcRNC log level
        """
        return self.framework.mcRNC_set_log_level(level)
        
    def restore_rnc_to_initial_state(self):
        """
        This keyword restore RNC to initial state
        """
        self.framework.restore_rnc_to_initial_state()
        
    def create_base_config_for_object(self, obj, create_object_itself=True):
        """
        Create Initial RNC config when RNW DB is empty
        """
        self.framework.create_base_config_for_object(obj, create_object_itself)
        
    def get_mo_dict_from_file(self, source_file):
        """
        Get MO dict from plan file
        """
        return self.framework.get_mo_dict_from_file(source_file)
        
    def get_mo_plan_file_list(self, plan_type='', excluded_objs=[]):
        """
        This keyword get mo plan file
        """
        return self.framework.get_mo_plan_file_list(plan_type, excluded_objs)
        
    def combine_all_mo_plan(self, plan_operation='create'):
        """
        This keyword combine all mo plan files
        """
        return self.framework.combine_all_mo_plan(plan_operation)   
    
    def combine_all_rnc_objects_plan(self):
        """
        This keyword combine all rnc mos plan files
        """
        return self.framework.combine_all_rnc_objects_plan()
        
    def combine_mo_plan_with_dependency(self, obj, include_obj_itself=False, plan_operation='create'):
        """
        This keyword combine plan files for create managed object on RNC when RNWDB is empty
        """
        return self.framework.combine_mo_plan_with_dependency(obj, include_obj_itself, plan_operation)    
    
    def combine_plans(self, sourcefiles, dstfile, source_dir='test_files', plan_operation=None):
        """
        This keyword combine plan files
        """
        return self.framework.combine_plans(sourcefiles, dstfile, source_dir, plan_operation)
    
    def combine_plans_without_replace_rncid(self, sourcefiles, dstfile, source_dir='test_files', plan_operation=None):
        """
        Combine plan files without replacing RNC id
        """
        return self.framework.combine_plans_without_replace_rncid(sourcefiles, dstfile, source_dir, plan_operation)
    
    def clear_prnc_info(self, requested_mode=['-','STANDARD','PRIMARY']):

        """
        This Keyword clears PRNC info in RNW Database
        in cRNC
        R0SMAN manages reciliency info which is stored in r0sfle.xml.
        This KW patches the PRNC node in the file and does OMU-0 state changes WO -> SP -> WO
        in which situation R0SMAN reads the XML file again
        in mcRNC
        This KW deletes records of PRNC, BKPRNC, RNCSERV, DATSYN
        """
        self.framework.clear_prnc_info_from_r0sfle(requested_mode)
    
    def add_RNCIPAddress(self):
        """
        Configures RNC and OMS connection
        """
        self.framework.add_RNCIPAddress()
    
    def enable_all_features(self):
        """
        Uses RAKTOR test mode and enables all features
        """
        self.framework.set_raktor_test_mode('ON')
        #self.framework.enable_optionality(255)
        self.framework.set_all_options('ON')
 
    def set_border_test_mode_on(self):
        """
        Activates BORDER's test mode where is does not wait for the OMS to reply
        the OMS Change Notification message.
        """
        self.framework.set_border_test_mode_on()
    
    def set_border_test_mode_off(self):
        """
        BORDER's test mode off: Now BORDER again waits for the OMS replies to
        OMS Change Notification messages.
        """
        self.framework.set_border_test_mode_off()    
    
    def set_cons_check_disabled(self, disabled = True):
        """
        Disable the consistency check
        """
        self.framework.set_cons_check_disabled(disabled)
        
    def ensure_unit0_working(self, unit=""):
        """
        This keyword ensures unit0 is in working state.
        """
        self.framework.ensure_unit0_working(unit)

    def metadata_suite_setup(self):
        """
        Test bench specific setups and other stuff
        """
        self.framework.metadata_suite_setup()
        
    def configure_oms_connection(self):
        """
        This keyword configures OMS connection
        In mcRNC: 
        configure role ssh to the IP address of the test bench
        "add networking address /QNOMU iface %s ip-address %s/24 role %s user /QNHTTPD" % (iface, ip_address, role)
        "set radio-network omsconn omsipadd %s rncid %s rncname %s " % (oms_ip_address, rnc_id[4:], rnc_name)
        In CRNC: 
        "ZL:3;", "ZLEL:3:,W0-BLCODE/RUOSTEQX.IMG", "Z3C"
        "Z3CR:%s,%s,%s" % (rnc_id[4:], oms_ip_address, rnc_name)        
        """
        self.framework.add_RNCIPAddress()
        
    def create_object_hierarchy_up_to(self, obj, create_object_itself):
        """
        This keyword creates the objects, which are required by the given object.
        It also creates the given object, if create_object_itself == True.
        """
        self.framework.create_object_hierarchy_up_to(obj, create_object_itself)
        
    def delete_object_hierarchy_down_to(self, obj, remain_object_itself):
        """
        This keyword deletes objects, which require the given object.
        It deletes also the given object, if remain_object_itself == False.
        """
        self.framework.delete_object_hierarchy_down_to(obj, remain_object_itself)

    def get_obj_from_jondoe_output(self, output):
        """
        Returns an object with field values initialized from the jondoe output

        Output:
         obj.wcel_range (CellRange)                   = 0
         obj.sac (SAC)                                = 1
         obj.hcs_prio (HCS)                           = 0

        Returns an object:
         obj.CellRange = 0
         obj.SAC =1
         obj.HCS_PRIO = 0
        """
        return self.framework.get_obj_from_jondoe_output(output)

    def upload_generated_file(self, local_name, remote_path="", remote_name=""):
        """
        Upload a file with replaced RNC-ID etc to test bench
        """
        self.framework.upload_generated_file(local_name, remote_path, remote_name)
    
    def upload_a_file(self, local_name, remote_path="", remote_name=""):
        """
        Upload a file or directory from local host to test bench
        Recursive upload of directories not supported
        """
        self.framework.upload_a_file(local_name, remote_path, remote_name)

    def ftp_get_a_file(self, remote_name, local_name):
        """
        Get a file from the curent cRNC test bench using ftp
        """
        self.framework.ftp_get_a_file(remote_name, local_name)
        
    def ftp_put_a_file(self, local_name, remote_name):
        """
        Put a file to the current cRNC test bench using ftp.
        """
        self.framework.ftp_put_a_file(local_name, remote_name)

    def sftp_get_a_file(self, local_name, remote_name):
        """
        Get a file from the current mcRNC test bench using ssh and sftp.
        """
        self.framework.sftp_get_a_file(local_name, remote_name)     
        
    def sftp_put_a_file(self, local_name, remote_name):
        """
        Put a file to the current mcRNC test bench using ssh and sftp.
        """
        self.framework.sftp_put_a_file(local_name, remote_name)
    
    def type_a_file(self, fname):
        """
        Generic Type a file KW for getting a file content
        using cat remotely over ssh in mcRNC and in CRNC by
        downloading files over FTP inspecting the contents locally
        """
        return self.framework.type_a_file(fname)

    def start_oms_change_notification_monitoring(self):
        """
        Start monitoring bs_om_relay_s messages sent by BORDER
        """
        return self.framework.start_oms_change_notification_monitoring()
    
    def stop_oms_change_notification_monitoring(self, mon_handle):
        """
        Stop monitoring bs_om_relay_s messages sent by BORDER
        """
        self.framework.stop_oms_change_notification_monitoring(mon_handle)

    def start_oam_message_monitoring(self):
        """
        Start oam message monitoring
        """
        return self.framework.start_oam_message_monitoring()
    
    def stop_oam_message_monitoring(self, mon_handle):
        self.framework.stop_oam_message_monitoring(mon_handle)
        
    def get_oms_change_event_xml(self, mon_handle, dist_name, operation):
        """
        Returns the OMS change notification event (XML, as string) sent by BORDER in bs_om_relay_s message.
        """
        return self.framework.get_oms_change_event_xml(mon_handle, dist_name, operation)      
    
    def copy_test_files_ifneeded(self):
        """
        Copy test files to RNC with correct RNC-ID and OMS-IP
        to be improved:
        Local Plan file Directory => Remote Plan file Directory
        """
        self.framework.copy_test_files_ifneeded()
        
    def all_RNC_objects_exist_in_db(self):
        """
        Check all rnc objects exist in DB,
        If yes, return True,
        If no, return False
        """
        return self.framework.all_RNC_objects_exist_in_db()
        
    def check_all_rnc_objects(self):
        """
        Check all rnc objects exist in DB,
        If not, create all rnc objects.
        """
        self.framework.check_all_rnc_objects()
    
    def get_prnc_mode(self):
        """
        Get PRNC mode,
        Primary(Standard, Protected)
        Backup
        """
        return self.framework.get_prnc_mode()
    
    def write_plan_text_to_file(self, file_path, plan_obj):
        """
        Write plan text to file
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, file_path)
        self.plan_generator.write_plan_text_to_file(file_path, str(plan_obj))
    
    """
    ############################### Log_utils functions #####################################
    """
           
    def stop_and_start_log_monitoring(self, handle = None, unit = None):
        """
        Stop and Start Computer log monitoring
        | Input Paramaters | Man. | Description |
        | handle           | No  | Log Monitoring Handle |   
        | unit             | No  | Unit to be Log Monitored |     
        | Return Value     |
        | log handle   |
        """
        self.log_utils.stop_log_monitoring(handle)
        return self.log_utils.start_log_monitoring(unit)
    
    def stop_log_monitoring(self, handle):
        """
        Stop Computer Log monitoring
        | Input Paramaters | Man. | Description |
        | handle           | Yes  | Log Monitoring Handle |
        """
        self.log_utils.stop_log_monitoring(handle)
 
    """
    ############################### XML_utils functions #####################################
    """
    def print_diff_list(self, diff_list):
        """
        Prints the diff list
        """
        self.XML_utils.print_diff_list(diff_list)
    
    def print_diff_dict(self, diff_list_all):
        """
        Prints the diff dict
        """
        self.XML_utils.print_diff_dict(diff_list_all)    
    
    def get_cmdata_from_file(self, file_name):
        """
        This keyword read cmdata from file
        | Input Paramaters | Man. | Description |
        | file_name        | Yes  | XML plan file name |
        | Return Value     |
        | cmData   |
        """
        return self.XML_utils.get_cmdata_from_file(file_name) 
        
    def get_cmdata_elem_from_text(self, text):
        """
        Returns the cmdata element from the plan XML given as text.
        (For some reason, ElementTree does not like the raml part,
        so it is first manually removed before parsing the XML)
        | Input Paramaters | Man. | Description |
        | text             | Yes  | XML text |
        | Return Value     |
        | cmData   |
        """    
        return self.XML_utils.get_cmdata_elem_from_text(text)

    def compare_plan_cmdata_and_obj(self, obj, cmdata):
        """
        Compares cmData and Management Object read from JONDOE output
        Returns a list of differences.
        | Input Paramaters | Man. | Description |
        | obj              | Yes  | Management Object read from JONDOE |
        | cmdata           | Yes  | Configuration data   |
        | Return Value     |
        | Different List   |
        """
        self.XML_utils.compare_plan_cmdata_and_obj(obj, cmdata)    
    
    def compare_plans_cmdata(self, cmdata1, cmdata2, distName="distName"):
        """
        Compares two cmData elements
        Returns a list of differences
        | Input Paramaters | Man. | Description |
        | cmdata1          | Yes  | Configuration data 1 |
        | cmdata2          | Yes  | Configuration data 2 |
        | distName         | No   | Dist Name |
        | Return Value     |
        | Different List   |
        """
        self.XML_utils.compare_plans_cmdata(cmdata1, cmdata2, distName)  
    
    def compare_plans_cmdata_into_dict(self, cmdata1, cmdata2, distName="distName"):
        """
        Compares two cmData elements
        Returns a dictionary of differences
        | Input Paramaters | Man. | Description |
        | cmdata1          | Yes  | Configuration data 1 |
        | cmdata2          | Yes  | Configuration data 2 |
        | distName         | No   | Dist Name |
        | Return Value     |
        | Different Dictionary  |
        """
        return self.XML_utils.compare_plans_cmdata_into_dict(cmdata1, cmdata2, distName)
    
    def get_da_plan_mo_name(self, file_name):
        """
        Get mo names from plan
        """
        return self.framework.get_da_plan_mo_name(file_name)
    
    """
    ############################### parameter_utils functions #####################################
    """
    def get_param_info(self, o_name, p_name, parent_name=""):
        """
        Returns instance of Foo_param
        | Input Paramaters | Man. | Description |
        | param_info_data  | Yes  | Parameter info data |
        | Return Value     |
        | Param Info Data  |
        The operation result is returned        
        Name:                 NRIMinForCSCN
        Parent o name:        TEST
        Parent p name:        (null)
        PDDB type:            simple
        Max occurs:           1
        Attributes:           -
        Param bit:            20
        PDDB base type:       decimal
        Min value:            0
        Max value:            1024
        Step:                 -
        Default value:        1024
        Special value:        1024
        """
        foo_param = None
        try:
            param_info_data = self.framework.get_param_info_data(o_name, p_name, parent_name)
            foo_param = self.parameter_utils.get_param_info(param_info_data)
        except ParameterNotFoundException:
            print 'param %s/%s %s not found' % (o_name, parent_name, p_name)
        return foo_param

"""
############################### TestResources functions #####################################
"""

          
def setResourceVariables(varsOfResource):
    """
    Set variables of resources
    """
    TestResources.setVariables(varsOfResource)
    
def getAndSetResources(bench_name):
    """
    Get and set variables of resources
    """
    return TestResources.getAndSetResources(bench_name)


def getVariables(name):
    """
    Called by Robot when this file is given as "Variables" file in Settings part of the test suite
    Must return a dict where the keys are variable names and values are variable values
    """
    return TestResources.getAndSetResources(name)

def setVariables(varsRes):
    """
    Updates current variables, so that they will include variables given as command prompt parameters.
    This is done only once at suite setup
    e.g.:
        pybot -v HOST:10.56.116.8 -v XML_PATH:/RUNNING/CI xxx.txt
    """
    TestResources.setVariables(varsRes)
   
        
if __name__ == '__main__':
    fool = foolib()
    print fool.get_common_version()
    print fool.get_keyword_names()
    print len(fool.get_keyword_names())
    print fool.getAndSetResources("10.56.116.8")
    fool.metadata_connect()
    fool.get_param_info('RNC', 'RncOptions')
    #fool.enable_all_features()
    
