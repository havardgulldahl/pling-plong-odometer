import asyncio

async def every_second():
    while True:
        for i in range(60):
            print(i, 's')
            await asyncio.sleep(1)

async def every_minute():
    for i in range(1, 10):
        await asyncio.sleep(10)
        print(i, 'minute')


async def multiply(x):
    result = x * 2
    await asyncio.sleep(1)
    return result


async def steps(x):
    y= await multiply(x)
    print ("result: {}".format(y))


loop = asyncio.get_event_loop()
#loop.run_until_complete(
    #asyncio.gather(every_second(),
                   #every_minute())
#)
coro = steps(5)
loop.run_until_complete(coro)
loop.close()
