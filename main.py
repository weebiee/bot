import asyncio
import csv
from argparse import ArgumentParser
from asyncio import TaskGroup, Lock
from itertools import batched
from typing import IO

import tqdm.asyncio as tqdm

from ckp import Checkpoint, ProgressManager, progress_manager
from weibo.client import async_client, Client
from weibo.model import Topic


async def write_to_csv(writer: csv.DictWriter, write_lock: Lock, topic: Topic, ckp: Checkpoint, client: Client, callback) -> bool:
    next_page = ckp.page + 1
    posts = await client.search(topic.name, next_page)
    if posts is None:
        return True
    elif not posts:
        return False

    await write_lock.acquire()
    writer.writerows((topic.name, post.poster_name, post.text, *(im.url for im in post.images)) for post in posts)
    ckp.context.amount += len(posts)
    write_lock.release()

    ckp.page = next_page
    await callback()
    return True


async def scrap(output: IO[str], progress: ProgressManager, parallel_tasks: int, interval: float, target_amount: int, callback):
    output_writer = csv.writer(output)
    write_lock = Lock()

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
                        write_to_csv(output_writer, write_lock, topic, progress[topic.name], client, callback)) for topic in chunked_topics)

                empty_topics = set(chunked_topics[idx] for idx, r in enumerate(results) if not r.result())
                if empty_topics:
                    print(f'Empty topics: {', '.join(f'{topic.name} (p{progress[topic.name].page})' for topic in empty_topics)}')

                await asyncio.sleep(interval)
                next_nonempty_topics -= empty_topics

                await callback()
                if progress.amount >= target_amount:
                    break

            current_working_topics = set(next_nonempty_topics)

    if progress.amount < target_amount:
        print('Scrapping ended because every topic is empty')


async def main():
    arg_parser = ArgumentParser()
    arg_parser.add_argument('--parallelism', '-p', type=int, default=8)
    arg_parser.add_argument('--interval', '-I', type=float, default=30)
    args = arg_parser.parse_args()

    checkpoint_path = 'scrapping.ckpt'
    target_amount = 100_000
    with progress_manager(checkpoint_path) as ckp_mgr, open('posts.csv', 'a+') as posts, tqdm.tqdm(
            total=target_amount) as pbar:
        async def callback():
            posts.flush()
            ckp_mgr.save(checkpoint_path)
            pbar.n = ckp_mgr.amount
            pbar.refresh()

        await scrap(posts, ckp_mgr, args.parallelism, args.interval, target_amount, callback)


if __name__ == "__main__":
    asyncio.run(main())
