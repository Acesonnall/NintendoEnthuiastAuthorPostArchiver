"""Script to Archive Nintendo Enthusiast Posts"""

import asyncio
import logging
import time

import aiohttp as aiohttp
from bs4 import BeautifulSoup
from typing import List
from waybackpy import WaybackMachineSaveAPI
from waybackpy.exceptions import TooManyRequestsError


class NEArchiver:
    def __init__(self, author: str, debug: bool):
        """Instantiates top-level url to begin scraping from"""
        self.debug = debug
        # create self.LOGger
        self.LOG = logging.getLogger("NEArchiver")
        if self.debug:
            self.LOG.setLevel(logging.DEBUG)
        else:
            self.LOG.setLevel(logging.INFO)
        # create console handler and set level to debug.
        # self.LOGging.StreamHandler(sys.stdout) to print to stdout instead of the default stderr
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        # create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to self.LOGger
        self.LOG.addHandler(ch)
        self.root_url = f"https://www.nintendoenthusiast.com/author/{author}"
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 5.1; rv:40.0) Gecko/20100101 Firefox/40.0"
        )
        self.archived_page_urls = []

    async def get_author_posts(self, soup) -> List:
        return (
            soup.find_all("div", class_="mnmd-main-col")
            .pop()
            .find_all("h3", class_="post__title")
        )

    async def fetch_page(self, url: str) -> BeautifulSoup:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                # Convert the response into an easily parsable object
                text = await r.read()
                soup = BeautifulSoup(text.decode("utf-8"), "html.parser")
        return soup

    async def archive(self):
        """This code will only work on Windows as it stands now."""
        try:
            # Get the first page
            self.LOG.info(f"Fetching {self.root_url}...")
            p1_soup = await self.fetch_page(self.root_url)
            # Extract total page numbers
            total_page_numbers = int(
                p1_soup.find_all("a", class_="mnmd-pagination__item").pop().get_text()
            )
            # Extract list of author posts from all pages
            self.LOG.info(
                f"Extracting remaining {total_page_numbers - 1} pages of author posts..."
            )
            tasks = []
            for page_number in range(2, total_page_numbers + 1):
                tasks.append(
                    asyncio.create_task(
                        self.fetch_page(f"{self.root_url}/page/{page_number}/")
                    )
                )
            remaining_pages_soup = await asyncio.gather(*tasks)
            author_posts = await self.get_author_posts(p1_soup)
            for page_soup in remaining_pages_soup:
                author_posts.extend(await self.get_author_posts(page_soup))
            self.LOG.info(
                f"Found {len(author_posts)} posts. Archiving them. Wayback Machine could try to fight us so this "
                f"could take a while. "
            )
            self.LOG.info(
                "Be prepared to let this run for 30 minutes to a day depending on how much posts you're "
                "archiving."
            )
            # Archive all posts
            tasks = []
            for idx, author_post in enumerate(author_posts):
                tasks.append(asyncio.create_task(self._archive(author_post)))
                if not len(tasks) % 15:
                    try:
                        self.archived_page_urls.extend(await asyncio.gather(*tasks))
                    except TooManyRequestsError as e:
                        back_off_mins = 10
                        self.LOG.error(e)
                        self.LOG.info(f"Backing off for {back_off_mins} minutes.")
                        time.sleep(back_off_mins * 60)
                        self.LOG.info("Resuming.")
                        continue
                    tasks.clear()
                    self.LOG.debug(
                        f"Archived {idx + 1} posts. Backing off for 2 minutes"
                    )
                    time.sleep(120)
            self.LOG.info(
                f"All {len(author_posts)} successfully archived. Here are the links to the archived pages:"
            )
            for archived_page in self.archived_page_urls:
                self.LOG.info(f"{archived_page}")
        except IndexError:
            self.LOG.error(
                "Please check that the author named entered is valid. If you're sure that's right, reach out to "
                "the code maintainer or debug the issue yourself."
            )
        except Exception as e:
            self.LOG.error(f"Exception: {e}")
            if self.archived_page_urls:
                self.LOG.info(
                    f"Some author posts were successfully archived. Here are the links to the archived pages:"
                )
                for archived_page in self.archived_page_urls:
                    self.LOG.info(f"{archived_page}")

    async def _archive(self, author_post) -> str:
        save_api = WaybackMachineSaveAPI(author_post.a["href"], self.user_agent)
        archived_page_url = save_api.save()
        return archived_page_url
