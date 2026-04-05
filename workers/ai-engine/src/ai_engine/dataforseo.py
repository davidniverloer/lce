from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass
import json
from typing import Any, Callable
from urllib.request import Request, urlopen

from .config import Settings


class DataForSEOError(RuntimeError):
    pass


@dataclass(frozen=True)
class DataForSEOKeywordOverview:
    keyword: str
    search_volume: int | None
    competition: float | None
    cpc: float | None
    low_top_of_page_bid: float | None
    high_top_of_page_bid: float | None
    monthly_searches: list[dict[str, Any]]


@dataclass(frozen=True)
class DataForSEOKeywordIdea:
    keyword: str
    search_volume: int | None
    competition: float | None
    cpc: float | None


@dataclass(frozen=True)
class DataForSEORelatedKeyword:
    keyword: str
    search_volume: int | None
    competition: float | None
    relevance: float | None


@dataclass(frozen=True)
class DataForSEOSerpCompetitor:
    domain: str
    avg_position: float | None
    median_position: float | None
    rating: float | None
    etv: float | None
    keywords_count: int | None
    visibility: float | None
    relevant_serp_items: int | None


@dataclass(frozen=True)
class DataForSEOSerpOrganicResult:
    domain: str
    url: str
    title: str
    rank_group: int | None
    rank_absolute: int | None
    position: str | None
    is_featured_snippet: bool


@dataclass(frozen=True)
class DataForSEOPageIntersectionKeyword:
    keyword: str
    search_volume: int | None
    competition: float | None
    intersection_score: float | None


Transport = Callable[[str, bytes, dict[str, str]], dict[str, Any]]


def _default_transport(url: str, payload: bytes, headers: dict[str, str]) -> dict[str, Any]:
    request = Request(url, data=payload, headers=headers, method="POST")
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


