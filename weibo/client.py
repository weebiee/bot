from pathlib import Path
from typing import Mapping

from aiohttp import ClientSession

from weibo.model import Topic


def _get_default_cache_dir() -> str:
    import platformdirs
    return platformdirs.site_cache_dir('Weebiee Bot')


async def _interactive_get_cookies() -> Mapping[str, str]:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto('https://passport.weibo.com/sso/signin')
        await page.wait_for_url('https://weibo.com', timeout=0)
        cookies = await page.context.cookies()

    return dict(cookie.items() for cookie in cookies)


class Client:
    def __init__(self, cache_directory: str | None):
        self.__http_client = ClientSession()
        self.__cache_dir = cache_directory if cache_directory else _get_default_cache_dir()

        self.__load_saved_cookie()

    def __load_saved_cookie(self):
        cookies_path = Path(self.__cache_dir, "cookies.properties")
        if cookies_path.exists():
            with open(cookies_path, 'rt') as fp:
                cookies = dict(line.strip().split('=', maxsplit=2) for line in fp.readlines())
            self.__http_client.cookie_jar.update_cookies(cookies)

    async def get_top_topics(self) -> list[Topic]:
        response = await self.__http_client.get('https://weibo.com/ajax/side/hotSearch', headers={
            'accept': 'application/json'
        })

        realtime_items = (await response.json())['data']['realtime']
        return list(Topic(name=item['word'], rank=item['rank'], count_posts=item['num']) for item in realtime_items)

    async def search(self, query: str, page_index: int):
        from yarl import URL
        url = URL(f'https://s.weibo.com/weibo?q={query}&page={page_index}', encoded=True)
        response = await self.__http_client.get(url)
        await response.text()

        # TODO: parse the result and return as list of Post models

    async def __aenter__(self):
        await self.__http_client.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.__http_client.__aexit__(exc_type, exc_val, exc_tb)
