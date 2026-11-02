"""Scrape faithfulwordbaptist.org/page5.html and render an audio podcast feed (feed.xml)."""
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

SOURCE = "https://www.faithfulwordbaptist.org/page5.html"
FEED_URL = "https://gitboy.github.io/rss/feed.xml"
OUT = "feed.xml"
COVER_URL = "https://gitboy.github.io/rss/cover.png"  # 1400x1400, committed next to feed.xml
YEARS = 3  # how far back the feed reaches; the site archive goes back to 2006

DATE = re.compile(r"^(\d\d)/(\d\d)/(\d\d), .*?(AM|PM)?$")


def parse(html):
    """Yield (mp3_url, title, speaker, pubdate) for every dated mp3 row, newest first."""
    # lxml: the page has stray </tr> tags, so rows are not nested reliably; walk td siblings instead
    soup = BeautifulSoup(html, "lxml")
    for a in soup.select('a[href$=".mp3"]'):
        td = a.find_parent("td")
        title_td = td.find_previous_sibling("td") if td else None
        date_td = title_td.find_previous_sibling("td") if title_td else None
        speaker_td = td.find_next_sibling("td") if td else None
        m = DATE.match(date_td.get_text(strip=True)) if date_td else None
        if not m or not title_td:  # undated rows ("06/2013, Series", "Movie") are old one-offs
            continue
        mm, dd, yy, ampm = m.groups()
        # ponytail: UTC with AM=10:00 / PM=18:00, only used to order same-day services
        hour = 18 if ampm == "PM" else 10
        pub = datetime(2000 + int(yy), int(mm), int(dd), hour, tzinfo=timezone.utc)
        yield (
            str(a["href"]).replace("http://", "https://", 1),  # Apple requires https enclosures
            title_td.get_text(strip=True),
            speaker_td.get_text(strip=True) if speaker_td else "",
            pub,
        )


def known_sizes(path):
    """url -> byte length from the previously published feed, so only new sermons need a HEAD request."""
    try:
        root = ElementTree.parse(path).getroot()
    except (FileNotFoundError, ElementTree.ParseError):
        return {}
    return {e.get("url"): int(e.get("length")) for e in root.iter("enclosure")}


def size(client, url):
    try:
        r = client.head(url, follow_redirects=True)
        r.raise_for_status()
        return int(r.headers["content-length"])
    except (httpx.HTTPError, KeyError, ValueError) as e:
        print(f"skip {url}: {e!r}", file=sys.stderr)  # retried on the next run


def build(rows, sizes):
    fg = FeedGenerator()
    fg.load_extension("podcast")
    fg.title("Faithful Word Baptist Church Sermons (unofficial)")
    fg.link(href=FEED_URL, rel="self")
    fg.link(href=SOURCE, rel="alternate")
    fg.description("Unofficial audio-only feed generated from faithfulwordbaptist.org.")
    fg.language("en")
    fg.logo(COVER_URL)
    fg.podcast.itunes_image(COVER_URL)
    fg.podcast.itunes_category("Religion & Spirituality", "Christianity")
    fg.podcast.itunes_explicit("no")
    for (url, title, speaker, pub), length in zip(rows, sizes):
        fe = fg.add_entry(order="append")
        fe.id(url)
        fe.guid(url, permalink=False)
        fe.title(title)
        fe.description(title)
        fe.pubDate(pub)
        fe.enclosure(url, str(length), "audio/mpeg")
        if speaker:
            fe.podcast.itunes_author(speaker)
    return fg


def main():
    with httpx.Client(timeout=60, headers={"User-Agent": "fwbc-rss"}) as client:
        html = client.get(SOURCE, follow_redirects=True)
        html.raise_for_status()
        cutoff = datetime.now(timezone.utc) - timedelta(days=365 * YEARS)
        rows = sorted((r for r in parse(html.text) if r[3] >= cutoff), key=lambda r: r[3], reverse=True)
        known = known_sizes(OUT)
        new = [r[0] for r in rows if r[0] not in known]
        with ThreadPoolExecutor(8) as pool:
            known.update(zip(new, pool.map(lambda u: size(client, u), new)))
    rows = [r for r in rows if known.get(r[0])]
    build(rows, [known[r[0]] for r in rows]).rss_file(OUT, pretty=True)
    print(f"wrote {OUT}: {len(rows)} items ({len(new)} new), newest {rows[0][1]!r}", file=sys.stderr)


if __name__ == "__main__":
    main()
