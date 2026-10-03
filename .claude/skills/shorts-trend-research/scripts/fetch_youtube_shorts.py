"""YouTube Data API v3로 최근 인기 쇼츠를 수집한다 (표준 라이브러리만 사용).

사용법:
  python fetch_youtube_shorts.py --chart [--region KR] [--max 50] --out raw.json
  python fetch_youtube_shorts.py --q "요리" [--days 14] [--region KR] [--lang ko] [--max 25] --out raw.json

환경변수 YOUTUBE_API_KEY 필요. 종료 코드: 0 성공, 1 API 오류, 2 키 없음/사용법 오류.
할당량: --chart 1단위, --q 검색 100단위 + videos 1단위 (일일 기본 10,000단위).
쇼츠 판정: 길이 180초 이하 (2024-10 이후 최대 3분).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

API = "https://www.googleapis.com/youtube/v3/"
SHORTS_MAX_SEC = 180


def _get(endpoint: str, params: dict) -> dict:
    url = API + endpoint + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            reason = json.loads(body)["error"]["errors"][0]["reason"]
        except Exception:
            reason = body[:200]
        raise SystemExit(_fail(f"API 오류 {e.code}: {reason}", 1))


def _fail(msg: str, code: int) -> int:
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False), file=sys.stderr)
    return code


def parse_duration(iso: str) -> int:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def _videos(key: str, ids: list[str]) -> list[dict]:
    out = []
    for i in range(0, len(ids), 50):
        data = _get("videos", {"key": key, "part": "snippet,statistics,contentDetails", "id": ",".join(ids[i : i + 50])})
        out.extend(data.get("items", []))
    return out


def _normalize(item: dict, now: datetime) -> dict | None:
    sec = parse_duration(item["contentDetails"].get("duration", ""))
    if not 0 < sec <= SHORTS_MAX_SEC:
        return None
    sn, st = item["snippet"], item.get("statistics", {})
    views = int(st.get("viewCount", 0))
    likes = int(st["likeCount"]) if "likeCount" in st else None
    comments = int(st["commentCount"]) if "commentCount" in st else None
    published = datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00"))
    age_days = max((now - published).total_seconds() / 86400, 0.5)
    engagement = ((likes or 0) + (comments or 0)) / views if views else None
    return {
        "id": item["id"],
        "url": f"https://www.youtube.com/shorts/{item['id']}",
        "title": sn["title"],
        "channel": sn["channelTitle"],
        "published": published.date().isoformat(),
        "duration_sec": sec,
        "views": views,
        "likes": likes,
        "comments": comments,
        "views_per_day": round(views / age_days),
        "engagement_rate": round(engagement, 4) if engagement is not None else None,
        "tags": sn.get("tags", [])[:15],
    }


def _summary(videos: list[dict]) -> dict:
    if not videos:
        return {"count": 0}
    words = Counter()
    for v in videos:
        for w in re.findall(r"#?[\w가-힣]{2,}", v["title"]):
            words[w.lower()] += 1
        for t in v["tags"]:
            words[t.lower()] += 1
    eng = [v["engagement_rate"] for v in videos if v["engagement_rate"] is not None]
    return {
        "count": len(videos),
        "median_views": int(statistics.median(v["views"] for v in videos)),
        "median_views_per_day": int(statistics.median(v["views_per_day"] for v in videos)),
        "median_engagement_rate": round(statistics.median(eng), 4) if eng else None,
        "median_duration_sec": int(statistics.median(v["duration_sec"] for v in videos)),
        "top_terms": [w for w, _ in words.most_common(20)],
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--chart", action="store_true", help="인기 차트(mostPopular)에서 쇼츠만")
    mode.add_argument("--q", help="검색어")
    p.add_argument("--region", default="KR")
    p.add_argument("--lang", default="ko")
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--max", type=int, default=25)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        return _fail("YOUTUBE_API_KEY 환경변수가 없습니다. 웹 조사로 대체하세요.", 2)

    now = datetime.now(timezone.utc)
    if a.chart:
        data = _get("videos", {"key": key, "part": "snippet,statistics,contentDetails", "chart": "mostPopular",
                               "regionCode": a.region, "maxResults": min(a.max, 50)})
        items = data.get("items", [])
        query = {"mode": "chart", "region": a.region}
    else:
        after = (now - timedelta(days=a.days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        data = _get("search", {"key": key, "part": "id", "type": "video", "videoDuration": "short", "order": "viewCount",
                               "q": a.q, "regionCode": a.region, "relevanceLanguage": a.lang,
                               "publishedAfter": after, "maxResults": min(a.max, 50)})
        ids = [it["id"]["videoId"] for it in data.get("items", [])]
        items = _videos(key, ids) if ids else []
        query = {"mode": "search", "q": a.q, "region": a.region, "days": a.days}

    videos = [v for v in (_normalize(it, now) for it in items) if v]
    videos.sort(key=lambda v: v["views_per_day"], reverse=True)
    result = {"ok": True, "collected_at": now.date().isoformat(), "query": query,
              "summary": _summary(videos), "videos": videos}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": True, "out": a.out, **result["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
