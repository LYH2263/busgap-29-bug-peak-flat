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
    period: str | None = None  # "peak"=本次用高峰尺, "offpeak"=本次用平峰尺, None=未配高峰(底座早期行为)

def classify_gap(gap_min: float, planned_headway_min: float, bunch_threshold: float, large_threshold: float,
                 period: str | None = None) -> tuple[str, str]:
    if gap_min < bunch_threshold:
        return ("bunching", f"间隔 {gap_min:.1f} 分钟低于串车阈值 {bunch_threshold}，建议后车缓行或抽稀。")
    if gap_min > large_threshold:
        return ("large_gap", f"间隔 {gap_min:.1f} 分钟超过大间隔阈值 {large_threshold}，建议前车减速或加发。")
    # 说明里写的峰/平必须等于本次真用的尺子
    if period == "peak":
        plan_text = f"高峰计划 {planned_headway_min:.1f}"
    elif period == "offpeak":
        plan_text = f"平峰计划 {planned_headway_min:.1f}"
    else:
        plan_text = f"计划 {planned_headway_min:.1f}"
    return ("normal", f"间隔接近{plan_text} 分钟，保持即可。")

def _minute_of_day(ts: datetime) -> float:
    return ts.hour * 60 + ts.minute + ts.second / 60.0

def peak_configured(peak_start_min: int | None, peak_end_min: int | None, peak_headway_min: float | None) -> bool:
    return peak_start_min is not None and peak_end_min is not None and peak_headway_min is not None

def _in_peak_window(ts: datetime, peak_start_min: int, peak_end_min: int) -> bool:
    return peak_start_min <= _minute_of_day(ts) < peak_end_min

def effective_headway(prev_ts: datetime, cur_ts: datetime, planned_headway_min: float,
                      peak_start_min: int | None, peak_end_min: int | None,
                      peak_headway_min: float | None) -> tuple[float, str | None]:
    # 未配高峰:与底座早期行为一致,平峰尺、无峰标记
    if not peak_configured(peak_start_min, peak_end_min, peak_headway_min):
        return planned_headway_min, None
    # 双班都落在高峰窗内才拿高峰计划分钟当尺子;任一班落在窗外就拿平峰那把
    if _in_peak_window(prev_ts, peak_start_min, peak_end_min) and \
       _in_peak_window(cur_ts, peak_start_min, peak_end_min):
        return peak_headway_min, "peak"
    return planned_headway_min, "offpeak"

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
            events.append(GapEvent(stop, prev["trip_no"], cur["trip_no"], round(gap_min, 2), headway,
                                   status, suggestion, period))
    return events

def events_to_dicts(events: list[GapEvent]) -> list[dict]:
    return [asdict(e) for e in events]

# topic helpers for report assembly

def peak_banner(period: str | None, headway: float) -> str:
    if period == "peak":
        return f"高峰计划 {headway:.1f}"
    if period == "offpeak":
        return f"平峰计划 {headway:.1f}"
    return f"计划 {headway:.1f}"

def axis_ruler_for_minute(minute: int, peak_start: int | None, peak_end: int | None,
                          peak_headway: float | None = None) -> str:
    # 未配高峰与底座早期一致:轴上没有峰,一律平峰尺
    if peak_start is None or peak_end is None or peak_headway is None:
        return "offpeak"
    if peak_start <= minute < peak_end:
        return "peak"
    return "offpeak"
