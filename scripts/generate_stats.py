#!/usr/bin/env python3

import sys
import io
import asyncio
import asyncpg # pip install asyncpg
import configparser
import datetime
import io
import collections
import attr
from decimal import Decimal

@attr.s
class DataPoint:
    'Hold data from the DB'
    resolver:str = attr.ib()
    result_code:int = attr.ib()
    count:int = attr.ib()
    relative:Decimal = attr.ib(init=False)


async def main(configuration:configparser.ConfigParser, outfile:io.TextIOWrapper):
    'main routine'
    dbpool = await asyncpg.create_pool(dsn=configuration.get('db', 'dsn'))

    async def run(name:str, sql:str) -> dict:
        'run an SQL query and return a dict with a named key'
        result = await dbpool.fetch(sql)
        rows = [DataPoint(**dict(r.items())) for r in result]
        resolvers = set(j.resolver for j in rows)
        totals = {}
        for resolvername in resolvers:
            s = sum([j.count for j in rows if j.resolver == resolvername])
            totals.update({resolvername:s}) 

        for dp in rows:
            #print("count: {}, totlas: {}, relative. {!r}".format(dp.count, totals[dp.resolver], Decimal(dp.count)/Decimal(totals[dp.resolver])))
            dp.relative = Decimal(dp.count)/Decimal(totals[dp.resolver])

        return {name: rows} 

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
    outfile.write(pformat(out))
    
    await dbpool.close()


if __name__ == '__main__':
    import logging
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