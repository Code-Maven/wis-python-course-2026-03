import argparse
import mimetypes
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download an image from a URL.")
    parser.add_argument("url", help="Image URL to download")
    parser.add_argument(
        "output",
        nargs="?",
        help="Optional output file path (default: derived from URL)",
    )
    return parser.parse_args()


def pick_output_path(url: str, content_type: str | None, output: str | None) -> Path:
    if output:
        return Path(output)

    parsed = urlparse(url)
    name_from_url = Path(parsed.path).name
    if name_from_url:
        return Path(name_from_url)

    extension = ""
    if content_type:
        content_type = content_type.split(";", 1)[0].strip().lower()
        extension = mimetypes.guess_extension(content_type) or ""

    return Path(f"downloaded_image{extension}")


def main() -> None:
    args = parse_args()

    with urlopen(args.url) as response:
        content_type = response.headers.get("Content-Type")
        if content_type and not content_type.lower().startswith("image/"):
            raise ValueError(f"URL does not point to an image. Content-Type: {content_type}")

        data = response.read()

    output_path = pick_output_path(args.url, content_type, args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)

    print(f"Saved image: {output_path}")


if __name__ == "__main__":
    main()
