#!/usr/bin/env python

import os.path
import tempfile
import time


from xmeml import iter as xmemliter

from flask import Flask
from flask_restful import Resource, Api, reqparse, fields, marshal_with
from flask_restful_swagger import swagger
import werkzeug

from celery import Celery, chain, group



APIVERSION = '0.1'

app = Flask(__name__)

###################################
# Set up the Celery task runner

app.config['CELERY_BROKER_URL'] = 'amqp://guest@localhost//'
app.config['CELERY_RESULT_BACKEND'] = 'amqp://guest@localhost//'
app.config['CELERY_TASK_SERIALIZER'] = 'pickle'
app.config['CELERY_RESULT_SERIALIZER'] = 'pickle'
app.config['CELERY_ACCEPT_CONTENT'] = ['pickle', 'json', 'msgpack', 'yaml']

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

class TaskRunner(object):
    'Keep track of all tasks'
    #TODO: keep track of every member of chain: 
    # http://stackoverflow.com/a/23908345
    def __init__(self):
        self.tasks = {}

    def add(self, task):
        'Add a task to the list'
        self.tasks[task.id] = task
        return True

    def get(self, taskId):
        'Find a task by uuid'
        try:
            return self.tasks[taskId]
        except KeyError:
            #no such task found
            return None

@swagger.model
class XmemlAnalysisTask(object):
    'The task of running an xmeml file through audio analysis'

    resource_fields = {
        'filename': fields.String,
        'celeryTaskId': fields.String, # uuid from celery
        'statusUrl': fields.Url(endpoint='status'),
        'status': fields.String,
        #'audiblefiles': fields.List,
    }
    def __init__(self, fileupload):
        app.logger.debug('New Xmeml task with fileupload: %r', fileupload)
        self.fileupload = fileupload # a werkzeug.datastructures.FileStorage object
        self.task = None # being set in .run()
        self.__chain = None
        self.xmemlfile = None # being set in .register()
        self.filename = None # being set in .register()

    @property
    def celeryTaskId(self):
        'Get celery task id'
        if self.__chain is not None:
            return self.__chain.id
        else:
            return None

    @property
    def status(self):
        'Get status'
        if self.task is not None:
            return self.task.state
        else:
            return 'UNKNOWN'

    def register(self):
        'Do some basic checks and, if they pass put this task into the queue'
        if not os.path.splitext(self.fileupload.filename)[1].lower() == '.xml':
            raise InvalidXmeml('Invalid file extension, expexting .xml')
        
        self.filename = self.fileupload.filename
        self.xmemlfile = tempfile.NamedTemporaryFile(suffix='.xml', delete=False)
        self.fileupload.save(self.xmemlfile)
        self.fileupload.close()

        return self.run()

    def audiblefiles(self):
        'Get all the audible files'
        return []

    def run(self):
        'Start analysis task'

        # This is a celery chain
        # parse_xmeml -> analyze_timeline
        #                  |_*_> (group) resolve_metadata
        self.__chain = chain(
            parse_xmeml.s(self.xmemlfile.name),
            analyze_timeline.s()
        )
        app.logger.debug('Set up celery chain: %r', self.__chain)
        self.task = self.__chain.delay()
        return self.task

@celery.task(bind=True)
def parse_xmeml(self, xmemlfile):
    """Background task to parse Xmeml with python-xmeml"""
    app.logger.info('Parsing the xmemlf ile with xmemliter: %r', xmemlfile)
    app.logger.info('exists? %s', os.path.exists(xmemlfile))
    xmeml = xmemliter.XmemlParser(xmemlfile)
    audioclips, audiofiles = xmeml.audibleranges()
    app.logger.info('Analyzing the audible parts: %r, files: %r', audioclips, audiofiles)
    return (audioclips, audiofiles) # Celery.AsyncResult

@celery.task(bind=True)
def analyze_timeline(self, ranges):
    """Background task to analyze the audible parts from the xmeml"""
    app.logger.info('analyzing #ranges: %r', len(ranges))
    audioclips, audiofiles = ranges
    analysis_group = group([resolve_metadata.s(aname, audiofiles[aname], cliprange) for aname, cliprange in audioclips.iteritems() if len(cliprange)>0])
    analysis_group()

@celery.task(bind=True)
def resolve_metadata(self, audioname, fileref, ranges):

    frames = len(ranges)
    app.logger.info("======= %s: %s -> %s======= ", audioname, ranges.r, frames)
    secs = ranges.seconds()
    # find resolver
    # run resolver
    # return metadata
    import random
    time.sleep(random.randint(0, 20)*0.1)
    app.logger.info("pretending to resove audio %r", audioname)
    return audioname

class AnalyzeXmeml(Resource):
    'Resource to handle reception of xmeml and push it into a queue'

    @marshal_with(XmemlAnalysisTask.resource_fields)
    @swagger.operation(
        notes='Do a HTTP POST file upload with a content-type of multipart/form-data',
        responseClass=XmemlAnalysisTask.__name__,
        nickname='upload',
        parameters=[
            {
                "name": "xmeml",
                "description": "The Xmeml sequence file from Premiere or Final Cut Pro.",
                "required": True,
                "allowMultiple": False,
                "dataType": "xmeml",
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
            app.logger.error(e)
            return {'error': str(e)}
        app.tasks.add(task.task)
        app.logger.info('New task created: %r', task.task)
        return task, 201

class AnalysisStatus(Resource):
    'Get a report on how the analysis of that uuid is going'

    @swagger.operation(
        notes='Do a HTTP GET with a UUID for a task, and get the status of it',
        #responseClass=XmemlAnalysisTask.__name__,
        nickname='status',
        parameters=[
            {
                "name": "task",
                "description": "The UUID of the Task",
                "required": True,
                "allowMultiple": False,
                "dataType": 'string',
                "paramType": 'path'
            }
            ]
    )
    def get(self, task):
        'GET a status on how the analysis of a task (passed by a uuid) is going'
        #parse_task = parse_xmeml.AsyncResult(str(task))
        parse_task = app.tasks.get(str(task))
        app.logger.debug('Getting status for parse_task %r: %s', parse_task, dir(parse_task))

        if parse_task.state == 'PENDING':
            # job did not start yet
            response = {
                'state': parse_task.state,
                'current': 0,
                'total': 1,
                'status': 'Pending...'
            }
        elif parse_task.state != 'FAILURE':
            response = {
                'state': parse_task.state,
                'current': parse_task.info.get('current', 0),
                'total': parse_task.info.get('total', 1),
                'status': parse_task.info.get('status', '')
            }
            if 'result' in parse_task.info:
                response['result'] = parse_task.info['result']
        else:
            # something went wrong in the background job
            response = {
                'state': parse_task.state,
                'current': 1,
                'total': 1,
                'status': str(parse_task.info),  # this is the exception raised
            }
        response.update({'uuid': str(task)})
        return response

api.add_resource(AnalyzeXmeml, '/analyze')

api.add_resource(AnalysisStatus, '/status/<uuid:task>', endpoint='status')




if __name__ == '__main__':
    app.tasks = TaskRunner()
    app.run(debug=True)
