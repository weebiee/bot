import asyncio

from weibo.client import Client


async def main():
    with Client(cache_directory='./cache') as client:
        top_topics = await client.get_top_topics()



if __name__ == "__main__":
    asyncio.run(main())
