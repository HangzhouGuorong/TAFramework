current_resources = None

class TestResource:
    resource_template = {}
    def __init__(self, name, res={}):
        self.name = name
        self.res = self.resource_template.copy()
        self.res.update(res)

    def setRes(self, varsRes):
        """
        Is done only once
        """
        for k,v in varsRes.iteritems():
            self.res[k.strip('${}')] = v

    def getName(self):
        return self.name

    def getRes(self):
        return self.res


class mcTestResource(TestResource):
    resource_template = {'JONDOE_PATH': '/opt/nokiasiemens/bin',
           'XML_PATH': '/mnt/backup/ci',
           'LIBRARY_PATH': '/mnt/backup/ci',
           'UNIT': '/CFPU-0/QNOMUServer-0',
           'USERNAME': 'root',
           'PASSWORD': 'root',
           'PROFILATION': 'N'}

    def ismcRNC(self):
        return True

# XML_PATH:        directory path where XML plan files are expeceted to be stored
# AUTOLOAD_XML:    if set to value 'Y' transfer files from ./test_files to XML_PATH
#                  in suite setup
# DUMP_PREVENTION: in cRNC a c_test_msg_s is sent to RAYMAN to control it's behavior
#                  if value is set to 'Y' the DB is not dumped to disk (for
#                  faster plan handling when running test cases)
# PROFILATION:     If set to 'Y' profilation of FOO, PAB and RAY is started in
#                  the target test bench in suite setup and stopped in suite
#                  teardown.
#                  Prerequirements in cRNC:
#                    PRQFILGX compiled and available in /RUNNING/BLCODE
#                    FOO,PAB and RAY compiled using profiling options
#                  Prerequirements in mcRNC:
#                    FOO,PAB and RAY compiled with -pg option


class classicTestResource(TestResource):
    resource_template = {'USERNAME': 'SYSTEM',
           'PASSWORD': 'SYSTEM',
           'XML_PATH': '/RUNNING/CI',
           'UNIT': 'OMU-0',
           'AUTOLOAD_XML': 'N',
           'DUMP_PREVENTION': 'Y',
           'PROFILATION': 'N'}

    def ismcRNC(self):
        return False


