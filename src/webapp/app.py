#!/usr/bin/env python

import os.path

from xmeml import iter as xmemliter

from flask import Flask
from flask_restful import Resource, Api, reqparse, fields, marshal_with
from flask_restful_swagger import swagger
import werkzeug

from celery import Celery



APIVERSION = '0.1'

app = Flask(__name__)

###################################
# Set up the Celery task runner

app.config['CELERY_BROKER_URL'] = 'amqp://guest@localhost//'
app.config['CELERY_RESULT_BACKEND'] = 'amqp://guest@localhost//'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)
###################################

# Wrap the Api with swagger.docs. It is a thin wrapper around the Api class
# that adds some swagger smarts

api = swagger.docs(Api(app), 
                   description='A simple, JSON based Restful API to Odometer+Origo',
                   apiVersion=APIVERSION)
###################################

class InvalidXmeml(Exception):
    pass

@swagger.model
class XmemlAnalysisTask(object):
    'The task of running an xmeml file through audio analysis'

    resource_fields = {
        'xmemlfile': fields.String(attribute='xmemlfile.filename'),
        'celery_id': fields.String, # uuid from celery
        'status_url': fields.Url,
        'status': fields.String,
        #'audiblefiles': fields.List,
    }
    def __init__(self, xmemlfile):
        app.logger.debug('New Xmeml task with xmemlfile: %r', xmemlfile)
        self.xmemlfile = xmemlfile # a werkzeug.datastructures.FileStorage object
        self.task = None # being set in .run()

    @property
    def celery_id(self):
        'Get celery queue id'
        if self.task is not None:
            return self.task.id
        else:
            return -1

    @property
    def status(self):
        'Get status'
        if self.task is not None:
            return self.task.state
        else:
            return 'UNKNOWN'

    def register(self):
        'Do some basic checks and, if they pass put this task into the queue'
        if not os.path.splitext(self.xmemlfile.filename)[1].lower() == '.xml':
            raise InvalidXmeml('Invalid file extension, expexting .xml')
        
        return self.run()

    def audiblefiles(self):
        'Get all the audible files'
        return []

    def run(self):
        'Start analysis task'
        self.task = analyze_async_xmeml.delay()
        return self.task

@celery.task(bind=True)
def analyze_async_xmeml(xmemlfile):
    """Background task to analyze Xmeml with python-xmeml"""
    xmeml = xmemliter.XmemlParser(xmemlfile)
    return xmeml # Celery.AsyncResult


class AnalyzeXmeml(Resource):
    'Resource to handle reception of xmeml and push it into a queue'

    @marshal_with(XmemlAnalysisTask.resource_fields)
    @swagger.operation(
        notes='This is how we do it',
        responseClass=XmemlAnalysisTask.__name__,
        nickname='upload',
        parameters=[
            {
                "name": "xmeml",
                "description": "The Xmeml sequence file from Premiere or Final Cut Pro.",
                "required": True,
                "allowMultiple": False,
                "dataType": 'xmeml',
                "paramType": "body"
            }
            ],
        responseMessages=[
            {
                "code": 201,
                "message": "Created. The URL of the created blueprint should be in the Location header"
            },
            {
                "code": 405,
                "message": "Invalid input"
            }
            ]
    )
    def post(self):
        'POST an xmeml sequence to start the music report analysis. Returns a unique identifier'

        parser = reqparse.RequestParser()
        parser.add_argument('xmeml',
                            required=True,
                            type=werkzeug.datastructures.FileStorage,
                            help='The Xmeml sequence from Premiere or Final Cut that we want to analyze.',
                            location='files')
        app.logger.debug('About to parse POST args')
        args = parser.parse_args(strict=True)
        task = XmemlAnalysisTask(args['xmeml'])
        try:
            task.register()
        except InvalidXmeml as e:
            return {'error': str(e)}

        app.logger.info('New task created: %r', task)
        return task, 201

class AnalysisStatus(Resource):
    'Get a report on how the analysis of that uuid is going'

    def get(self, task):
        'GET a status on how the analysis of a task (a uuid) is going'
        return {'status': 'running',
                'task': str(task)}

api.add_resource(AnalyzeXmeml, '/analyze')

api.add_resource(AnalysisStatus, '/status/<uuid:task>')




if __name__ == '__main__':
    app.run(debug=True)
