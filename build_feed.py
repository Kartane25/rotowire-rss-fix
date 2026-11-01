
from datetime import datetime, timezone
from email.utils import format_datetime
from zoneinfo import ZoneInfo
import re
import xml.etree.ElementTree as ET

import requests

SOURCE_URL = "https://www.rotowire.com/rss/news.php?sport=NHL"
OUTPUT_FILE = "feed.xml"

PACIFIC = ZoneInfo("America/Los_Angeles")

DATE_PATTERN = re.compile(
    r"^([A-Za-z]{3},\s+\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\s+"
    r"(\d{1,2}:\d{2}:\d{2})\s+(AM|PM)\s+(PDT|PST)$",
    re.IGNORECASE
)


def correct_date(original):
    original = original.strip()
    match = DATE_PATTERN.match(original)

    if not match:
        raise ValueError(f"Unrecognized RotoWire date: {original}")

    date_part, time_part, meridiem, zone = match.groups()

    local_date = datetime.strptime(
        f"{date_part} {time_part} {meridiem.upper()}",
        "%a, %d %b %Y %I:%M:%S %p"
    )

    local_date = local_date.replace(tzinfo=PACIFIC)

    if local_date.strftime("%Z") != zone.upper():
        raise ValueError(f"Timezone mismatch: {original}")

    utc_date = local_date.astimezone(timezone.utc)

    return format_datetime(utc_date, usegmt=True)


def build_feed():
    response = requests.get(
        SOURCE_URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )
    response.raise_for_status()

    root = ET.fromstring(response.content)

    items = root.findall("./channel/item")

    if not items:
        raise RuntimeError("No RotoWire articles found.")

    corrected = 0

    for item in items:
        pub_date = item.find("pubDate")

        if pub_date is None or not pub_date.text:
            continue

        original = pub_date.text.strip()

        if DATE_PATTERN.match(original):
            pub_date.text = correct_date(original)
            corrected += 1
        else:
            raise ValueError(
                f"Unexpected publication date: {original}"
            )

    if corrected == 0:
        raise RuntimeError("No publication dates were corrected.")

    ET.indent(root, space="  ")

    tree = ET.ElementTree(root)
    tree.write(
        OUTPUT_FILE,
        encoding="utf-8",
        xml_declaration=True
    )

    print(f"Processed {len(items)} RotoWire articles.")
    print(f"Corrected {corrected} publication dates.")
    print("RSS feed generated successfully.")


if __name__ == "__main__":
    build_feed()
