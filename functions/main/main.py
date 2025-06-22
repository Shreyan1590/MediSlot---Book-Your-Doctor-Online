from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.wrappers import Response
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app

def handler(event, context):
    with flask_app.app_context():
        return Response(
            flask_app.full_dispatch_request(),
            status=flask_app.response.status_code,
            headers=dict(flask_app.response.headers)
        )

app = DispatcherMiddleware(flask_app)