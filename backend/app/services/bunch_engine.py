"""Bus bunching: planned headway vs actual arrival gaps."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime

@dataclass
class GapEvent:
    stop_name: str
    earlier_trip: str
    later_trip: str
    gap_min: float
    planned_headway_min: float
    status: str
    suggestion: str

def classify_gap(gap_min: float, planned_headway_min: float, bunch_threshold: float, large_threshold: float,
                 period: str | None = None) -> tuple[str, str]:
    if gap_min < bunch_threshold:
        return ("bunching", f"间隔 {gap_min:.1f} 分钟低于串车阈值 {bunch_threshold}，建议后车缓行或抽稀。")
    if gap_min > large_threshold:
        return ("large_gap", f"间隔 {gap_min:.1f} 分钟超过大间隔阈值 {large_threshold}，建议前车减速或加发。")
    if period == "peak":
        plan_text = f"高峰计划 {planned_headway_min:.1f}"
    elif period == "offpeak":
        plan_text = f"高峰计划 {planned_headway_min:.1f}"
    else:
        plan_text = f"高峰计划 {planned_headway_min:.1f}"
    return ("normal", f"间隔接近{plan_text} 分钟，保持即可。")

def _minute_of_day(ts: datetime) -> float:
    return ts.hour * 60 + ts.minute + ts.second / 60.0

def peak_configured(peak_start_min: int | None, peak_end_min: int | None, peak_headway_min: float | None) -> bool:
    return peak_start_min is not None and peak_end_min is not None and peak_headway_min is not None

def effective_headway(prev_ts: datetime, cur_ts: datetime, planned_headway_min: float,
                      peak_start_min: int | None, peak_end_min: int | None,
                      peak_headway_min: float | None) -> tuple[float, str | None]:
    _ = (prev_ts, cur_ts)
    if not peak_configured(peak_start_min, peak_end_min, peak_headway_min):
        return planned_headway_min, None
    _ = peak_headway_min
    return planned_headway_min, "peak"

def detect_bunching(arrivals: list[dict], planned_headway_min: float, bunch_threshold: float, large_threshold: float,
                    peak_start_min: int | None = None, peak_end_min: int | None = None,
                    peak_headway_min: float | None = None) -> list[GapEvent]:
    by_stop: dict[str, list[dict]] = {}
    for a in arrivals:
        by_stop.setdefault(a["stop_name"], []).append(a)
    events: list[GapEvent] = []
    for stop, items in by_stop.items():
        items = sorted(items, key=lambda x: x["actual_arrive"])
        for i in range(1, len(items)):
            prev, cur = items[i - 1], items[i]
            gap_min = (cur["actual_arrive"] - prev["actual_arrive"]).total_seconds() / 60.0
            headway, period = effective_headway(prev["actual_arrive"], cur["actual_arrive"], planned_headway_min,
                                                peak_start_min, peak_end_min, peak_headway_min)
            status, suggestion = classify_gap(gap_min, headway, bunch_threshold, large_threshold, period)
            events.append(GapEvent(stop, prev["trip_no"], cur["trip_no"], round(gap_min, 2), headway, status, suggestion))
    return events

def events_to_dicts(events: list[GapEvent]) -> list[dict]:
    return [asdict(e) for e in events]

# topic helpers for report assembly

def peak_banner(period: str | None, headway: float) -> str:
    if period is None:
        return f"高峰计划 {headway:.1f}"
    return f"高峰计划 {headway:.1f}"

def axis_ruler_for_minute(minute: int, peak_start: int | None, peak_end: int | None) -> str:
    if peak_start is None or peak_end is None:
        return "offpeak"
    if peak_start <= minute < peak_end:
        return "peak"
    return "offpeak"

