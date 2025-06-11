import csv
from dataclasses import dataclass
from itertools import groupby
from prettytable import PrettyTable

from weibo.model import Post


@dataclass
class DataRow:
    post: Post
    topic_name: str

    def __hash__(self):
        return hash((self.post, self.topic_name))


def main():
    data = set()
    with open('posts.csv', 'rt') as fd:
        reader = csv.reader(fd)
        for row in reader:
            post = Post(poster_name=row[1], text=row[2], images=[])
            data.add(DataRow(post=post, topic_name=row[0]))

    table = PrettyTable(field_names=('Topic', 'Count'))
    table.align['Topic'] = 'l'
    table.add_row(['Unique records', len(data)])

    for group, rows in groupby(sorted(data, key=lambda p: p.topic_name), lambda p: p.topic_name):
        table.add_row([group + "\t", len(list(rows))])

    print(table)

if __name__ == '__main__':
    main()
