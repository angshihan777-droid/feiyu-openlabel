"""Pure domain rules for the multi-tenant video annotation challenge.

The user selected closed intervals: [start, end]. Two intervals overlap when
``previous.end >= next.start``. Keeping these rules independent from HTTP and
ORM code makes the business contract deterministic and directly testable.
"""

from __future__ import annotations

import math
from typing import Iterable, Mapping, Sequence

MAX_REJECTS = 2
ESCALATE_ON_REJECT = MAX_REJECTS + 1


class IntervalValidationError(ValueError):
    """Raised when an interval payload violates the annotation contract."""


def _to_seconds(value: object) -> float:
    if isinstance(value, bool):
        raise IntervalValidationError("时间必须是数字")
    try:
        seconds = float(value)
    except (TypeError, ValueError) as exc:
        raise IntervalValidationError("时间必须是数字") from exc
    if not math.isfinite(seconds):
        raise IntervalValidationError("时间必须是有限数字")
    return seconds


def _label_from_object(obj: Mapping) -> str | None:
    attributes = obj.get("attributes") or {}
    if isinstance(attributes, Mapping):
        for key in ("label", "name", "value", "action"):
            value = attributes.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    value = obj.get("label") or obj.get("object_type")
    if not isinstance(value, str):
        value = obj.get("ol_type_")
    return value.strip() if isinstance(value, str) and value.strip() else None


def extract_intervals(objects: Iterable[Mapping]) -> list[dict]:
    """Convert OpenLABEL-style label objects into canonical intervals."""
    intervals: list[dict] = []
    for obj in objects or []:
        attributes = obj.get("attributes") or {}
        if isinstance(attributes, Mapping) and attributes.get("opType") == "remove":
            continue
        ranges = obj.get("frame_intervals")
        if ranges is None and "start" in obj and "end" in obj:
            ranges = [obj]
        if not isinstance(ranges, Sequence):
            continue
        for frame_range in ranges:
            if not isinstance(frame_range, Mapping):
                continue
            start = frame_range.get("time_start", frame_range.get("start"))
            end = frame_range.get("time_end", frame_range.get("end"))
            if start is None or end is None:
                continue
            interval = {"start": _to_seconds(start), "end": _to_seconds(end)}
            label = _label_from_object(obj)
            if label:
                interval["label"] = label
            intervals.append(interval)
    return intervals


def validate_intervals(
    intervals: Iterable[Mapping],
    *,
    duration: float | None = None,
) -> list[dict]:
    """Validate and return normalized closed intervals."""
    normalized: list[dict] = []
    limit = _to_seconds(duration) if duration is not None else None
    if limit is not None and limit <= 0:
        raise IntervalValidationError("视频时长必须大于 0")

    for raw in intervals or []:
        if not isinstance(raw, Mapping):
            raise IntervalValidationError("区间必须是对象")
        start = _to_seconds(raw.get("start"))
        end = _to_seconds(raw.get("end"))
        if start < 0:
            raise IntervalValidationError("区间起点不能小于 0")
        if end <= start:
            raise IntervalValidationError("区间结束时间必须大于开始时间")
        if limit is not None and end > limit:
            raise IntervalValidationError("区间超出视频时长")
        item = {"start": start, "end": end}
        label = raw.get("label")
        if isinstance(label, str) and label.strip():
            item["label"] = label.strip()
        normalized.append(item)

    if not normalized:
        raise IntervalValidationError("至少需要一个有效区间")

    normalized.sort(key=lambda item: (item["start"], item["end"]))
    for previous, current in zip(normalized, normalized[1:]):
        if previous["end"] >= current["start"]:
            raise IntervalValidationError(
                f"区间重叠: [{previous['start']:g}, {previous['end']:g}] "
                f"与 [{current['start']:g}, {current['end']:g}]"
            )
    return normalized


def total_duration(intervals: Iterable[Mapping]) -> float:
    total = 0.0
    for interval in intervals:
        total += _to_seconds(interval["end"]) - _to_seconds(interval["start"])
    return total


def pick_round_robin(
    pool: Sequence[int],
    *,
    ordinal: int,
    exclude: Iterable[int] = (),
) -> int | None:
    """Pick by stable rotation after removing ineligible users."""
    excluded = set(exclude)
    eligible = [int(user_id) for user_id in pool if int(user_id) not in excluded]
    if not eligible:
        return None
    return eligible[max(0, int(ordinal)) % len(eligible)]


def next_reject_state(reject_count: int) -> tuple[str, int]:
    """Return status and new count; the third reject escalates to admin."""
    new_count = max(0, int(reject_count)) + 1
    if new_count >= ESCALATE_ON_REJECT:
        return "escalated", new_count
    return "rejected", new_count


def anonymize_unit(unit: Mapping, *, viewer_role: str) -> dict:
    """Hide the counterparty identity while preserving workflow metadata."""
    result = dict(unit)
    if viewer_role == "annotator":
        result.pop("reviewer_id", None)
        result["reviewer_name"] = "匿名" if result.get("reviewer_name") else None
    elif viewer_role == "reviewer":
        result.pop("assignee_id", None)
        result["annotator_name"] = "匿名"
    return result
