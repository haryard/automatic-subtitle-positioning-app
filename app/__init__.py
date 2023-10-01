import os
from flask import Flask
from app import db
from app import main
from app.extension import executor

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'app.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)
        app.config['EXECUTOR_TYPE'] = 'thread'
        app.config['EXECUTOR_MAX_WORKER'] = 8

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    db.init_app(app)
    executor.init_app(app)
    app.register_blueprint(main.bp)
    
    return app