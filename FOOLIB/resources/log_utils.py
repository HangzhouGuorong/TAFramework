try:
    from STE.functional_lib import computer_os_logs
except:
    pass
import TestResources
try:
    from comm.communication import connections as il_connections
except:
    pass
import re
import time
import random

class LogItem:
    def __init__(self, line):
        self._line = line
        self._removed = False

    def remove(self):
        self._removed = True

    def isRemoved(self):
        return self._removed

    def getLogLine(self):
        return self._line

    def __eq__(self, other):
        return self._line == other

    def __str__(self):
        return self._line


class LogMonitoringHandle:
    """
    Log monitoring handle for mcRNC
    """
    def __init__(self, pattern = None, log_file = '/var/log/syslog'):
        self.log = None
        self.tmp_file = '/tmp/foo_test_logs_%d.txt' % random.randint(0,999999)
        cmd = 'tail -n 0 -F %s' % log_file
        if pattern != None:
            cmd += ' | grep --line-buffered "%s" ' % pattern
        cmd += ' > %s &' % self.tmp_file
        out = il_connections.execute_mml(cmd)
        #print out.split('\n')
        self.tail_job = out.split('\n')[1].split()[0]
        self.tail_pid = out.split('\n')[1].split()[1]
        self.running = True
        self.log_items = []

    def stop_monitoring(self):

        il_connections.execute_mml_without_check('kill %%%s' % self.tail_job.strip('[]'))
        while True:
            if il_connections.execute_mml('jobs').find(self.tail_job) < 0:
                break
            time.sleep(1)

        self._get_log_data()
        self.running = False
        il_connections.execute_mml('rm -f %s' % self.tmp_file)
        self.tmp_file = None
        self.tail_pid = None

    def _update_log_data(self, logs):
        for l in logs:
            if len(l) == 0:
                continue
            if l not in self.log_items:
                #print '----- adding new item', l
                self.log_items.append(LogItem(l))

    def _get_log_data(self):
        if self.running:
            # Still running
            logs = il_connections.execute_mml('cat %s' % self.tmp_file).split('\n')
            # Remove all empty lines
            for i, l in enumerate(logs):
                logs[i] = l.strip()
            #print 'Old items', self.log_items
            #print l
            # And extend the log items list with all new items
            self._update_log_data(logs)
            # print 'after extend',self.log_items
        return self.log_items

    def _find_entry(self, pattern):
        logs = self._get_log_data()
        r = re.compile(pattern,re.S)
        for l in logs:
            if l.isRemoved():
                #print '   -> was removed'
                continue
            if (r.search(l.getLogLine()) != None):
                return l
        return None

    def find_log_entry(self, pattern, remove = False):
        l = self._find_entry(pattern)
        if l is not None:
            print 'Found log', str(l)
            if remove:
                l.remove()
            return True
        else:
            return False

    def find_and_remove_log_entry(self, pattern):
        self.find_log_entry(pattern, True)

    def get_logs(self):
        logs = self._get_log_data()
        return '\n'.join(map(str, logs))

    def __del__(self):
        if self.tail_pid != None:
            try:
                il_connections.execute_mml_without_check('kill %s' % self.tail_pid)
            except:
                pass
        if self.tmp_file != None:
            try:
                il_connections.execute_mml('rm -f %s' % self.tmp_file)
            except:
                pass