class DataForSEOClient:
    def __init__(
        self,
        *,
        base_url: str,
        login: str,
        password: str,
        location_code: int,
        language_code: str,
        transport: Transport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._login = login
        self._password = password
        self._location_code = location_code
        self._language_code = language_code
        self._transport = transport or _default_transport

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        transport: Transport | None = None,
    ) -> DataForSEOClient | None:
        if not settings.dataforseo_login or not settings.dataforseo_password:
            return None
        return cls(
            base_url=settings.dataforseo_base_url,
            login=settings.dataforseo_login,
            password=settings.dataforseo_password,
            location_code=settings.dataforseo_location_code,
            language_code=settings.dataforseo_language_code,
            transport=transport,
        )

    def keyword_overview(self, *, keyword: str) -> DataForSEOKeywordOverview:
        body = [
            {
                "keywords": [keyword],
                "location_code": self._location_code,
                "language_code": self._language_code,
                "include_clickstream_data": False,
                "include_serp_info": False,
            }
        ]
        response = self._transport(
            f"{self._base_url}/v3/dataforseo_labs/google/keyword_overview/live",
            json.dumps(body).encode("utf-8"),
            self._headers(),
        )

        items = self._extract_items(
            response,
            purpose="keyword overview items",
        )
        item = items[0]
        keyword_info = item.get("keyword_info") or {}
        monthly_searches = keyword_info.get("monthly_searches")

        return DataForSEOKeywordOverview(
            keyword=str(item.get("keyword") or keyword),
            search_volume=_to_int(keyword_info.get("search_volume")),
            competition=_to_float(keyword_info.get("competition")),
            cpc=_to_float(keyword_info.get("cpc")),
            low_top_of_page_bid=_to_float(keyword_info.get("low_top_of_page_bid")),
            high_top_of_page_bid=_to_float(keyword_info.get("high_top_of_page_bid")),
            monthly_searches=monthly_searches if isinstance(monthly_searches, list) else [],
        )

    def keyword_ideas(self, *, keyword: str, limit: int = 5) -> list[DataForSEOKeywordIdea]:
        body = [
            {
                "keywords": [keyword],
                "location_code": self._location_code,
                "language_code": self._language_code,
                "include_serp_info": False,
                "limit": limit,
            }
        ]
        response = self._transport(
            f"{self._base_url}/v3/dataforseo_labs/google/keyword_ideas/live",
            json.dumps(body).encode("utf-8"),
            self._headers(),
        )

        items = self._extract_items(response)
        ideas: list[DataForSEOKeywordIdea] = []
        for item in items[:limit]:
            keyword_info = item.get("keyword_info") or {}
            ideas.append(
                DataForSEOKeywordIdea(
                    keyword=str(item.get("keyword") or ""),
                    search_volume=_to_int(keyword_info.get("search_volume")),
                    competition=_to_float(keyword_info.get("competition")),
                    cpc=_to_float(keyword_info.get("cpc")),
                )
            )
        return ideas

    def related_keywords(
        self,
        *,
        keyword: str,
        limit: int = 5,
    ) -> list[DataForSEORelatedKeyword]:
        body = [
            {
                "keyword": keyword,
                "location_code": self._location_code,
                "language_code": self._language_code,
                "include_seed_keyword": False,
                "limit": limit,
            }
        ]
        response = self._transport(
            f"{self._base_url}/v3/dataforseo_labs/google/related_keywords/live",
            json.dumps(body).encode("utf-8"),
            self._headers(),
        )

        items = self._extract_items(response)
        related: list[DataForSEORelatedKeyword] = []
        for item in items[:limit]:
            keyword_data = item.get("keyword_data") or {}
            keyword_info = keyword_data.get("keyword_info") or {}
            related.append(
                DataForSEORelatedKeyword(
                    keyword=str(keyword_data.get("keyword") or item.get("keyword") or ""),
                    search_volume=_to_int(keyword_info.get("search_volume")),
                    competition=_to_float(keyword_info.get("competition")),
                    relevance=_to_float(item.get("relevance")),
                )
            )
        return related

    def serp_competitors(
        self,
        *,
        keyword: str,
        limit: int = 5,
    ) -> list[DataForSEOSerpCompetitor]:
        body = [
            {
                "keywords": [keyword],
                "location_code": self._location_code,
                "language_code": self._language_code,
                "item_types": ["organic"],
                "limit": limit,
            }
        ]
        response = self._transport(
            f"{self._base_url}/v3/dataforseo_labs/google/serp_competitors/live",
            json.dumps(body).encode("utf-8"),
            self._headers(),
        )

        items = self._extract_items(response)
        competitors: list[DataForSEOSerpCompetitor] = []
        for item in items[:limit]:
            competitors.append(
                DataForSEOSerpCompetitor(
                    domain=str(item.get("domain") or ""),
                    avg_position=_to_float(item.get("avg_position")),
                    median_position=_to_float(item.get("median_position")),
                    rating=_to_float(item.get("rating")),
                    etv=_to_float(item.get("etv")),
                    keywords_count=_to_int(item.get("keywords_count")),
                    visibility=_to_float(item.get("visibility")),
                    relevant_serp_items=_to_int(item.get("relevant_serp_items")),
                )
            )
        return competitors

    def serp_organic_results(
        self,
        *,
        keyword: str,
        limit: int = 10,
    ) -> list[DataForSEOSerpOrganicResult]:
        body = [
            {
                "keyword": keyword,
                "location_code": self._location_code,
                "language_code": self._language_code,
                "device": "desktop",
                "os": "windows",
                "depth": limit,
            }
        ]
        response = self._transport(
            f"{self._base_url}/v3/serp/google/organic/live/advanced",
            json.dumps(body).encode("utf-8"),
            self._headers(),
        )

        items = self._extract_items(
            response,
            purpose="SERP items",
        )

        organic_results: list[DataForSEOSerpOrganicResult] = []
        for item in items:
            if str(item.get("type") or "") != "organic":
                continue
            organic_results.append(
                DataForSEOSerpOrganicResult(
                    domain=str(item.get("domain") or ""),
                    url=str(item.get("url") or ""),
                    title=str(item.get("title") or ""),
                    rank_group=_to_int(item.get("rank_group")),
                    rank_absolute=_to_int(item.get("rank_absolute")),
                    position=str(item.get("position")) if item.get("position") is not None else None,
                    is_featured_snippet=bool(item.get("is_featured_snippet", False)),
                )
            )
            if len(organic_results) >= limit:
                break
        return organic_results

    def page_intersection(
        self,
        *,
        page_urls: list[str],
        limit: int = 10,
        intersection_mode: str = "intersect",
    ) -> list[DataForSEOPageIntersectionKeyword]:
        if len(page_urls) < 2:
            return []

        pages = {
            str(index): url
            for index, url in enumerate(page_urls[:20], start=1)
            if url
        }
        body = [
            {
                "pages": pages,
                "location_code": self._location_code,
                "language_code": self._language_code,
                "item_types": ["organic"],
                "intersection_mode": intersection_mode,
                "limit": limit,
            }
        ]
        response = self._transport(
            f"{self._base_url}/v3/dataforseo_labs/google/page_intersection/live",
            json.dumps(body).encode("utf-8"),
            self._headers(),
        )

        items = self._extract_items(response)
        keywords: list[DataForSEOPageIntersectionKeyword] = []
        for item in items[:limit]:
            keyword_data = item.get("keyword_data") or {}
            keyword_info = keyword_data.get("keyword_info") or {}
            keywords.append(
                DataForSEOPageIntersectionKeyword(
                    keyword=str(keyword_data.get("keyword") or item.get("keyword") or ""),
                    search_volume=_to_int(keyword_info.get("search_volume")),
                    competition=_to_float(keyword_info.get("competition")),
                    intersection_score=_to_float(
                        item.get("intersection_score") or item.get("relevance")
                    ),
                )
            )
        return keywords

    def _headers(self) -> dict[str, str]:
        credentials = b64encode(f"{self._login}:{self._password}".encode("utf-8")).decode("ascii")
        return {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "LCE-Market-Intelligence/0.1",
        }

    def _extract_items(
        self,
        response: dict[str, Any],
        *,
        purpose: str = "keyword items",
    ) -> list[dict[str, Any]]:
        status_code = response.get("status_code")
        if status_code != 20000:
            raise DataForSEOError(
                f"Unexpected DataForSEO status_code={status_code} message={response.get('status_message')}"
            )

        tasks = response.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            raise DataForSEOError("DataForSEO response did not include tasks.")

        task = tasks[0]
        if task.get("status_code") != 20000:
            raise DataForSEOError(
                f"Unexpected DataForSEO task status_code={task.get('status_code')} message={task.get('status_message')}"
            )

        result = task.get("result")
        if isinstance(result, dict):
            result_entries = [result]
        elif isinstance(result, list) and result:
            result_entries = [entry for entry in result if isinstance(entry, dict)]
        else:
            result_entries = []

        if not result_entries:
            raise DataForSEOError("DataForSEO response did not include result items.")

        if isinstance(task.get("items"), list) and task["items"]:
            return [item for item in task["items"] if isinstance(item, dict)]

        for entry in result_entries:
            items = entry.get("items")
            if isinstance(items, list) and items:
                return [item for item in items if isinstance(item, dict)]

        path = task.get("path")
        data = task.get("data") if isinstance(task.get("data"), dict) else {}
        keywords = data.get("keywords") or data.get("keyword") or data.get("targets")
        items_count = result_entries[0].get("items_count")
        raise DataForSEOError(
            f"DataForSEO returned no {purpose}. "
            f"path={path} keywords={keywords} items_count={items_count}"
        )


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
