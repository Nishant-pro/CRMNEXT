from tasks import celery
from app.utils.ssh_manager import SSHManager
from app.models import Server, Job
from app import db

@celery.task(bind=True)
def run_classic_export(self, server_id, schema, file):
    server = Server.query.get(server_id)
    log_lines = []
    try:
        ssh = SSHManager(server.host, server.port, server.username,
                         password=server.password, key_filename=server.key_filename)
        cmd = f"exp {schema}/***** FILE={file}"
        out, err = ssh.execute_oracle(cmd, server.oracle_home, server.oracle_sid)
        log_lines.append(out)
        if err:
            log_lines.append(f"STDERR: {err}")
        ssh.close()
        status = 'SUCCESS' if 'Export terminated successfully' in out else 'FAILURE'
    except Exception as e:
        log_lines.append(str(e))
        status = 'ERROR'

    job = Job.query.filter_by(celery_id=self.request.id).first()
    if job:
        job.log = "\n".join(log_lines)
        job.status = status
        db.session.commit()
    return {'status': status, 'log': "\n".join(log_lines)}

@celery.task(bind=True)
def run_classic_import(self, server_id, schema, file, fromuser=None, touser=None):
    server = Server.query.get(server_id)
    log_lines = []
    try:
        ssh = SSHManager(server.host, server.port, server.username,
                         password=server.password, key_filename=server.key_filename)
        cmd = f"imp {schema}/***** FILE={file}"
        if fromuser and touser:
            cmd += f" FROMUSER={fromuser} TOUSER={touser}"
        out, err = ssh.execute_oracle(cmd, server.oracle_home, server.oracle_sid)
        log_lines.append(out)
        if err:
            log_lines.append(f"STDERR: {err}")
        ssh.close()
        status = 'SUCCESS' if 'Import terminated successfully' in out else 'FAILURE'
    except Exception as e:
        log_lines.append(str(e))
        status = 'ERROR'

    job = Job.query.filter_by(celery_id=self.request.id).first()
    if job:
        job.log = "\n".join(log_lines)
        job.status = status
        db.session.commit()
    return {'status': status, 'log': "\n".join(log_lines)}
