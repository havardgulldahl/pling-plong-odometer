#!/usr/bin/env python3

import json
import sys
import io
import asyncio
import asyncpg # pip install asyncpg
import configparser
import datetime
import io
import collections
import attr
import logging

@attr.s
class DataPoint:
    'Hold data from the DB'
    resolver:str = attr.ib()
    result_code:int = attr.ib()
    count:int = attr.ib()
    #'relative:float = attr.ib(init=False)

    def to_dict(self): 
        return attr.asdict(self)

@attr.s
class Dataset:
    'sort DataPoints'
    _set:collections.OrderedDict = attr.ib(default=collections.OrderedDict())

    def append(self, dp:DataPoint):
        'add to dataset'
        if not dp.resolver in self._set:
            self._set.update({dp.resolver: []})
        self._set[dp.resolver].append(dp)

class DataPointEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, DataPoint):
            return obj.to_dict()
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

async def main(configuration:configparser.ConfigParser, outfile:io.TextIOWrapper):
    'main routine'
    dbpool = await asyncpg.create_pool(dsn=configuration.get('db', 'dsn'))

    async def strip(sql:str) -> list:
        'run an sql query and return naked items'
        result = await dbpool.fetch(sql)
        return [ r[0] for r in result ]

    resolvers = await strip('''SELECT DISTINCT resolver from resolve_result ORDER BY resolver ASC;''')

    result_codes = await strip('''SELECT DISTINCT result_code from resolve_result ORDER BY result_code ASC;''')


    async def run(setname:str, sql:str) -> dict:
        'run an SQL query and return a dict with a named key'
        dataset = Dataset()
        for r in await dbpool.fetch(sql):
            dataset.append(DataPoint(**dict(r.items())))
        ret = []
        for name, datapoints in dataset._set.items():

            codes = {}
            for code in result_codes:
                codes[code] = sum([dp.count for dp in datapoints if dp.result_code == code])
            ret.append( {name: codes})

        return {setname: ret} 

    out = {'timestamp':datetime.datetime.now().isoformat()}
    out.update(await run('activity_24hrs', 
        '''SELECT  resolver, result_code, COUNT(resolver)
        FROM    resolve_result
        WHERE   timestamp >= NOW() - '1 day'::INTERVAL
        GROUP BY result_code, resolver
        ORDER BY resolver'''
    ))
    out.update(await run('activity_7days', 
        '''SELECT  resolver, result_code, COUNT(resolver)
        FROM    resolve_result
        WHERE   timestamp >= NOW() - '7 day'::INTERVAL
        GROUP BY result_code, resolver
        ORDER BY resolver'''
    ))
    
    from pprint import pprint, pformat

    #pprint(out)
    #outfile.write(pformat(out))
    json.dump(out, outfile, cls=DataPointEncoder, indent=0)
    
    await dbpool.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    import argparse

    parser = argparse.ArgumentParser(description="Odometer stats generator")
    parser.add_argument('outfile', nargs='?', type=argparse.FileType('w'), default=sys.stdout)
    parser.add_argument('--configfile', default='config.ini')
    args = parser.parse_args()

    configuration = configparser.ConfigParser()
    configuration.read(args.configfile)

    ioloop = asyncio.get_event_loop()
    #tasks = [ioloop.create_task(foo()), ioloop.create_task(bar())]
    #wait_tasks = asyncio.wait(tasks)
    ioloop.run_until_complete(main(configuration, args.outfile))
    ioloop.close()