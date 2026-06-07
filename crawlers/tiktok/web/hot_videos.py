from typing import Any, Dict, Iterable, List, Optional


def _safe_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0


def _first_dict(*values: Any) -> Dict[str, Any]:
    for value in values:
        if isinstance(value, dict):
            return value
    return {}


def _first_value(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", []):
            return value
    return None


def _safe_str(value: Any) -> str:
    return "" if value is None else str(value)


def _first_url(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return str(value[0]) if value else ""
    if isinstance(value, dict):
        return _first_url(
            _first_value(
                value.get("urlList"),
                value.get("url_list"),
                value.get("urls"),
                value.get("uri"),
            )
        )
    return ""


def extract_search_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = _first_value(
        payload.get("data"),
        payload.get("item_list"),
        payload.get("aweme_list"),
        payload.get("items"),
        [],
    )
    if not isinstance(data, list):
        return []

    items = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        item_info = _first_dict(entry.get("itemInfo"), entry.get("item_info"))
        item = _first_dict(
            entry.get("item"),
            entry.get("aweme_info"),
            entry.get("itemStruct"),
            item_info.get("itemStruct"),
            entry,
        )
        if item:
            items.append(item)
    return items


def extract_search_id(payload: Dict[str, Any]) -> str:
    extra = _first_dict(payload.get("extra"))
    log_pb = _first_dict(payload.get("log_pb"), payload.get("logPb"))
    return str(
        _first_value(
            payload.get("searchId"),
            payload.get("search_id"),
            extra.get("logid"),
            log_pb.get("impr_id"),
            "",
        )
    )


def get_next_cursor(payload: Dict[str, Any], fallback: int) -> int:
    cursor = _first_value(
        payload.get("cursor"),
        payload.get("nextCursor"),
        payload.get("next_cursor"),
        payload.get("maxCursor"),
        payload.get("max_cursor"),
    )
    next_cursor = _safe_int(cursor)
    return next_cursor if next_cursor > 0 else fallback


def has_more_results(payload: Dict[str, Any]) -> bool:
    marker = _first_value(
        payload.get("has_more"),
        payload.get("hasMore"),
        payload.get("has_more_result"),
        payload.get("hasMoreResult"),
    )
    if marker is None:
        return True
    return bool(_safe_int(marker))


def normalize_search_item(keyword: str, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    stats = _first_dict(item.get("stats"), item.get("statsV2"), item.get("statistics"))
    author = _first_dict(item.get("author"), item.get("authorInfo"), item.get("author_info"))
    video = _first_dict(item.get("video"))
    music = _first_dict(item.get("music"))
    share_info = _first_dict(item.get("shareInfo"), item.get("share_info"))

    item_id = _safe_str(_first_value(item.get("id"), item.get("itemId"), item.get("aweme_id")))
    if not item_id:
        return None

    unique_id = _safe_str(_first_value(author.get("uniqueId"), author.get("unique_id")))
    share_url = _safe_str(_first_value(share_info.get("shareUrl"), share_info.get("share_url")))
    is_photo = bool(_first_dict(item.get("imagePost"), item.get("image_post")))

    if share_url:
        url = share_url
    elif unique_id:
        post_type = "photo" if is_photo else "video"
        url = f"https://www.tiktok.com/@{unique_id}/{post_type}/{item_id}"
    else:
        url = f"https://www.tiktok.com/video/{item_id}"

    play_count = _safe_int(_first_value(stats.get("playCount"), stats.get("play_count")))
    digg_count = _safe_int(_first_value(stats.get("diggCount"), stats.get("digg_count")))
    comment_count = _safe_int(_first_value(stats.get("commentCount"), stats.get("comment_count")))
    share_count = _safe_int(_first_value(stats.get("shareCount"), stats.get("share_count")))
    collect_count = _safe_int(_first_value(stats.get("collectCount"), stats.get("collect_count")))

    hot_score = (
        play_count
        + digg_count * 8
        + comment_count * 12
        + share_count * 16
        + collect_count * 10
    )

    return {
        "keyword": keyword,
        "id": item_id,
        "url": url,
        "desc": _safe_str(_first_value(item.get("desc"), item.get("description"))),
        "create_time": _safe_int(_first_value(item.get("createTime"), item.get("create_time"))),
        "is_photo": is_photo,
        "author": {
            "id": _safe_str(_first_value(author.get("id"), author.get("uid"))),
            "unique_id": unique_id,
            "nickname": _safe_str(_first_value(author.get("nickname"), author.get("nickName"))),
            "avatar": _first_url(
                _first_value(author.get("avatarThumb"), author.get("avatar_thumb"), author.get("avatarMedium"))
            ),
        },
        "music": {
            "id": _safe_str(_first_value(music.get("id"))),
            "title": _safe_str(_first_value(music.get("title"))),
            "author": _safe_str(_first_value(music.get("authorName"), music.get("author_name"))),
        },
        "stats": {
            "play_count": play_count,
            "digg_count": digg_count,
            "comment_count": comment_count,
            "share_count": share_count,
            "collect_count": collect_count,
        },
        "hot_score": hot_score,
        "cover": _first_url(_first_value(video.get("cover"), video.get("originCover"), video.get("dynamicCover"))),
        "play_addr": _first_url(video.get("playAddr")),
        "download_addr": _first_url(video.get("downloadAddr")),
    }


def normalize_search_items(keyword: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    videos = []
    for item in extract_search_items(payload):
        video = normalize_search_item(keyword, item)
        if video is not None:
            videos.append(video)
    return videos


def rank_hot_videos(
        videos: Iterable[Dict[str, Any]],
        sort_by: str = "hot",
        include_photos: bool = False,
) -> List[Dict[str, Any]]:
    metric_map = {
        "hot": "hot_score",
        "play": "stats.play_count",
        "like": "stats.digg_count",
        "comment": "stats.comment_count",
        "share": "stats.share_count",
        "collect": "stats.collect_count",
        "create_time": "create_time",
    }
    metric = metric_map.get(sort_by, "hot_score")

    deduped = {}
    for video in videos:
        if not include_photos and video.get("is_photo"):
            continue
        video_id = video.get("id")
        if not video_id:
            continue
        current = deduped.get(video_id)
        if current is None or video.get("hot_score", 0) > current.get("hot_score", 0):
            deduped[video_id] = video

    def metric_value(video: Dict[str, Any]) -> int:
        if "." not in metric:
            return _safe_int(video.get(metric))
        first, second = metric.split(".", 1)
        return _safe_int(_first_dict(video.get(first)).get(second))

    return sorted(deduped.values(), key=metric_value, reverse=True)
