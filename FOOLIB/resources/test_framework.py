
from comm.communication import connections as il_connections
import atexit
import TestResources
import paramiko
import time
import os

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
    import IpaMml.misc_lib
    import FunctionLib
except:
    pass

class test_framework():

    def restart_ipa_unit(self, unit="", max_wait=120):
        if unit == "":
            unit = TestResources.getResources('UNIT')
        IpaMml.units_lib.restart_unit(unit, "DSK")
        units = IpaMml.units_lib.get_units(unit)

        wait_time = 0
        while(units.state.find("-EX") == -1):
            time.sleep(5)
            units = IpaMml.units_lib.get_units(unit)
            wait_time = wait_time + 5
            if(wait_time > max_wait):
                raise AssertionError('unit %s in state %s' % (unit, units.state))

    def ipa_unit_change_state(self, unit="OMU-0", state='WO-EX', max_wait=120):
        if unit == "":
            unit = TestResources.getResources('UNIT')
        IpaMml.units_lib.get_units(unit)
        try:
            IpaMml.units_lib.change_unit_state(unit, 'WO-EX', mode="FCD", expect_loss_mml=True, boot_timeout=max_wait);
        except:
            pass
        self._wait_until_connection_is_back()

    def wait_unit_up(self, unit="", max_wait=480):
        if unit == "":
            unit = TestResources.getResources('UNIT')

        if TestResources.ismcRNC():
            cmd = "fshascli -s /%s" % unit
            output = il_connections.execute_mml(cmd)
            wait_time = 0
            while("role(ACTIVE)" not in output):
                time.sleep(5)
                output = il_connections.execute_mml(cmd)
                wait_time = wait_time + 5
                if(wait_time > max_wait):
                    raise AssertionError('unit %s did not get up in time (%d seconds)' % max_wait)
        else:
            units = IpaMml.units_lib.get_units(unit, mode="")
            wait_time = 0
            print units
            while(units.state.find("-EX") == -1):
                time.sleep(5)
                units = IpaMml.units_lib.get_units(unit, mode="")
                wait_time = wait_time + 5
                if(wait_time > max_wait):
                    raise AssertionError('unit %s in state %s' % (unit, units.state))

    def wait_spare_unit_up(self, unit="", max_wait=480):
        if unit == "":
            unit = TestResources.getResources('UNIT')

        if TestResources.ismcRNC():
            raise AssertionError('not implemented')
        else:
            units = IpaMml.units_lib.get_units(unit, mode="")
            wait_time = 0
            print units
            while(units.state.find("SP-EX") == -1):
                time.sleep(5)
                units = IpaMml.units_lib.get_units(unit, mode="")
                wait_time = wait_time + 5
                if(wait_time > max_wait):
                    raise AssertionError('unit %s in state %s' % (unit, units.state))

    def change_package(self, sw_package="LOTTOKON"):
        IpaMml.connections.execute_mml_without_check("ZWSC:STAT=NW:STAT=BU;")
        IpaMml.connections.execute_mml_without_check("ZWSC:NAME=%s:STAT=NW:;" % sw_package)
        IpaMml.connections.execute_mml_without_check("ZWSD:NAME=%s:;" % sw_package, "Y")
        time.sleep(120)

    def connect_to_ipa(self, ipaddress='10.16.28.89', username = 'SYSTEM', passwd = 'SYSTEM'):
        IpaMml.connections.connect_to_ipa(host=ipaddress, user=username, passwd=passwd)
        IpaMml.connections._get_current_connection()

    def disconnect_from_ipa(self):
        IpaMml.connections.disconnect_from_ipa()

    def connect_to_mc(self, ipaddress='10.16.51.11', username='root', passwd='password'):

        self._connection = il_connections.connect_to_il(ipaddress, user = username, passwd = passwd)
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

    def setResouceVariables(self, varsResource):
        TestResources.setVariables(varsResource)

    def test_connect(self):
        """
        Connect to metadata test bench.
        After connection the user can execute command line commands using
        connections.execute_mml function.
        """
        atexit.register(self.test_disconnect)
        self._connected = True
        print '*INFO* Connnected to metadata testbench'
        res = TestResources.getResources()
        if TestResources.ismcRNC():
            self.connect_to_mc(res['IPADDRESS'], res['USERNAME'], res['PASSWORD'])
        else:
            self.connect_to_ipa(res['IPADDRESS'], res['USERNAME'], res['PASSWORD'])

    def test_suite_setup(self):
        """
        Test bench specific setups and other stuff
        """
        if TestResources.ismcRNC():
            self.run_cmd('export LD_LIBRARY_PATH=%s' % TestResources.getResources('LIBRARY_PATH') )
            # By default only error (and higher) level IL logs are forwarded to syslog
            #self.run_cmd('fsclish -c "set troubleshooting app-log rule rule-id default keep level notice unit OMU-0"')
        else:
            pass

    def test_suite_teardown(self):
        pass

    def set_connection_timeout(self, val):
        il_connections.set_mml_timeout(val)

    def disconnect_mc(self):
        if hasattr(self, '_connection'):
            il_connections.disconnect_from_il()
            del self._connection
            print '*INFO* disconnected from metadata testbench'
        global org_execute_mml
        if org_execute_mml != None:
            il_connections.execute_mml = org_execute_mml
            org_execute_mml = None

    def test_disconnect(self):
        """
        Disconnect from metadata test bench.
        """
        print 'Disconnecting'
        if TestResources.ismcRNC():
            self.disconnect_mc()
        else:
            self.disconnect_from_ipa()

    def system_restart(self):
        if TestResources.ismcRNC():
            raise AssertionError('No support for system restart for mcRNC yet');
        else:
            IpaMml.misc_lib.restart_system("TOT","FCD")

    def wait_until_icsu2_up(self):
            #IpaMml.units_lib._wait_until_units_list_are_in_states(['ICSU-2'], ['WO-EX'], '10s')
            FunctionLib.units_lib._wait_until_units_list_are_in_states(['ICSU-2'], ['WO-EX'], '10s')

    def ftp_get_a_file(self, remote_name, local_name):
        ftp_url = "ftp://" + TestResources.getResources('IPADDRESS') + remote_name
        username = TestResources.getResources('USERNAME')
        password = TestResources.getResources('PASSWORD')
        Utils.ftp_lib.download_from_ftp_to_local(ftp_url, local_name, 'bin', username, password)

    def ftp_put_a_file(self, local_name, remote_name):
        ftp_url = "ftp://" + TestResources.getResources('IPADDRESS') + remote_name
        username = TestResources.getResources('USERNAME')
        password = TestResources.getResources('PASSWORD')
        print "url='%s' local_name='%s'" % (ftp_url, local_name)
        Utils.ftp_lib.upload_to_ftp_from_local(ftp_url, local_name, 'bin', username, password)

    def sftp_put_a_file(self, local_name, remote_name):
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
                sftp.put(os.path.join(local_name, item), "%s/%s" % (remote_name, item))
        else:
            sftp.put(local_name, remote_name)

        sftp.close()
        ssh.close()

    def upload_a_file(self, local_name, remote_path="", remote_name=""):
        """
        Upload a file or directory from local host to test bench
        Recursive upload of directories not supported
        """
        if(remote_path == ""):
            remote_path = TestResources.getResources('XML_PATH')

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
        Generic Delete a file KW for removing a file from the disk.
        """
        if TestResources.ismcRNC():
            return self.run_cmd('rm -rf ' + fname)
        else:
            ipa_cmd = 'ZPS:unlink,%s' % fname
            output = self.execute_service_terminal_commands(['ZL:P', 'ZLP:P,POM', ipa_cmd])
            self.execute_service_terminal_commands(['ZL:P'])
            return output

    def ipa_copy_file(self, src, dst):
        STE.open_service_terminal('OMU')
        try:
            IpaMml.connections.execute_mml_without_check('ZLP:P,POM')
            output = IpaMml.connections.execute_mml_without_check('ZPS:cp,%s,%s' % (src,dst))
        finally:
            STE.close_service_terminal()

        if(output.find("COPIED") == -1):
            raise AssertionError('cp %s %s failed!' % (src,dst))

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
                output = output + IpaMml.connections.execute_mml_without_check('%s;' % c, answers)
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

    def unlink_crnc_extensions(self):
        unit = TestResources.getResources('UNIT')
        unit = unit.replace('-',',')
        STE.open_service_terminal(unit)

        try:
            output = IpaMml.connections.execute_mml_without_check("ZL?")
            for line in output.split('\n'):
                if(line.find(".....") != -1):
                    cmd_letter = line[0]
                    if(cmd_letter != "G"):
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

    def ismcRNC(self):
        return TestResources.ismcRNC()

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


def main():
    TestResources.getAndSetResources('jokeri')


if __name__=="__main__":
    main()
