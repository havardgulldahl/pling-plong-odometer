from aiohttp_apispec import docs, use_kwargs, marshal_with, AiohttpApiSpec
from aiohttp import web
from marshmallow import Schema, fields
import logging
logging.basicConfig(level=logging.DEBUG)


class RequestSchema(Schema):
    id = fields.Int()
    name = fields.Str(description='name')
    bool_field = fields.Bool()


class ResponseSchema(Schema):
    msg = fields.Str()
    data = fields.Dict()


@docs(tags=['mytag'],
      summary='Test method summary',
      description='Test method description')
@use_kwargs(RequestSchema(strict=True))
@marshal_with(ResponseSchema(), 200)
async def index(request):
    return web.json_response({'msg': 'done', 'data': {}})


app = web.Application()
app.router.add_post('/v1/test', index)

# init docs with all parameters, usual for ApiSpec
doc = AiohttpApiSpec(title='My Documentation',
                     version='v1',
                     url='/api/docs/api-docs')

# add method to form swagger json:
doc.register(app)  # we should do it only after all routes are added to router!

# now we can find it on 'http://localhost:8080/api/docs/api-docs'
web.run_app(app)