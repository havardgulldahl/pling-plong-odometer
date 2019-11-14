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
from rights import DueDiligence, SpotifyNotFoundError

async def main(configuration:configparser.ConfigParser):
    'main routine'
    dbpool = await asyncpg.create_pool(dsn=configuration.get('db', 'dsn'))
    con = await dbpool.acquire()

    async def strip(sql:str) -> list:
        'run an sql query and return naked items'
        result = await dbpool.fetch(sql)
        return [ r for r in result ]

    async def update_isrc(dma_id:str, ok=bool):
        sql = '''UPDATE dma_data_health
                 SET isrc_ok=$1, checked=NOW()
                WHERE dma_id = $2;'''
        try:
            await con.execute(sql, ok, dma_id)
        except Exception as e:
            logging.error(e)
            

    codes = await strip('''SELECT dma_id,isrc,ean FROM dma_data_health 
                           WHERE checked IS NULL AND (isrc is NOT NULL OR ean IS NOT NULL) ;''')

    spotify = DueDiligence(config=configuration)
    r = DMAResolver()
    r.config = configuration
    for dma_id, isrc_code, ean_code in codes:
        try:
            dma = await r.resolve(dma_id)
            isrc = spotify.spotify_search_track(f'isrc:{isrc_code}')
        except SpotifyNotFoundError as e:
            await update_isrc(dma_id, ok=False)
            logging.error(e)
            continue
        except Exception as e:
            logging.error(e)
            continue
        logging.info(f'DMA: title={dma.title}, artists={dma.artist}, year={dma.year}')
        logging.info(f"ISRC: title={isrc['name']}, artists={[a['name'] for a in isrc['artists'] ]}, year={isrc['album']['release_date'][:4]}")
        feedback = 'X'
        while feedback not in ('C', 'I'):
            feedback = input("====== [C]orrect  - or - [I]ncorrect ? =====").upper().strip()
        await update_isrc(dma_id, ok=feedback=='C')
        
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