def getAndSetResources(bench_name):
    """
    Returns the settings (variables) of given test bench. Also
    sets the current_resources global variable which then holds
    the test suite variables
    
    | Input Parameters | Man. | Description |
    | bench_name       | Yes  | Test Bench Name which is the RNC IP Address |
    """
    benches=[
         #TestResourceType(bench_name, {ResKey1: ResValue1, ResKey2: ResValue2}),
         classicTestResource('willie', {'IPADDRESS': '10.16.28.89', 'IPADDRESS1': '10.16.28.90', 'OMSIPADDRESS': '10.68.145.180', 'RNC-ID': 'RNC-1', 'RNC-NAME': 'willie'}),
         classicTestResource('barbara', {'IPADDRESS': '10.16.28.15', 'IPADDRESS1': '10.16.28.16', 'OMSIPADDRESS': '10.68.145.180', 'RNC-ID': 'RNC-1', 'RNC-NAME': 'barbara'}),
         classicTestResource('10.68.145.147', {'IPADDRESS': '10.68.145.147', 'IPADDRESS1': '10.68.145.148', 'OMSIPADDRESS': '10.68.145.180', 'RNC-ID': 'RNC-100', 'RNC-NAME': 'cRNC-100'}),
         classicTestResource('10.68.145.64', {'IPADDRESS': '10.68.145.64', 'IPADDRESS1': '10.68.145.65', 'OMSIPADDRESS': '10.68.145.180', 'RNC-ID': 'RNC-56', 'RNC-NAME': 'cRNC-56'}),
         classicTestResource('10.68.145.82', {'IPADDRESS': '10.68.145.82', 'IPADDRESS1': '10.68.145.83', 'OMSIPADDRESS': '10.68.145.180', 'RNC-ID': 'RNC-63', 'RNC-NAME': 'cRNC-63'}),
         classicTestResource('10.68.145.47', {'IPADDRESS': '10.68.145.47', 'IPADDRESS1': '10.68.145.48', 'OMSIPADDRESS': '10.68.145.180', 'RNC-ID': 'RNC-66', 'RNC-NAME': 'cRNC-66'}),
         classicTestResource('10.68.187.152', {'IPADDRESS': '10.68.187.152', 'IPADDRESS1': '10.68.187.153', 'OMSIPADDRESS': '10.69.44.254', 'RNC-ID': 'RNC-105', 'RNC-NAME': 'cRNC-105'}),
         mcTestResource('10.106.129.197', {'IPADDRESS': '10.106.129.197', 'MASK': '26', 'IPADDRESS1': '10.106.129.198', 'OMSIPADDRESS': '10.68.145.180', 'RNC-ID': 'RNC-224', 'RNC-NAME': 'mcRNC-224'}),
         mcTestResource('10.69.33.47', {'INTFACE':'lo', 'IPADDRESS': '10.69.33.47', 'MASK': '32', 'IPADDRESS1': '10.69.33.46', 'OMSIPADDRESS': '10.68.145.180', 'RNC-ID': 'RNC-465', 'RNC-NAME': 'mcRNC-465'}),
         mcTestResource('10.56.116.55', {'IPADDRESS': '10.56.116.55', 'IPADDRESS1': '10.56.116.55', 'OMSIPADDRESS': '10.69.44.254', 'RNC-ID': 'RNC-515', 'RNC-NAME': 'mcRNC-515'}),
         mcTestResource('10.69.251.43', {'IPADDRESS': '10.69.251.43', 'IPADDRESS1': '10.69.251.43', 'OMSIPADDRESS': '10.69.44.254', 'RNC-ID': 'RNC-152', 'RNC-NAME': 'mcRNC-152'}),
         mcTestResource('10.69.44.137', {'IPADDRESS': '10.69.44.137', 'IPADDRESS1': '10.69.44.138', 'OMSIPADDRESS': '10.68.145.180', 'RNC-ID': 'RNC-76', 'RNC-NAME': 'mcRNC-76'}),
         mcTestResource('10.56.116.8', {'IPADDRESS': '10.56.116.8', 'IPADDRESS1': '10.56.116.9', 'OMSIPADDRESS': '10.68.145.180', 'RNC-ID': 'RNC-114', 'RNC-NAME': 'mcRNC-114'}),
         mcTestResource('10.68.156.38', {'IPADDRESS': '10.68.156.38', 'IPADDRESS1': '10.68.156.39', 'OMSIPADDRESS': '10.68.145.180', 'RNC-ID': 'RNC-151', 'RNC-NAME': 'mcRNC-151'}),
         mcTestResource('10.68.156.177', {'IPADDRESS': '10.68.156.177', 'IPADDRESS1': '10.68.156.178', 'OMSIPADDRESS': '10.68.145.180', 'RNC-ID': 'RNC-32', 'RNC-NAME': 'RNC-32'}),
         mcTestResource('10.69.44.69', {'IPADDRESS': '10.69.44.69', 'IPADDRESS1': '10.69.44.70', 'OMSIPADDRESS': '10.68.145.180', 'RNC-ID': 'RNC-61', 'RNC-NAME': 'mcRNC-61'}),
         mcTestResource('prinsessa', {'IPADDRESS': '10.16.51.11', 'IPADDRESS1': '10.16.51.12', 'OMSIPADDRESS': '10.68.145.180', 'RNC-ID': 'RNC-1', 'RNC-NAME': 'prinsessa'}),
         mcTestResource('jokeri', {'IPADDRESS': '10.16.52.67', 'IPADDRESS1': '10.16.52.68', 'OMSIPADDRESS': '10.68.145.180', 'RNC-ID': 'RNC-1', 'RNC-NAME': 'jokeri'}),
         mcTestResource('punarinta', {'IPADDRESS': '10.16.52.218', 'IPADDRESS1': '10.16.52.219', 'OMSIPADDRESS': '10.68.145.180', 'RNC-ID': 'RNC-1', 'RNC-NAME': 'punarinta'})
         ]

    for b in benches:
        if b.getName() == bench_name:
            global current_resources
            current_resources = b
            return b.getRes()
    else:
        raise Exception('Cannot find test bench %s config' % bench_name)

def getResources(this_resource=None):
    """
    Returns all or one test suite variable
    """
    res = current_resources.getRes()
    if this_resource is not None:
        if this_resource in res.iterkeys():
            return res[this_resource]
        else:
            return None
    else:
        return res

def ismcRNC():
    return current_resources.ismcRNC()

def getVariables(name):
    """
    Called by Robot when this file is given as "Variables" file in Settings part of the test suite
    Must return a dict where the keys are variable names and values are variable values
    """
    return getAndSetResources(name)

def setVariables(varsRes):
    """
    Updates current variables, so that they will include variables given as command prompt parameters.
    This is done only once at suite setup
    e.g.:
        pybot -v TEST_BENCH:willie -v XML_PATH:/RUNNING/CI xxx.txt
    """
    current_resources.setRes(varsRes)

