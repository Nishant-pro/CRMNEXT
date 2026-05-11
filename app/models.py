from app import db

class Server(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    host = db.Column(db.String(100), nullable=False)
    port = db.Column(db.Integer, default=22)
    username = db.Column(db.String(100), default='oracle')
    password = db.Column(db.String(200))          # encrypted in real code!
    key_filename = db.Column(db.String(500))      # path to private key
    oracle_home = db.Column(db.String(500))
    oracle_sid = db.Column(db.String(50))

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_type = db.Column(db.String(50))   # DP_EXPORT, DP_IMPORT, CLASSIC_EXPORT, CLASSIC_IMPORT
    status = db.Column(db.String(20), default='PENDING')
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'))
    parameters = db.Column(db.Text)        # JSON
    log = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
