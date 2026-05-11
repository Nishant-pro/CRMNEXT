from tasks import celery
from app.utils.ssh_manager import SSHManager
from app.models import Server, Job
from app import db
import time

@celery.task(bind=True)
def run_datapump_export(self, server_id, schema, directory, dumpfile, parallel=1):
    server = Server.query.get(server_id)
    log_lines = []
    try:
        ssh = SSHManager(server.host, server.port, server.username,
                         password=server.password, key_filename=server.key_filename)
        cmd = (f"expdp {schema}/***** DIRECTORY={directory} DUMPFILE={dumpfile} "
               f"PARALLEL={parallel}")
        out, err = ssh.execute_oracle(cmd, server.oracle_home, server.oracle_sid)
        log_lines.append(out)
        if err:
            log_lines.append(f"STDERR: {err}")
        ssh.close()
        status = 'SUCCESS' if 'successfully completed' in out.lower() else 'FAILURE'
    except Exception as e:
        log_lines.append(str(e))
        status = 'ERROR'

    # Update job log in DB
    job = Job.query.filter_by(celery_id=self.request.id).first()
    if job:
        job.log = "\n".join(log_lines)
        job.status = status
        db.session.commit()
    return {'status': status, 'log': "\n".join(log_lines)}

@celery.task(bind=True)
def run_datapump_import(self, server_id, schema, directory, dumpfile,
                        remap_schema=None, remap_tablespace=None, parallel=1):
    server = Server.query.get(server_id)
    log_lines = []
    try:
        ssh = SSHManager(server.host, server.port, server.username,
                         password=server.password, key_filename=server.key_filename)
        cmd = f"impdp {schema}/***** DIRECTORY={directory} DUMPFILE={dumpfile} PARALLEL={parallel}"
        if remap_schema:
            cmd += f" REMAP_SCHEMA={remap_schema}"
        if remap_tablespace:
            cmd += f" REMAP_TABLESPACE={remap_tablespace}"
        out, err = ssh.execute_oracle(cmd, server.oracle_home, server.oracle_sid)
        log_lines.append(out)
        if err:
            log_lines.append(f"STDERR: {err}")
        ssh.close()
        status = 'SUCCESS' if 'successfully completed' in out.lower() else 'FAILURE'
    except Exception as e:
        log_lines.append(str(e))
        status = 'ERROR'

    job = Job.query.filter_by(celery_id=self.request.id).first()
    if job:
        job.log = "\n".join(log_lines)
        job.status = status
        db.session.commit()
    return {'status': status, 'log': "\n".join(log_lines)}
