#!/usr/bin/env python3

import sys
import io
import asyncio
import asyncpg # pip install asyncpg
import configparser
import datetime

async def main(configuration:configparser.ConfigParser):
    'main routine'
    dbpool = await asyncpg.create_pool(dsn=configuration.get('db', 'dsn'))

    async def run(name:str, sql:str) -> dict:
        'run an SQL query and return a dict with a named key'
        result = await dbpool.fetch(sql)

        return {name: result}

    out = {'timestamp':datetime.datetime.now().isoformat()}
    out.update(await run('activity_24hrs', 
        '''SELECT  resolver, result_code, COUNT(resolver)
        FROM    resolve_result
        WHERE   timestamp >= NOW() - '1 day'::INTERVAL
        GROUP BY result_code, resolver
        ORDER BY result_code'''
    ))
    out.update(await run('activity_7days', 
        '''SELECT  resolver, result_code, COUNT(resolver)
        FROM    resolve_result
        WHERE   timestamp >= NOW() - '7 day'::INTERVAL
        GROUP BY result_code, resolver
        ORDER BY result_code'''
    ))
    
    from pprint import pprint

    pprint(out)
    
    await dbpool.close()


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    import argparse

    parser = argparse.ArgumentParser(description="Odometer stats generator")
    #parser.add_argument('--path')
    parser.add_argument('--configfile', default='config.ini')
    args = parser.parse_args()

    configuration = configparser.ConfigParser()
    configuration.read(args.configfile)

    ioloop = asyncio.get_event_loop()
    #tasks = [ioloop.create_task(foo()), ioloop.create_task(bar())]
    #wait_tasks = asyncio.wait(tasks)
    ioloop.run_until_complete(main(configuration))
    ioloop.close()