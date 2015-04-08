try:
    from comm.communication import connections as il_connections
except:
    pass

WORK_DIR = '/tmp'
PROFILE_SESSION_DIR = WORK_DIR+'/oprofilesession'
PAB_BIN = '/opt/nsn/pac_pab_q2_e1/bin/pabros.bin'
RAY_BIN = '/opt/nsn/pac_ray_q2_e1/bin/rayman.bin'
FOO_BIN = '/opt/nokiasiemens/lib64/libfoolib.so'

class profiling_utils:

    """
    Keywords for profiling
    """

    def init_profiling_mc(self):
        il_connections.execute_mml('opcontrol --init')
        il_connections.execute_mml('opcontrol --reset')
        il_connections.execute_mml('opcontrol --no-vmlinux')
        il_connections.execute_mml('opcontrol --session-dir=%s' % PROFILE_SESSION_DIR)

    def start_profiling_mc(self):
        il_connections.execute_mml('opcontrol --start --session-dir=%s' % PROFILE_SESSION_DIR)

    def stop_profiling_mc(self):
        il_connections.execute_mml('opcontrol --dump')

    def get_profiling_result_mc(self):
        il_connections.execute_mml('cd %s;opreport -l --sort=image --session-dir=%s %s || true' % (WORK_DIR,PROFILE_SESSION_DIR,PAB_BIN))
        il_connections.execute_mml('cd %s;opreport -l --sort=image --session-dir=%s %s || true' % (WORK_DIR,PROFILE_SESSION_DIR,RAY_BIN))
        il_connections.execute_mml('cd %s;opreport -l --sort=image --session-dir=%s %s || true' % (WORK_DIR,PROFILE_SESSION_DIR,FOO_BIN))
        il_connections.execute_mml('cd %s;opgprof --session-dir=%s %s || true' % (WORK_DIR,PROFILE_SESSION_DIR,PAB_BIN))
        il_connections.execute_mml('cd %s;opgprof --session-dir=%s %s || true' % (WORK_DIR,PROFILE_SESSION_DIR,RAY_BIN))
        il_connections.execute_mml('cd %s;opgprof --session-dir=%s %s || true' % (WORK_DIR,PROFILE_SESSION_DIR,FOO_BIN))
        out =  il_connections.execute_mml('gprof -p %s || true' % PAB_BIN)
        out = out + il_connections.execute_mml('gprof -p %s || true' % RAY_BIN)
        out = out + il_connections.execute_mml('gprof -p %s || true' % FOO_BIN)

        il_connections.execute_mml('opcontrol --stop')
        il_connections.execute_mml('opcontrol --shutdown')

        return out
