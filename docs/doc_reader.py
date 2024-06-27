import re
import zlib
from typing import ClassVar, Optional, Set, Tuple, Union

import aiohttp
from bs4 import BeautifulSoup, Tag
from markdownify import MarkdownConverter


class DocumentationReader:
    # these symbols either cause errors, don't render properly, and/or are not useful
    EXCLUDED_DIRECTIVES: ClassVar[Set[str]] = {
        'cpp:functionParam',
        'std:label',
        'std:doc',
    }

    def __init__(self, base_url: str, session: aiohttp.ClientSession) -> None:
        self.base_url = base_url
        self.session = session

        self.inventories = {}
        self.md_converter = MarkdownConverter(code_language='cpp')

    def clear_inventories(self) -> None:
        self.inventories.clear()

    async def fetch_inventory_raw(self, url: str) -> str:
        async with self.session.get(url) as resp:
            stream = resp.content
            inventory_version = int((await stream.readline()).decode().rstrip()[-1])
            if inventory_version != 2:
                raise ValueError('Unsupported inventory version')

            project_name = (await stream.readline()).decode().lstrip('Project: ')
            project_version = (await stream.readline()).decode().lstrip('Version: ')
            if 'zlib' not in (await stream.readline()).decode():
                raise ValueError('Unknown compression method')

            return zlib.decompress(await stream.read()).decode()

    def has_inventory_for_version(self, version: str) -> bool:
        return version in self.inventories

    async def update_inventory(self, version: str) -> None:
        self.inventories[version] = {}
        content = await self.fetch_inventory_raw(
            self.base_url + version + '/objects.inv'
        )
        for line in content.split('\n'):
            # regex from https://github.com/python-discord/bot/blob/main/bot/exts/info/doc/_inventory_parser.py
            match = re.match(r"(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+?(\S*)\s+(.*)", line)
            if not match:
                continue

            name, directive, _, location, _ = (
                match.groups()
            )  # ignore the parsed items we don't need
            if directive not in self.EXCLUDED_DIRECTIVES:
                self.inventories[version][name] = (
                    self.base_url + version + '/' + location
                )

    async def get_symbol_markdown(
        self, name: str, version: str
    ) -> Optional[Union[str, Tuple[str, str, str]]]:
        # 1. Will return None if the symbol is not found
        # 2. Will return a string url if the symbol was found but the documentation is not available online
        # 3. Will return a tuple of url, signature, description if the symbol was found and the documentation is available online

        try:
            url = self.inventories[version][name]
        except KeyError:
            return None

        async with self.session.get(url) as resp:
            html_content = await resp.text()
            soup = BeautifulSoup(html_content, 'html.parser')
            symbol_heading = soup.find(id=url.split('#')[-1])

        if symbol_heading is None:
            return url

        signature = symbol_heading.text.rstrip('¶')

        remaining = symbol_heading.find_next_sibling()
        # get all the elements until the child directives (like methods of a class) start
        description_elements = get_elements_before_class(
            'breathe-sectiondef', remaining.children
        )

        description = self.md_converter.convert(
            ''.join(map(str, description_elements))
        ).replace('\n\n\n', '\n')

        return url, signature.strip(), description.strip()


def get_elements_before_class(class_, children):
    elements = []
    for child in children:
        if isinstance(child, Tag):
            if class_ in child.get('class', []):
                break
            elements.append(child)
    return elements