class DMXLogMonitoringHandle(LogMonitoringHandle):
    def __init__(self, unit='OMU-1'):
        self.unit = unit
        self.running = True
        self.log_items = []
        self._get_log_data()
        # We must ignore old entries
        for l in self.log_items:
            l.remove()

    def _get_log_data(self):
        if self.running:
            logs =  computer_os_logs.get_computer_logs(self.unit)
            # get_computer_logs returns a dict of Dmx_computer_log items
            # but our generic log handling likes just strings
            # so we convert the object to simple string
            items = []
            for v in logs.values():
                items.append('\n'.join(v.log_lines))
            self._update_log_data(items)
        return self.log_items

    def _parse_entry_data(self, log_entry):
        # CALLER : 00BE 0000 00 RETURN ADDRESS: 0940 (G0296).00000B9A
        # WRITE TIME: 2013-12-19 08:00:40.70
        # PARAMETERS: I-08 0938.00000033 00000021 0938.00000004
        # USER TEXT : FOOLIB: too many items (3) at the list VCCBundl
        # USER DATA : eParams foo_obj_conversions.c:403
        log_entry = log_entry.replace('\n', '')
        log_entry = log_entry.replace('\r', '')
        log_entry = log_entry.replace('USER TEXT : ', '')
        log_entry = log_entry.replace('USER DATA : ', '')
        return log_entry

    def _find_entry(self, pattern):
        logs = self._get_log_data()
        # Space pattern is modified because in DMX the
        # log formatting is a bit different and we may
        # have missing spaces after the _parse_entry_data call
        pattern = pattern.replace(' ', '[ ]*')
        r = re.compile(pattern,re.S)
        for l in logs:
            if l.isRemoved():
                continue
            log_writing = self._parse_entry_data(l.getLogLine())
            if (r.search(log_writing) != None):
                return l
        return None

    def stop_monitoring(self):
        self._get_log_data()
        self.running = False

    def __del__(self):
        pass

class log_utils:
    def start_log_monitoring_with_args(self, pattern=None, logfile='/var/log/syslog'):
        """
        Log monitoring with arguments
        """
        # Works only with mcrnc
        if TestResources.ismcRNC():
            il_connections.execute_mml('fsclish -c "set troubleshooting app-log rule rule-id default keep level info"')
            return LogMonitoringHandle(pattern, logfile)
        else:
            # In cRNC we cannot do any pattern based monitoring
            return self.start_log_monitoring()

    def start_log_monitoring(self, unit = None):
        if TestResources.ismcRNC():
            il_connections.execute_mml('fsclish -c "set troubleshooting app-log rule rule-id default keep level info"')
            return LogMonitoringHandle()
        else:
            if unit is None:
                unit = TestResources.getResources('UNIT')
            return DMXLogMonitoringHandle(unit)

    def stop_log_monitoring(self, handle):
        if handle is not None:
            handle.stop_monitoring()

    def check_log_pattern(self, handle, pattern, should_match = True, remove = False):
        """
        Check if given pattern is found from the log
        """
        #print 'the log\n',handle.log

        found = handle.find_log_entry(pattern, remove)

        if (found and should_match) or (not found and not should_match):
            return
        if found and not should_match:
            msg = 'Pattern found unexpectedly'
        else:
            msg = 'Pattern %s was not found from log' % pattern
        raise AssertionError(msg)

    def remove_log_pattern(self, handle, pattern, allVar=False):
        """
        Removes given pattern if found from the log
        """
        while True:
            found = handle.find_and_remove_log_entry(pattern)
            if (found and not allVar) or (not found):
                break

    def get_logs(self, handle=None):
        if handle is not None:
            return handle.get_logs()
        else:
            if TestResources.ismcRNC():
                il_connections.execute_mml('cat /var/log/syslog')
            else:
                computer_os_logs.get_computer_logs(TestResources.getResources('UNIT'))

#class DMXLog:
#    def __init__(self, lines):
#        self.log_lines = lines.split('\n')#
#
#Logs={1:DMXLog('CALLER : 00BE 0000 00 RETURN ADDRESS: 0940 (G0296).00000B9A\nWRITE TIME: 2013-12-19 08:00:40.70\nPARAMETERS: I-08 0938.00000033 00000021 0938.00000004\nUSER TEXT : FOOLIB: too many items (3) at the list VCCBundl\nUSER DATA : eParams foo_obj_conversions.c:403')}
#
#class computer_os_logs:
#    @staticmethod
#    def get_computer_logs(u):
#
#        return Logs
#
#if __name__=="__main__":
#
#    monHandle = DMXLogMonitoringHandle('u')
#    print 'find a'
#    print monHandle.find_entry('a')
#    Logs[2] = DMXLog('CALLER : 00BE 0000 00 RETURN ADDRESS: 0940 (G0296).00000B9A\nWRITE TIME: 2013-12-19 08:00:40.71\nPARAMETERS: I-08 0938.00000033 00000021 0938.00000004\nUSER TEXT : FOOLIB: too many items (3) at the list VCCBundl\nUSER DATA : eParams foo_obj_conversions.c:403')
#    print 'second find'
#    print monHandle.find_entry('VCCBundleParams')
