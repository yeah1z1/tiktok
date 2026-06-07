import argparse
import asyncio
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crawlers.tiktok.web.hot_videos import rank_hot_videos
from crawlers.tiktok.web.web_crawler import TikTokWebCrawler


def parse_keywords(values: Iterable[str]) -> List[str]:
    keywords = []
    for value in values:
        for keyword in value.split(","):
            keyword = keyword.strip()
            if keyword and keyword not in keywords:
                keywords.append(keyword)
    return keywords


def resolve_output(path: str) -> Path:
    output = Path(path)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def build_proxies(http_proxy: str, https_proxy: str) -> Dict[str, str]:
    proxies = {}
    if http_proxy:
        proxies["http://"] = http_proxy
    if https_proxy:
        proxies["https://"] = https_proxy
    return proxies


def write_json(path: Path, payload: Dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, videos: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "keyword",
        "rank",
        "hot_score",
        "id",
        "url",
        "desc",
        "create_time",
        "play_count",
        "digg_count",
        "comment_count",
        "share_count",
        "collect_count",
        "author_unique_id",
        "author_nickname",
        "music_title",
        "cover",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index, video in enumerate(videos, start=1):
            stats = video.get("stats", {})
            author = video.get("author", {})
            music = video.get("music", {})
            writer.writerow({
                "keyword": video.get("keyword", ""),
                "rank": index,
                "hot_score": video.get("hot_score", 0),
                "id": video.get("id", ""),
                "url": video.get("url", ""),
                "desc": video.get("desc", ""),
                "create_time": video.get("create_time", ""),
                "play_count": stats.get("play_count", 0),
                "digg_count": stats.get("digg_count", 0),
                "comment_count": stats.get("comment_count", 0),
                "share_count": stats.get("share_count", 0),
                "collect_count": stats.get("collect_count", 0),
                "author_unique_id": author.get("unique_id", ""),
                "author_nickname": author.get("nickname", ""),
                "music_title": music.get("title", ""),
                "cover": video.get("cover", ""),
            })


async def run(args: argparse.Namespace) -> Dict:
    keywords = parse_keywords(args.keywords)
    if not keywords:
        raise ValueError("At least one keyword is required.")

    crawler = TikTokWebCrawler(
        cookie=args.cookie,
        proxies=build_proxies(args.http_proxy, args.https_proxy),
    )

    results = []
    all_videos = []
    errors = []
    for keyword in keywords:
        try:
            result = await crawler.fetch_keyword_hot_videos(
                keyword=keyword,
                pages=args.pages,
                cursor=args.cursor,
                count=args.count,
                limit=args.limit,
                sort_by=args.sort_by,
                sort_type=args.sort_type,
                publish_time=args.publish_time,
                region=args.region,
                language=args.language,
                include_photos=args.include_photos,
                include_raw=args.include_raw,
            )
        except Exception as exc:
            error = {
                "keyword": keyword,
                "error": str(exc),
                "error_type": exc.__class__.__name__,
            }
            errors.append(error)
            result = {
                "keyword": keyword,
                "cursor": args.cursor,
                "pages_requested": args.pages,
                "total": 0,
                "sort_by": args.sort_by,
                "videos": [],
                "error": error,
            }
            if args.fail_fast:
                raise
        results.append(result)
        all_videos.extend(result.get("videos", []))
        if args.sleep > 0:
            await asyncio.sleep(args.sleep)

    all_videos = rank_hot_videos(all_videos, sort_by=args.sort_by, include_photos=args.include_photos)
    if args.global_limit > 0:
        all_videos = all_videos[:args.global_limit]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "keywords": keywords,
        "sort_by": args.sort_by,
        "videos": all_videos,
        "results": results,
        "errors": errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch and rank hot TikTok videos by keyword.",
    )
    parser.add_argument(
        "--keywords",
        nargs="+",
        required=True,
        help='Keywords separated by spaces or commas, for example: --keywords "ai tools,fitness"',
    )
    parser.add_argument("--pages", type=int, default=1, help="Pages to fetch for each keyword.")
    parser.add_argument("--cursor", type=int, default=0, help="Start cursor.")
    parser.add_argument("--count", type=int, default=20, help="Items per page.")
    parser.add_argument("--limit", type=int, default=20, help="Per-keyword result limit.")
    parser.add_argument("--global-limit", type=int, default=100, help="Merged result limit.")
    parser.add_argument(
        "--sort-by",
        default="hot",
        choices=["hot", "play", "like", "comment", "share", "collect", "create_time"],
        help="Ranking metric.",
    )
    parser.add_argument("--sort-type", type=int, default=0, help="TikTok search sort type.")
    parser.add_argument("--publish-time", type=int, default=0, help="TikTok publish time filter.")
    parser.add_argument("--region", default="US", help="TikTok region.")
    parser.add_argument("--language", default="en", help="TikTok language.")
    parser.add_argument("--include-photos", action="store_true", help="Include photo posts.")
    parser.add_argument("--include-raw", action="store_true", help="Include raw TikTok pages in JSON output.")
    parser.add_argument("--fail-fast", action="store_true", help="Stop immediately when one keyword fails.")
    parser.add_argument("--sleep", type=float, default=1.0, help="Seconds to sleep between keywords.")
    parser.add_argument("--cookie", default="", help="TikTok cookie override. TIKTOK_COOKIE also works.")
    parser.add_argument("--http-proxy", default="", help="HTTP proxy override. TIKTOK_HTTP_PROXY also works.")
    parser.add_argument("--https-proxy", default="", help="HTTPS proxy override. TIKTOK_HTTPS_PROXY also works.")
    parser.add_argument("--output", default="outputs/tiktok_hot_videos.json", help="JSON output path.")
    parser.add_argument("--csv-output", default="", help="Optional CSV output path.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    payload = asyncio.run(run(args))

    json_path = resolve_output(args.output)
    write_json(json_path, payload)
    print(f"Wrote {len(payload['videos'])} videos to {json_path}")
    if payload["errors"]:
        print(f"{len(payload['errors'])} keyword(s) failed; see the errors field in the JSON output.")

    if args.csv_output:
        csv_path = resolve_output(args.csv_output)
        write_csv(csv_path, payload["videos"])
        print(f"Wrote CSV to {csv_path}")


if __name__ == "__main__":
    main()
