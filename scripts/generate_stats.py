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
    resolver = attr.ib()
    result_code = attr.ib()
    count = attr.ib()
    #'relative:float = attr.ib(init=False)

    def to_dict(self): 
        return attr.asdict(self)

@attr.s
class Dataset:
    'sort DataPoints'
    #_set:collections.OrderedDict = attr.ib(default=collections.OrderedDict())
    _set = attr.ib(default=collections.OrderedDict())

    def append(self, dp):#:DataPoint):
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

async def main(configuration, outfile):#:configparser.ConfigParser, outfile:io.TextIOWrapper):
    'main routine'
    dbpool = await asyncpg.create_pool(dsn=configuration.get('db', 'dsn'))

    async def strip(sql):#:str) -> list:
        'run an sql query and return naked items'
        result = await dbpool.fetch(sql)
        return [ r[0] for r in result ]

    resolvers = await strip('''SELECT DISTINCT resolver from resolve_result ORDER BY resolver ASC;''')

    result_codes = await strip('''SELECT DISTINCT result_code from resolve_result ORDER BY result_code ASC;''')

    #
    # Make stats on how well the filename resolvers worked the last X days 
    #

    async def run_activity(setname, sql):#:str, sql:str) -> dict:
        'run an SQL query and return a dict with a named key'
        dataset = Dataset()
        for r in await dbpool.fetch(sql):
            dataset.append(DataPoint(**dict(r.items())))
        ret = {'labels':[],
               'datasets':{k:[] for k in result_codes},
               'tooltips':{k:[] for k in result_codes},
               }

        for name, datapoints in dataset._set.items():
            ret['labels'].append(name)
            total = sum(dp.count for dp in datapoints)
            for code in result_codes:
                num = sum([dp.count for dp in datapoints if dp.result_code == code])
                rel = float(num) / float(total)
                ret['datasets'][code].append(rel)
                ret['tooltips'][code].append(num)

        return {setname: ret} 

    out = {'timestamp':datetime.datetime.now().isoformat()}
    out.update(await run_activity('activity_24hrs', 
        '''SELECT  resolver, result_code, COUNT(resolver)
        FROM    resolve_result
        WHERE   timestamp >= NOW() - '1 day'::INTERVAL
        GROUP BY result_code, resolver
        ORDER BY resolver'''
    ))
    out.update(await run_activity('activity_7days', 
        '''SELECT  resolver, result_code, COUNT(resolver)
        FROM    resolve_result
        WHERE   timestamp >= NOW() - '7 day'::INTERVAL
        GROUP BY result_code, resolver
        ORDER BY resolver'''
    ))

    #
    # MAke statitics on how well the copyright resolvers work 

    def mkweek(record):
       return '{}W{:02d}'.format(int(record['year']), int(record['week']))

    async def run_lookup_results(setname, sql):#:str, sql:str) -> dict:
        datasets = {}
        tooltips = []

        for r in await dbpool.fetch(sql):
            #year   week    result  numrecords    
            #2019	36	    CHECK	139
            #2019	36	    NO	    3
            #2019	36	    OK	    108
            #logging.info("got row- {!r}".format(r))
            if not r['result'] in datasets.keys():
                # first time we see new series, store the old one
                datasets[r['result']] = []
            datasets[r['result']].append( {
                'x': mkweek(r),
                'y': r['numrecords']
            })

        # calculate  percentage
        

        ret = {'labels':[],
               'datasets':datasets,
               'tooltips':tooltips
               }


        return {setname: ret} 

    out.update(await run_lookup_results('ownership_resolve_efficiency_weeks',
        '''SELECT date_part('year', timestamp) as year, 
                  date_part('week', timestamp) as week, 
                  result, 
                  Count(ID) as numRecords
            FROM copyright_lookup_result
            GROUP BY date_part('year', timestamp), date_part('week', timestamp), result
            ORDER BY year, week ASC;'''
    ))

    _totals = await dbpool.fetch(
        '''SELECT date_part('year', timestamp) as year, 
                  date_part('week', timestamp) as week, 
                  Count(ID) as numRecords
        FROM copyright_lookup_result
        GROUP BY date_part('year', timestamp), date_part('week', timestamp)
        ORDER BY year, week ASC '''
    )

    totals = { mkweek(r):r['numrecords'] for r in _totals }

    _resolved = await dbpool.fetch(
        '''SELECT date_part('year', timestamp) as year, 
                  date_part('week', timestamp) as week, 
                  Count(ID) as numRecords
        FROM copyright_lookup_result
        WHERE result = 'OK' OR result = 'NO'
        GROUP BY date_part('year', timestamp), date_part('week', timestamp)
        ORDER BY year, week ASC '''
    )
    resolved = { mkweek(r):r['numrecords'] for r in _resolved }

    resolved_rate = []
    for week,total_hits in totals.items():
        try:
            val = resolved[week] / total_hits 
        except KeyError:
            val = 0
        resolved_rate.append( {
            'x': week,
            'y': val
        })  

    out.update({'resolved_rate':resolved_rate})

    from pprint import pprint, pformat

    #pprint(out)
    #outfile.write(pformat(out))
    json.dump(out, outfile, cls=DataPointEncoder, indent=1)
    
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