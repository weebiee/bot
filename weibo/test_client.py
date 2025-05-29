from unittest import TestCase, IsolatedAsyncioTestCase

from weibo.client import async_client


class TestClient(IsolatedAsyncioTestCase):
    async def test_search(self):
        async with async_client('../cache') as client:
            if not await client.search('虞书欣晒照庆祝来微博第10年'):
                self.fail()
