import os
import time
import string
import paramiko
import re
from datetime import datetime
from datetime import timedelta

import TestResources

class plan_generate:
    def get_rnc_id(self):
        new_RNCID = TestResources.getResources('RNC-ID')
        return new_RNCID
    
    def get_old_dir(self, base_dir):
        old_dir = os.path.join(base_dir,'..')
        old_dir = os.path.join(old_dir,'test_files')
        return old_dir
    
    def create_new_dir(self, new_dir):
        if os.path.exists(new_dir):
            print 'Directory', new_dir ,'exists'
        else:
            print 'Directory', new_dir ,'does not exist, create it'
            try:
                os.makedirs(new_dir)
            except:
                print "can't create Directory %s" % new_dir
    
    def get_new_dir(self, base_dir):
        if os.name == 'nt':
            new_dir = os.path.join(base_dir,'..')
            new_dir = os.path.join(new_dir,'new_files')
        else:
            new_dir = '/tmp/ci'
        self.create_new_dir(new_dir)
        return new_dir

    def get_new_directory_of_topology(self, base_dir):
        if os.name == 'nt':
            new_dir = os.path.join(base_dir,'..')
            new_dir = os.path.join(new_dir,'new_files')
        else:
            new_dir = '/tmp/topology'
        self.create_new_dir(new_dir)
        return new_dir
    
    def get_modified_time_file_path(self, new_dir):
        if os.name == 'nt':
            file_path = os.path.join(new_dir, 'last_modified_time.txt')
        else:
            file_path = '%s/last_modified_time.txt' % new_dir
        return file_path
    
    def replace_rnc_id_string(self, plan_old, new_rnc_id):
        plan_new = string.replace(plan_old, 'RNC-1', new_rnc_id)
        return plan_new
    
    def replace_adjx_rnc_id_string(self, plan_old, new_adjs_rnc_id):
        plan_new = string.replace(plan_old, '\"AdjsRNCid\">1', '\"AdjsRNCid\">%s ' % new_adjs_rnc_id[4:])
        plan_new = string.replace(plan_new, '\"AdjdRNCid\">1', '\"AdjdRNCid\">%s ' % new_adjs_rnc_id[4:])
        return plan_new
            
    def replace_oms_ip_string(self, plan_old, new_oms_ip):
        pattern = re.compile('''<p name="OMSIpAddress">[0-9]*.[0-9]*.[0-9]*.[0-9]*</p>''')
        #result = pattern.findall(text)
        replace_string = '''<p name="OMSIpAddress">''' + new_oms_ip + "</p>"
        plan_new = re.sub(pattern, replace_string, plan_old)
        
        pattern2 = re.compile('''<p name="SecOMSIpAddress">[0-9]*.[0-9]*.[0-9]*.[0-9]*</p>''')
        replace_string2 = '''<p name="SecOMSIpAddress">''' + new_oms_ip + "</p>"
        plan_new2 = re.sub(pattern2, replace_string2, plan_new)
        print replace_string, replace_string2
        return plan_new2
        
    
    def get_dir_modified_time(self, local_dir):
        dir_modified_time = 0
        plan_file_names = os.listdir(local_dir)
        for plan_file_name in plan_file_names:
            plan_file = os.path.join(local_dir, plan_file_name)
            os.stat_float_times(False)
            file_modified_time = os.stat(plan_file).st_mtime
            os.stat_float_times(True)
            
            if dir_modified_time < file_modified_time:
                dir_modified_time = file_modified_time
        return dir_modified_time
    
    def convert_local_time_to_gm(self, modified_time):
        modified_time_local = time.localtime(modified_time)
        modified_datetime_local = datetime(modified_time_local.tm_year, modified_time_local.tm_mon, modified_time_local.tm_mday, \
                                   modified_time_local.tm_hour, modified_time_local.tm_min, modified_time_local.tm_sec)
        modified_datetime_gm = modified_datetime_local + timedelta(seconds=time.timezone)
        return modified_datetime_gm
    
    def convert_gm_string_to_gm(self, modified_time_str):
        modified_time_gt = time.strptime(modified_time_str, '%Y-%m-%d %H:%M:%S')
        datetime_modified = datetime(modified_time_gt.tm_year, modified_time_gt.tm_mon, modified_time_gt.tm_mday, \
                             modified_time_gt.tm_hour, modified_time_gt.tm_min, modified_time_gt.tm_sec)
        return datetime_modified
    
    def get_dir_modified_time_list(self, local_dir):
        dir_modified_time = 0
        dir_name = os.path.basename(local_dir)
        dir_modified_time_list = dict({dir_name: dir_modified_time})
        plan_file_names = os.listdir(local_dir)
        for plan_file_name in plan_file_names:
            if(not os.path.isdir(os.path.join(local_dir, plan_file_name))):
                plan_file = os.path.join(local_dir, plan_file_name)
                os.stat_float_times(False)
                file_modified_time = os.stat(plan_file).st_mtime
                os.stat_float_times(True)
                dir_modified_time_list.update({plan_file_name: self.convert_local_time_to_gm(file_modified_time)})
            
                if dir_modified_time < file_modified_time:
                    dir_modified_time = file_modified_time
        dir_modified_time_list.update({dir_name : self.convert_local_time_to_gm(dir_modified_time)})
        return dir_modified_time_list
    
    def get_plan_text_from_file(self, file_path):
        if not os.path.exists(file_path):
            print "file %s doesn't exist" % file_path
            return None
        f1 = open(file_path)
        plan_text = f1.read()
        f1.close()
        return plan_text
    
    def write_plan_text_to_file(self, file_path, plan_text):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            f2 = open(file_path, 'w')
            f2.write(plan_text)
            f2.flush()
            f2.close()
        except:
            print "can't open file %s" % file_path
    
    def generate_a_plan_file(self, old_file, new_file):
        if os.path.exists(new_file):
            os.remove(new_file)
        new_rnc_id = TestResources.getResources('RNC-ID')
        new_oms_ip = TestResources.getResources('OMSIPADDRESS')
        
        if(not os.path.isdir(old_file)):
            plan_text_origin = self.get_plan_text_from_file(old_file)
            plan_text_new = self.replace_rnc_id_string(plan_text_origin, new_rnc_id)
            plan_text_new = self.replace_oms_ip_string(plan_text_new, new_oms_ip)
            plan_text_new = self.replace_adjx_rnc_id_string(plan_text_new, new_rnc_id)
            self.write_plan_text_to_file(new_file, plan_text_new)
                
    def generate_plan_files(self, old_dir, new_dir):
        plan_file_names = os.listdir(old_dir)
        
        for plan_file_name in plan_file_names:
            plan_file_origin = os.path.join(old_dir, plan_file_name)
            plan_file_new = os.path.join(new_dir, plan_file_name)
            new_rnc_id = TestResources.getResources('RNC-ID')
            new_oms_ip = TestResources.getResources('OMSIPADDRESS')
            
            if(not os.path.isdir(plan_file_origin)):
                plan_text_origin = self.get_plan_text_from_file(plan_file_origin)
                plan_text_new = self.replace_rnc_id_string(plan_text_origin, new_rnc_id)
                plan_text_new = self.replace_oms_ip_string(plan_text_new, new_oms_ip)
                plan_text_new = self.replace_adjx_rnc_id_string(plan_text_new, new_rnc_id)
                self.write_plan_text_to_file(plan_file_new, plan_text_new)
    
    def save_dir_modified_time_to_file(self, local_file_path, dir_path, modified_time_list):
        modified_time_file = open(local_file_path, 'w+')
        dir_name = os.path.basename(dir_path)
        new_rnc_id = TestResources.getResources('RNC-ID')
        modified_time_string = "RNC-ID %s: File modification time is in Greenwich Mean Time" % new_rnc_id
        #modified_time_string = modified_time_string + "\n%-69s %s" %(dir_name,  modified_time_list.pop(dir_name) - timedelta(seconds=10))
        modified_time_string = modified_time_string + "\n%-69s %s" %(dir_name,  modified_time_list.pop(dir_name))
        modified_time_file.write(modified_time_string)
        modified_time_file.close() 
            
    def save_modified_time_to_file(self, local_file_path, modified_time_list):
        modified_time_file = open(local_file_path, 'a+')
        
        for modified_time_pair in sorted(modified_time_list.iteritems()):
            modified_time_file.write("\n%-69s %s" % modified_time_pair)
        modified_time_file.close()
    
    def load_modified_time_from_file(self, local_file_path):
        modified_time_file = open(local_file_path, 'r')
        print string.strip(modified_time_file.readline())
        text = string.strip(modified_time_file.read())
        modified_time_file.close()
        lines = text.split('\n')
        modified_time_list = {}
        for line in lines:
            #pattern '%Y-%m-%d %H:%M:%S'
            pattern = re.compile('''(.*\s+)([0-9]*-[0-9]*-[0-9]*\ [0-9]*:[0-9]*:[0-9]*)''')
            m = pattern.search(line)
            if (m == None):
                continue
            file_name = string.strip(m.group(1))
            modified_time_str = string.strip(m.group(2))
            modified_time = self.convert_gm_string_to_gm(modified_time_str)
            print file_name, modified_time
            modified_time_list.update({file_name : modified_time})
        return modified_time_list
    
    def update_dir_modified_time(self, modified_time_list, dir_name):
        dir_modified_time = datetime(1, 1, 1, 0, 0, 1)
        for file_name in sorted(modified_time_list.iterkeys()):
            if modified_time_list[file_name] > dir_modified_time:
                dir_modified_time = modified_time_list[file_name]
        modified_time_list.update({dir_name: dir_modified_time})
        
    def check_copy_needed(self, old_dir, new_dir, new_rnc_id):
        local_modified_time_list = self.get_dir_modified_time_list(old_dir)
        modified_time_file_name = self.get_modified_time_file_path(new_dir)
        dir_name = os.path.basename(old_dir)
        print 'modified time file name', modified_time_file_name
        remote_modified_time_list = {dir_name: datetime(1, 1, 1, 0, 0, 1)}
        copy_list = {}
        if os.path.exists(modified_time_file_name):
            try:
                remote_modified_time_list = self.load_modified_time_from_file(modified_time_file_name)
                
            except:
                print "load remote modified time from file failed"
        self.update_dir_modified_time(remote_modified_time_list, dir_name)
        print 'remote modified time', remote_modified_time_list[dir_name]
        print "local modified time", local_modified_time_list[dir_name]
        if remote_modified_time_list[dir_name] < local_modified_time_list[dir_name]:
            self.generate_plan_files(old_dir, new_dir)
            self.save_dir_modified_time_to_file(modified_time_file_name, old_dir, local_modified_time_list)
            self.save_modified_time_to_file(modified_time_file_name, local_modified_time_list)
            print 'plan files copy needed'
            for modified_time_key in sorted(local_modified_time_list.iterkeys()):
                if (modified_time_key not in remote_modified_time_list) \
                   or (remote_modified_time_list[modified_time_key] < local_modified_time_list[modified_time_key]):
                    copy_list.update({modified_time_key: local_modified_time_list[modified_time_key]})
            print "Need copy files number: ", len(copy_list)
            return copy_list
        else:
            print 'plan files copy not needed'
            return copy_list
        
