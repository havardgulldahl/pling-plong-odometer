#!/usr/bin/env python


import uuid




from flask import Flask
from flask_restful import Resource, Api
from flask_restful_swagger import swagger




APIVERSION = '0.1'

app = Flask(__name__)
###################################

# Wrap the Api with swagger.docs. It is a thin wrapper around the Api class
# that adds some swagger smarts

api = swagger.docs(Api(app), apiVersion=APIVERSION)
###################################


class HelloWorld(Resource):
    def get(self):
        return {'hello': 'world'}

class AnalyzeXmeml(Resource):
    'Resource to handle reception of xmeml and push it into a queue'

    def post(self):
        'POST an xmeml sequence to start the music report analysis. Returns a unique identifier'
        u = uuid.uuid4()
        return {'uuid':str(u)}

class AnalysisStatus(Resource):
    'Get a report on how the analysis of that uuid is going'

    def get(self, task):
        'GET a status on how the analysis of a task is going'
        return {'status': 'running',
                'task': str(task)}


api.add_resource(HelloWorld, '/')

api.add_resource(AnalyzeXmeml, '/analyze')

api.add_resource(AnalysisStatus, '/status/<uuid:task>')




if __name__ == '__main__':
    app.run(debug=True)