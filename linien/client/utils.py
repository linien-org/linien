import os
import paramiko

from linien.config import REMOTE_BASE_PATH


def run_server(host, user, password):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, username=user, password=password)
    ftp = ssh.open_sftp()

    directory = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..'
        )
    )

    # upload the code required for running the server
    for dirpath, dirnames, filenames in os.walk(directory):
        dirpath_rel = dirpath.replace(directory, '').lstrip('/')
        remote_path = os.path.join(REMOTE_BASE_PATH, dirpath_rel)

        if '.' in dirpath_rel or '__' in dirpath_rel:
            continue

        try:
            ftp.lstat(remote_path)
        except IOError:
            ftp.mkdir(os.path.join(remote_path.rstrip('/')))

        for filename in filenames:
            local_path = os.path.join(dirpath, filename)
            remote_filepath = os.path.join(remote_path, filename)
            # put file
            ftp.put(local_path, remote_filepath)

    ftp.close()

    # start the server process
    ssh.exec_command('bash %s/server/start_server_in_screen.sh' % REMOTE_BASE_PATH)
    ssh.close()
