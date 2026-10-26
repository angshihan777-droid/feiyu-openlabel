import pytest

from feiyu_app.biz.challenge.domain import (
    IntervalValidationError,
    anonymize_unit,
    extract_intervals,
    next_reject_state,
    pick_round_robin,
    total_duration,
    validate_intervals,
)


def test_extracts_openlabel_time_ranges_and_skips_removals():
    objects = [
        {
            "id": "a",
            "frame_intervals": [{"time_start": 0, "time_end": 5.2}],
            "attributes": {"label": "抓取"},
        },
        {
            "id": "b",
            "frame_intervals": [{"time_start": 5.2, "time_end": 9.0}],
            "attributes": {"opType": "remove"},
        },
    ]

    assert extract_intervals(objects) == [
        {"start": 0.0, "end": 5.2, "label": "抓取"}
    ]


def test_extracts_taxonomy_category_when_free_text_label_is_absent():
    assert extract_intervals([
        {
            "object_type": "抓取动作",
            "frame_intervals": [{"time_start": 1, "time_end": 2}],
        }
    ]) == [{"start": 1.0, "end": 2.0, "label": "抓取动作"}]


def test_closed_intervals_touch_is_rejected():
    with pytest.raises(IntervalValidationError, match="重叠"):
        validate_intervals(
            [
                {"start": 0, "end": 5},
                {"start": 5, "end": 8},
            ]
        )


def test_rejects_zero_length_out_of_range_and_nan_intervals():
    invalid_cases = [
        [{"start": 1, "end": 1}],
        [{"start": -1, "end": 2}],
        [{"start": 0, "end": 11}],
        [{"start": float("nan"), "end": 2}],
    ]
    for intervals in invalid_cases:
        with pytest.raises(IntervalValidationError):
            validate_intervals(intervals, duration=10)


def test_sums_only_valid_closed_intervals():
    intervals = [
        {"start": 0, "end": 2.5},
        {"start": 3, "end": 7.25},
    ]
    assert total_duration(intervals) == pytest.approx(6.75)


def test_round_robin_is_stable_and_excludes_current_annotator():
    pool = [11, 12, 13]
    assert pick_round_robin(pool, ordinal=0, exclude={11}) == 12
    assert pick_round_robin(pool, ordinal=1, exclude={11}) == 13
    assert pick_round_robin(pool, ordinal=2, exclude={11}) == 12


def test_reject_returns_twice_then_escalates_on_third_reject():
    assert next_reject_state(0) == ("rejected", 1)
    assert next_reject_state(1) == ("rejected", 2)
    assert next_reject_state(2) == ("escalated", 3)


def test_anonymize_hides_counterparty_identity():
    unit = {
        "assignee_id": 7,
        "reviewer_id": 8,
        "annotator_name": "张三",
        "reviewer_name": "李四",
    }
    annotator_view = anonymize_unit(unit, viewer_role="annotator")
    reviewer_view = anonymize_unit(unit, viewer_role="reviewer")

    assert "reviewer_id" not in annotator_view
    assert annotator_view["reviewer_name"] == "匿名"
    assert "assignee_id" not in reviewer_view
    assert reviewer_view["annotator_name"] == "匿名"
