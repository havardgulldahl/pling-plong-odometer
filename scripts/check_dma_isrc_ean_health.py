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
import logging
from metadataresolvers import DMAResolver

async def main(configuration:configparser.ConfigParser):
    'main routine'
    dbpool = await asyncpg.create_pool(dsn=configuration.get('db', 'dsn'))

    async def strip(sql:str) -> list:
        'run an sql query and return naked items'
        result = await dbpool.fetch(sql)
        return [ r[0] for r in result ]

    dma_filenames = await strip('''SELECT DISTINCT filename FROM resolve_result 
                                   WHERE resolver='DMA' AND result_text='OK';''')

    r = DMAResolver()
    r.config = configuration
    sql = '''INSERT INTO dma_data_health
                (dma_id, isrc, ean)
            VALUES ($1, $2, $3);'''
    con = await dbpool.acquire()
    for fil in dma_filenames:
        try:
            md = await r.resolve(filename=fil)
        except Exception as e:
            logging.error(e)
            continue
        logging.info("dma: {identifier} - isrc: {isrc} - ean: {ean}".format(**vars(md)))
        try:
            await con.execute(sql, md.identifier.replace('DMATrack#', ''), md.isrc, md.ean)
        except Exception as e:
            logging.error(e)
    await con.close()
    await r.session.close()


    await dbpool.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    import argparse

    parser = argparse.ArgumentParser(description="Run code to test ISRC and EAN codes of DMA")
    parser.add_argument('--configfile', default='config.ini')
    args = parser.parse_args()

    configuration = configparser.ConfigParser()
    configuration.read(args.configfile)

    ioloop = asyncio.get_event_loop()
    #tasks = [ioloop.create_task(foo()), ioloop.create_task(bar())]
    #wait_tasks = asyncio.wait(tasks)
    ioloop.run_until_complete(main(configuration))
    ioloop.close()