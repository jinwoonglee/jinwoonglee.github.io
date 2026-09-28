"""Check local references in the site's HTML files (standard library only).

For every href/src that points inside the site:
  - the referenced file must exist;
  - a #fragment must match an id in the target page.
Exits with status 1 if anything is broken.

Usage (from the project root): python3 site/.github/scripts/check_site.py
"""
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

SITE = Path(__file__).resolve().parents[2]  # site/.github/scripts/ -> site/


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.refs = []  # (line, url)

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name == "id" and value:
                self.ids.add(value)
            elif name in ("href", "src") and value is not None:
                self.refs.append((self.getpos()[0], value))


def main():
    pages = {}
    for path in sorted(SITE.rglob("*.html")):
        parser = PageParser()
        parser.feed(path.read_text(encoding="utf-8"))
        pages[path] = parser

    errors, checked = [], 0
    for page, parser in pages.items():
        for line, ref in parser.refs:
            url = urlsplit(ref)
            if url.scheme or url.netloc:  # external: https:, mailto:, //host
                continue
            checked += 1
            where = f"{page.relative_to(SITE).as_posix()}:{line}"
            target = page
            if url.path:
                base = SITE if url.path.startswith("/") else page.parent
                target = (base / unquote(url.path).lstrip("/")).resolve()
                if target.is_dir():
                    target /= "index.html"
                if not target.is_file():
                    errors.append(f"{where}: file not found: {ref}")
                    continue
            if url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                errors.append(f"{where}: no element with id '{url.fragment}': {ref}")

    for error in errors:
        print(error)
    print(f"{len(pages)} page(s), {checked} local reference(s), {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
