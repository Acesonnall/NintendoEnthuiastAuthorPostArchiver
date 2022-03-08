"""Archive all posts from a Nintendo Enthusiast author"""
import asyncio
import logging
from functools import wraps

import click as click

from src.ne_scraper import NEArchiver

LOG = logging.getLogger("ne_archive")
LOG.setLevel(logging.DEBUG)

# create console handler and set level to debug.
# logging.StreamHandler(sys.stdout) to print to stdout instead of the default stderr
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
LOG.addHandler(ch)


def coro(f):
    """
    Wrapper to help click work with async functions
    @param f:
    @return:
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


@click.command()
@click.option(
    "--author",
    required=True,
    type=str,
    help="The author's name as seen in the author url (i.e. For 'nintendoenthusiast.com/author/omar-t/', the author is "
    "'omar-t'",
)
@click.option(
    "--debug/--no-debug",
    default=False,
    help="Turn on or off debug logs",
    show_default=True,
)
@click.option(
    "--max-backoff-override",
    default=0.0,
    type=float,
    help="The default backoff time maximum may not be sufficient. Use this to override. Value is in minutes",
)
@coro
async def ne_archive(author: str, debug: bool, max_backoff_override: float):
    LOG.info(f"Archiving all posts from {author}")
    ne_scraper = NEArchiver(
        author=author, debug=debug, max_backoff_override=max_backoff_override
    )
    await ne_scraper.archive()


if __name__ == "__main__":
    asyncio.run(ne_archive())
