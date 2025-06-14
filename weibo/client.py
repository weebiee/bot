from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Iterable

from aiohttp import ClientSession, CookieJar
from bs4 import BeautifulSoup
from bs4.element import Tag

from weibo.model import Topic, Post


def _get_default_cache_dir() -> str:
    import platformdirs
    return platformdirs.site_cache_dir('Weebiee Bot')


async def _interactive_get_cookies() -> Iterable[tuple[str, str]]:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto('https://passport.weibo.com/sso/signin')
        await page.wait_for_url('https://weibo.com', timeout=0)
        cookies = await page.context.cookies()

    return ((cookie.get('name'), cookie.get('value')) for cookie in cookies)


@asynccontextmanager
async def async_client(cache_dir: str | None = None) -> AsyncGenerator['Client', Any]:
    cache_path = Path(cache_dir if cache_dir else _get_default_cache_dir())
    if not cache_path.exists():
        cache_path.mkdir()
    cookies_path = cache_path.joinpath('cookies.bin')
    cookies_jar = CookieJar()
    if cookies_path.exists():
        cookies_jar.load(cookies_path)

    async with ClientSession(cookie_jar=cookies_jar) as http_client:
        try:
            yield Client(http_client)
        finally:
            cookies_jar.save(cookies_path)


class Client:
    def __init__(self, http_client: ClientSession):
        self.__http_client = http_client

    async def get_top_topics(self) -> list[Topic]:
        response = await self.__http_client.get('https://weibo.com/ajax/side/hotSearch', headers={
            'accept': 'application/json'
        })

        realtime_items = (await response.json())['data']['realtime']
        return list(Topic(name=item['word'], rank=item['rank'], count_posts=item['num']) for item in realtime_items)

    async def sign_in(self):
        new_cookies = await _interactive_get_cookies()
        self.__http_client.cookie_jar.update_cookies(new_cookies)

    async def is_signed_in(self) -> bool:
        from yarl import URL
        url = URL(f'https://s.weibo.com/weibo?q=我和佛祖打CS', encoded=True)
        headers = {
            'Host': 's.weibo.com'
        }
        response = await self.__http_client.get(url, headers=headers)
        return response.status == 200

    async def search(self, query: str, page_index: int = 1) -> list[Post] | None:
        from urllib.parse import quote
        url = f'https://s.weibo.com/weibo?q={quote(query, safe='')}&page={page_index}&t=31'
        headers = {
            'Host': 's.weibo.com',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
        }
        response = await self.__http_client.get(url, headers=headers)
        if response.status == 403:
            await self.sign_in()
            response = await self.__http_client.get(url, headers=headers)

        res_text = await response.text()
        if len(res_text) < 100:
            return None

        bs = BeautifulSoup(res_text, 'lxml')
        posts = []
        for tag in bs.find_all(attrs={'action-type': 'feed_list_item', 'class': 'card-wrap'}):
            post = tag.find('p', attrs={'class': 'txt', 'node-type': 'feed_list_content_full'}) or tag.find('p', attrs={'class': 'txt', 'node-type': 'feed_list_content'})
            if not post or not post.has_attr('nick-name'):
                continue

            content = ''.join(child.text.strip() for child in post.childGenerator() if
                              not isinstance(child, Tag) or not child.find('i', attrs={'class': 'wbicon'}))
            posts.append(Post(
                poster_name=post.get('nick-name'),
                text=content,
                images=[]
            ))

        return posts

    async def __aenter__(self):
        await self.__http_client.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.__http_client.__aexit__(exc_type, exc_val, exc_tb)