def main():
    TestResources.getAndSetResources('10.56.116.8')
    base_dir = os.path.dirname(os.path.abspath(__file__))
    plan_generator = plan_generate()
    old_dir = plan_generator.get_old_dir(base_dir)
    new_dir = plan_generator.get_new_dir(base_dir)
    remote_dir = TestResources.getResources('XML_PATH')
    rnc_id = TestResources.getResources('RNC-ID')

    local_modified_time_file_path = plan_generator.get_modified_time_file_path(new_dir)
    
    if TestResources.ismcRNC():
        remote_modified_time_file_path = '%s/last_modified_time.txt' %remote_dir
        server = TestResources.getResources('IPADDRESS')
        username = TestResources.getResources('USERNAME')
        password = TestResources.getResources('PASSWORD')
        #os.system("scp -r %s %s@%s:%s" % (local_name, user_name, server, remote_name))
       
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
        ssh.connect(server, username=username, password=password)
        sftp = ssh.open_sftp()
        
        sftp.get(remote_modified_time_file_path, local_modified_time_file_path)
      
        plan_generator.check_copy_needed(old_dir, new_dir, rnc_id)


"""                    
        generate_plan_files(old_dir, new_dir)
   
        if(os.path.isdir(new_dir)):
            for item in os.listdir(new_dir):
                if(not os.path.isdir(os.path.join(new_dir, item))):
                    sftp.put(os.path.join(new_dir, item), "%s/%s" % (remote_dir, item))
        else:
            sftp.put(new_dir, remote_dir)
        
        print "copy done."


    new_oms_ip = "10.100.100.100"
    text = '''<p name="N302">7</p><p name="N304">2</p><p name="OMSIpAddress">10.236.190.120</p><p name="PageRep1stInterv">11</p>'''
    print text
    pattern = re.compile('''<p name="OMSIpAddress">[0-9]*.[0-9]*.[0-9]*.[0-9]*</p>''')
    result = pattern.findall(text)
    print result
    replace_string = '''<p name="OMSIpAddress">''' + new_oms_ip + "</p>"
    text = re.sub(pattern, replace_string, text)
    print text
    match_result = pattern.match(text,40)
    cmdata_start = match_result.start()
    cmdata_end = match_result.end()
    
    if (cmdata_start==-1) or (cmdata_end==-1):
        raise AssertionError('Invalid parameter: cmData section not found')
    old_oms_ip = text[cmdata_start:cmdata_end-4]
    print old_oms_ip
    
    print new_oms_ip
    text = string.replace(text, old_oms_ip, new_oms_ip)
    print text   
"""

  
if __name__ == "__main__":
    main()