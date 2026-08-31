import os
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    db_url = os.environ.get('DATABASE_URL')
    
    if db_url:
        # SQLAlchemy requires 'postgresql://' instead of 'postgres://'
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    else:
        basedir = os.path.abspath(os.path.dirname(__file__))
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'mailpilot.db')
        
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
