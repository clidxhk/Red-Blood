#!/usr/bin/env python3
"""
Generate images from a Markdown file plus extra requirements using the OpenAI SDK.

Examples:
  python scripts/generate_image_from_md.py scene.md --extra "Ancient xianxia style, cinematic lighting"
  python scripts/generate_image_from_md.py scene.md --extra-file notes.txt --model gpt-image-2-all --n 2
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
import textwrap
import urllib.request
from pathlib import Path

try:
    from openai import OpenAI
except ImportError as exc:
    print("Missing dependency: openai. Install it with: pip install openai", file=sys.stderr)
    raise SystemExit(1) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate image files from a Markdown prompt source with the OpenAI Images API."
    )
    parser.add_argument("md_path", type=Path, help="Path to the source Markdown file.")
    parser.add_argument(
        "--extra",
        default="",
        help="Additional image requirements appended after the Markdown content.",
    )
    parser.add_argument(
        "--extra-file",
        type=Path,
        help="Optional text file containing additional image requirements.",
    )
    parser.add_argument(
        "--model",
        default="gpt-image-2-all",
        help="Image model name. Defaults to gpt-image-2-all as requested.",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="API key. Overrides OPENAI_API_KEY when provided.",
    )
    parser.add_argument(
        "--base-url",
        default="",
        help="Custom API base URL. Overrides OPENAI_BASE_URL when provided.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Optional .env file path. Used when CLI args and process env vars are absent.",
    )
    parser.add_argument(
        "--size",
        default="1024x1024",
        help="Image size, for example 1024x1024, 1536x1024, or 1024x1536.",
    )
    parser.add_argument(
        "--quality",
        default="high",
        help="Image quality value passed to the API. Common values include low, medium, or high.",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=1,
        help="Number of images to generate.",
    )
    parser.add_argument(
        "--max-md-chars",
        type=int,
        default=12000,
        help="Maximum Markdown characters to send. Longer files are truncated from the tail.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs"),
        help="Output directory for generated images.",
    )
    return parser.parse_args()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")


def truncate_markdown(markdown: str, limit: int) -> tuple[str, bool]:
    if limit <= 0 or len(markdown) <= limit:
        return markdown, False
    return markdown[:limit], True


def parse_dotenv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}

    values: dict[str, str] = {}
    for raw_line in read_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def build_prompt(markdown: str, extra_requirements: str) -> str:
    extra_block = extra_requirements.strip() or "No extra requirements."
    return textwrap.dedent(
        f"""
        Create a single polished image based on the source material below.

        Treat the Markdown as the canonical scene and art-direction source.
        Preserve important named entities, atmosphere, materials, architecture,
        clothing, symbols, lighting, and mood when they are present.
        Resolve the text into one visually coherent composition instead of a collage.

        [Markdown Source]
        {markdown}

        [Additional Requirements]
        {extra_block}
        """
    ).strip()


def save_image_from_base64(image_b64: str, path: Path) -> None:
    image_bytes = base64.b64decode(image_b64)
    path.write_bytes(image_bytes)


def save_image_from_url(url: str, path: Path) -> None:
    with urllib.request.urlopen(url) as response:
        path.write_bytes(response.read())


def main() -> int:
    args = parse_args()

    dotenv_values = parse_dotenv(args.env_file)

    api_key = (
        args.api_key.strip()
        or os.environ.get("OPENAI_API_KEY", "").strip()
        or os.environ.get("API_KEY", "").strip()
        or dotenv_values.get("OPENAI_API_KEY", "").strip()
        or dotenv_values.get("API_KEY", "").strip()
    )
    base_url = (
        args.base_url.strip()
        or os.environ.get("OPENAI_BASE_URL", "").strip()
        or os.environ.get("BASE_URL", "").strip()
        or dotenv_values.get("OPENAI_BASE_URL", "").strip()
        or dotenv_values.get("BASE_URL", "").strip()
    )

    if not api_key:
        print(
            "API key is not set. Provide --api-key, OPENAI_API_KEY/API_KEY, or put it in the .env file.",
            file=sys.stderr,
        )
        return 1

    if not args.md_path.is_file():
        print(f"Markdown file not found: {args.md_path}", file=sys.stderr)
        return 1

    markdown = read_text(args.md_path)
    markdown, was_truncated = truncate_markdown(markdown, args.max_md_chars)

    extra_parts = []
    if args.extra.strip():
        extra_parts.append(args.extra.strip())
    if args.extra_file:
        if not args.extra_file.is_file():
            print(f"Extra requirements file not found: {args.extra_file}", file=sys.stderr)
            return 1
        extra_parts.append(read_text(args.extra_file).strip())

    prompt = build_prompt(markdown, "\n\n".join(part for part in extra_parts if part))

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)
    response = client.images.generate(
        model=args.model,
        prompt=prompt,
        size=args.size,
        quality=args.quality,
        n=args.n,
    )

    args.output.mkdir(parents=True, exist_ok=True)
    stem = args.md_path.stem

    for index, item in enumerate(response.data, start=1):
        output_path = args.output / f"{stem}-{index}.png"
        if getattr(item, "b64_json", None):
            save_image_from_base64(item.b64_json, output_path)
        elif getattr(item, "url", None):
            save_image_from_url(item.url, output_path)
        else:
            print(f"No image payload returned for item {index}.", file=sys.stderr)
            return 1
        print(output_path)

    if was_truncated:
        print(
            f"Warning: Markdown was truncated to {args.max_md_chars} characters before sending.",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
