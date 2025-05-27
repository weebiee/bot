import asyncio

from weibo.client import async_client


async def main():
    async with async_client(cache_dir='./cache') as client:
        top_topics = await client.get_top_topics()
        posts = (await client.search(query=top_topics[0].name, page_index=1))
        print(posts[0].text)


if __name__ == "__main__":
    asyncio.run(main())
