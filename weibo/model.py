class Topic:
    def __init__(self, name: str, rank: int, count_posts: int):
        self.name = name
        self.rank = rank
        self.count_posts = count_posts


class Image:
    def __init__(self, url: str):
        self.url = url


class Post:
    def __init__(self, username: str, text: str, images: list[Image]):
        self.username = username
        self.text = text
        self.images = images
