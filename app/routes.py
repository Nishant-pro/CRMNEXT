from flask import Blueprint, render_template, request, jsonify
from app.models import Server, Job
from app import db
import json

main = Blueprint('main', __name__)

@main.route('/')
def index():
    servers = Server.query.all()
    return render_template('index.html', servers=servers)

@main.route('/api/export/datapump', methods=['POST'])
def dp_export():
    data = request.json
    from tasks.datapump import run_datapump_export
    task = run_datapump_export.delay(
        server_id=data['server_id'],
        schema=data['schema'],
        directory=data['directory'],
        dumpfile=data['dumpfile'],
        parallel=data.get('parallel', 1)
    )
    job = Job(job_type='DP_EXPORT', status='SUBMITTED', server_id=data['server_id'],
              parameters=json.dumps(data), celery_id=task.id)
    db.session.add(job)
    db.session.commit()
    return jsonify({'job_id': task.id, 'db_job_id': job.id}), 202

@main.route('/api/import/datapump', methods=['POST'])
def dp_import():
    data = request.json
    from tasks.datapump import run_datapump_import
    task = run_datapump_import.delay(
        server_id=data['server_id'],
        schema=data['schema'],
        directory=data['directory'],
        dumpfile=data['dumpfile'],
        remap_schema=data.get('remap_schema'),
        remap_tablespace=data.get('remap_tablespace'),
        parallel=data.get('parallel', 1)
    )
    job = Job(job_type='DP_IMPORT', status='SUBMITTED', server_id=data['server_id'],
              parameters=json.dumps(data), celery_id=task.id)
    db.session.add(job)
    db.session.commit()
    return jsonify({'job_id': task.id, 'db_job_id': job.id}), 202

@main.route('/api/export/classic', methods=['POST'])
def classic_export():
    data = request.json
    from tasks.classic import run_classic_export
    task = run_classic_export.delay(
        server_id=data['server_id'],
        schema=data['schema'],
        file=data['file']
    )
    job = Job(job_type='CLASSIC_EXPORT', status='SUBMITTED', server_id=data['server_id'],
              parameters=json.dumps(data), celery_id=task.id)
    db.session.add(job)
    db.session.commit()
    return jsonify({'job_id': task.id, 'db_job_id': job.id}), 202

@main.route('/api/import/classic', methods=['POST'])
def classic_import():
    data = request.json
    from tasks.classic import run_classic_import
    task = run_classic_import.delay(
        server_id=data['server_id'],
        schema=data['schema'],
        file=data['file'],
        fromuser=data.get('fromuser'),
        touser=data.get('touser')
    )
    job = Job(job_type='CLASSIC_IMPORT', status='SUBMITTED', server_id=data['server_id'],
              parameters=json.dumps(data), celery_id=task.id)
    db.session.add(job)
    db.session.commit()
    return jsonify({'job_id': task.id, 'db_job_id': job.id}), 202

@main.route('/api/tablespace', methods=['POST'])
def tablespace_info():
    data = request.json
    server = Server.query.get(data['server_id'])
    from app.utils.oracle_helper import get_tablespace_info
    rows = get_tablespace_info(
        dsn=f"{server.host}:1521/{server.oracle_sid}",
        user=server.username,
        password=server.password
    )
    return jsonify(rows)

@main.route('/api/job/<job_id>/log')
def job_log(job_id):
    job = Job.query.get(job_id)
    if job:
        return jsonify({'log': job.log or 'No log yet'})
    return jsonify({'error': 'Job not found'}), 404

@main.route('/api/job/history')
def job_history():
    jobs = Job.query.order_by(Job.created_at.desc()).limit(20).all()
    result = []
    for j in jobs:
        result.append({
            'id': j.id,
            'type': j.job_type,
            'status': j.status,
            'created_at': j.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    return jsonify(result)
