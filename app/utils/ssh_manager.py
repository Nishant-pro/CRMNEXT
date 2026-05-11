import paramiko
from io import StringIO

class SSHManager:
    def __init__(self, host, port=22, username='oracle', password=None, key_filename=None):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(host, port, username, password=password, key_filename=key_filename)

    def execute(self, command):
        stdin, stdout, stderr = self.client.exec_command(command)
        return stdout.read().decode(), stderr.read().decode()

    def execute_oracle(self, command, oracle_home=None, oracle_sid=None):
        """Source Oracle environment then run command."""
        env = ''
        if oracle_home and oracle_sid:
            env = f'export ORACLE_HOME={oracle_home}; export ORACLE_SID={oracle_sid}; export PATH=$ORACLE_HOME/bin:$PATH; '
        full_cmd = f'{env}{command}'
        return self.execute(full_cmd)

    def close(self):
        self.client.close()
