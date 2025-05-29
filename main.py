import asyncio
import csv
from asyncio import TaskGroup
from itertools import batched
from typing import IO

import tqdm

from ckp import Checkpoint, ProgressManager, progress_manager
from weibo.client import async_client, Client
from weibo.model import Topic


async def write_to_csv(writer: csv.DictWriter, topic: Topic, ckp: Checkpoint, client: Client) -> bool:
    next_page = ckp.page + 1
    posts = await client.search(topic.name, next_page)
    writer.writerows((topic.name, post.username, post.text, *(im.url for im in post.images)) for post in posts)
    ckp.context.amount += len(posts)
    if not posts:
        print(f'Not proceeding because page {next_page} of topic "{topic.name}" is empty')
        return False

    ckp.page = next_page
    return True


async def scrap(output: IO[str], progress: ProgressManager, parallel_tasks: int, target_amount: int, callback):
    output_writer = csv.writer(output)

    async with async_client(cache_dir='./cache') as client:
        if not await client.is_signed_in():
            await client.sign_in()

        top_topics = await client.get_top_topics()
        current_working_topics = set(top_topics)
        next_nonempty_topics = set(top_topics)
        while progress.amount < target_amount and current_working_topics:
            for chunked_topics in batched(current_working_topics, parallel_tasks):
                async with TaskGroup() as tg:
                    results = list(tg.create_task(
                        write_to_csv(output_writer, topic, progress[topic.name], client)) for topic in chunked_topics)

                empty_topics = set(chunked_topics[idx] for idx, r in enumerate(results) if not r.result())
                next_nonempty_topics -= empty_topics

                await asyncio.sleep(30)

                await callback()
                if progress.amount >= target_amount:
                    break

            current_working_topics = set(next_nonempty_topics)

    if progress.amount < target_amount:
        print('Scrapping ended because every topic is empty')


async def main():
    checkpoint_path = 'scrapping.ckpt'
    target_amount = 100_000
    with progress_manager(checkpoint_path) as ckp_mgr, open('posts.csv', 'a+') as posts, tqdm.tqdm(
            total=target_amount) as pbar:
        async def callback():
            posts.flush()
            ckp_mgr.save(checkpoint_path)
            pbar.update(n=ckp_mgr.amount)

        await scrap(posts, ckp_mgr, 12, target_amount, callback)


if __name__ == "__main__":
    asyncio.run(main())
