from dataclasses import dataclass


@dataclass
class Topic:
    name: str
    rank: int
    count_posts: int

    def __hash__(self):
        return hash((self.name, self.rank, self.count_posts))


@dataclass
class Image:
    url: str

    def __hash__(self):
        return hash((self.url, ))


@dataclass
class Post:
    poster_name: str
    text: str
    images: list[Image]

    def __hash__(self):
        return hash((self.poster_name, self.text, *self.images))
