class parameter_utils:

    """
    Keywords for parameters
    """

    class Foo_param:
        def __init__(self):
            self.name = ""
            self.parent_o_name = ""
            self.parent_p_name = ""
            self.pddb_type = ""
            self.max_occurs = ""
            self.attributes = ""
            self.interfaces = ""
            self.param_bit = ""
            self.pddb_base_type = ""
            self.min_value = ""
            self.max_value = ""
            self.step = ""
            self.default_value = ""
            self.special_value = ""
            self.struct_id = ""
            self.size = ""
            self.offset = ""
            self.count_offset = ""
            self.count_type = ""
            self.rel_features = ""

        def __str__(self):
            s = self.name
            return s

    def get_param_info(self, param_info_data):
        """
        Returns instance of Foo_param

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

        param = self.Foo_param()
        for line in param_info_data.split('\n'):
            if ( line.find("Name:") != -1 ):
                param.name = line.split(':')[1].lstrip().rstrip()
            if ( line.find("Parent o name:") != -1 ):
                param.parent_o_name = line.split(':')[1].lstrip().rstrip()
            if ( line.find("Parent p name:") != -1 ):
                param.parent_p_name = line.split(':')[1].lstrip().rstrip()
            if ( line.find("Attributes:") != -1 ):
                param.attributes = line.split(':')[1].lstrip().rstrip()
            if ( line.find("Interfaces:") != -1 ):
                param.interfaces = line.split(':')[1].lstrip().rstrip()
            if ( line.find("Max occurs:") != -1 ):
                param.max_occurs = line.split(':')[1].lstrip().rstrip()
            if ( line.find("Count type:") != -1 ):
                param.count_type = line.split(':')[1].lstrip().rstrip()
            if ( line.find("PDDB type:") != -1 ):
                param.pddb_type = line.split(':')[1].lstrip().rstrip()
            if ( line.find("Default value:") != -1 ):
                param.default_value = line.split(':')[1].lstrip().rstrip()
            if ( line.find('Param rel features:') != -1 and 'N/A' not in line):
                param.rel_features = line.split(':')[1].strip()
            # XXX
        print ( "param = " + str(param))
        return param

    def is_param_upload_only(self, foo_param):
        """
        Returns True if the given foo_param does not have download attribute
        Otherwise returns False
        """
        if "racDownload" in foo_param.interfaces or "emDownload" in foo_param.interfaces:
            return False
        else:
            return True

    def is_param_download_only(self, foo_param):
        """
        Returns True if the given foo_param does not have uplaod attribute
        Otherwise returns False
        """
        if "racUpload" in foo_param.interfaces or "emUpload" in foo_param.interfaces:
            return False
        else:
            return True

    def is_param_oms_only(self, foo_param):
        """
        Returns True if the given foo_param is only for OMS
        Otherwise returns False
        """
        if "racDownload" in foo_param.interfaces or "racUpload" in foo_param.interfaces:
            return False
        else:
            return True
    
    def is_param_unmodif(self, foo_param):
        """
        Returns True if the given foo_param has attribute unModifiable
        Otherwise returns False
        """
        if foo_param.attributes.find("unModifiable") != -1:
            return True
        else:
            return False
            
    def is_param_list_without_count_field(self, foo_param):
        """
        Returns True if the max_occurs > 1 and the parameter does not have any count field
        """
        if (int(foo_param.max_occurs) > 1) and (foo_param.count_type == "0"):
            return True
        else:
            return False

    def get_param_default_value(self, foo_param):
        """
        Returns the default value
        """
        return foo_param.default_value

    def check_feature_conditions(self, foo_param, features):
        import re
        opt_str = foo_param.rel_features

        if opt_str == '' or features == '' or features is None:
            return True
        
        if not hasattr(features,'__iter__'):
            features = [features]

        opt_str = opt_str.replace('|', ' or ')
        opt_str = opt_str.replace('*', ' and ')
        opt_str = opt_str.replace('(', ' ( ')
        opt_str = opt_str.replace(')', ' ) ')
        opt_list = re.split(' ', opt_str)
        for i, o in enumerate(opt_list):
            if o in features:
                opt_list[i] = 'False' 
            elif o.isdigit():
                opt_list[i] = 'True'
        opt_str = ' '.join(opt_list)
        print 'modified opt string',opt_str
        return eval(opt_str)

