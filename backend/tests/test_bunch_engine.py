from datetime import datetime, timedelta
from app.services.bunch_engine import classify_gap, detect_bunching, effective_headway

def test_classify_bunching():
    assert classify_gap(2.0, 8.0, 3.0, 15.0)[0] == "bunching"

def test_classify_large():
    assert classify_gap(16.0, 8.0, 3.0, 15.0)[0] == "large_gap"

def test_classify_normal():
    assert classify_gap(8.0, 8.0, 3.0, 15.0)[0] == "normal"

def test_detect_bunching_events():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=2)},
        {"stop_name": "A", "trip_no": "T3", "actual_arrive": base + timedelta(minutes=20)},
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    assert len(events) == 2
    assert events[0].status == "bunching"
    assert events[1].status == "large_gap"

# --- 峰平峰计划间隔 ---

def test_normal_text_unchanged_without_peak():
    assert classify_gap(8.0, 8.0, 3.0, 15.0)[1] == "间隔接近计划 8.0 分钟，保持即可。"

def test_normal_text_names_peak_and_offpeak():
    assert "高峰计划 5.0" in classify_gap(5.0, 5.0, 3.0, 15.0, period="peak")[1]
    assert "平峰计划 8.0" in classify_gap(8.0, 8.0, 3.0, 15.0, period="offpeak")[1]

def test_effective_headway_both_in_peak():
    base = datetime(2026, 1, 1, 8, 0)  # 高峰 7:00-9:00 = 420-540
    headway, period = effective_headway(base, base + timedelta(minutes=6), 8.0, 420, 540, 5.0)
    assert (headway, period) == (5.0, "peak")

def test_effective_headway_mixed_pair_uses_offpeak():
    prev = datetime(2026, 1, 1, 8, 55)   # 高峰内
    cur = datetime(2026, 1, 1, 9, 10)    # 高峰外
    headway, period = effective_headway(prev, cur, 8.0, 420, 540, 5.0)
    assert (headway, period) == (8.0, "offpeak")

def test_effective_headway_window_bounds():
    start = datetime(2026, 1, 1, 7, 0)   # 起点分钟算高峰内
    end = datetime(2026, 1, 1, 9, 0)     # 止点分钟算高峰外
    assert effective_headway(start, start + timedelta(minutes=5), 8.0, 420, 540, 5.0)[1] == "peak"
    assert effective_headway(end - timedelta(minutes=5), end, 8.0, 420, 540, 5.0)[1] == "offpeak"

def test_effective_headway_not_configured():
    headway, period = effective_headway(datetime(2026, 1, 1, 8, 0), datetime(2026, 1, 1, 8, 6),
                                        8.0, None, None, None)
    assert (headway, period) == (8.0, None)

def test_detect_bunching_with_peak_config():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=6)},
        {"stop_name": "A", "trip_no": "T3", "actual_arrive": base + timedelta(minutes=180)},  # 11:00 平峰
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, peak_start_min=420, peak_end_min=540, peak_headway_min=5.0)
    assert events[0].planned_headway_min == 5.0
    assert "高峰计划" in events[0].suggestion
    assert events[1].planned_headway_min == 8.0
    assert events[1].status == "large_gap"

# --- 双班都在峰窗才用峰尺;落在窗外(含跨窗)用平峰尺 ---

def test_effective_headway_both_outside_uses_offpeak():
    base = datetime(2026, 1, 1, 12, 0)  # 午间平峰
    headway, period = effective_headway(base, base + timedelta(minutes=8), 8.0, 420, 540, 5.0)
    assert (headway, period) == (8.0, "offpeak")

def test_detect_pair_outside_window_uses_offpeak_ruler_text():
    base = datetime(2026, 1, 1, 12, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=8)},
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, peak_start_min=420, peak_end_min=540, peak_headway_min=5.0)
    assert events[0].period == "offpeak"
    assert events[0].planned_headway_min == 8.0
    assert "平峰计划 8.0" in events[0].suggestion
    assert "高峰计划" not in events[0].suggestion  # 写峰却按平峰算=互斥失败

def test_detect_crossing_window_pair_uses_offpeak_ruler():
    prev = datetime(2026, 1, 1, 8, 55)
    cur = datetime(2026, 1, 1, 9, 10)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": prev},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": cur},
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, peak_start_min=420, peak_end_min=540, peak_headway_min=5.0)
    assert events[0].period == "offpeak"
    assert events[0].planned_headway_min == 8.0

def test_peak_event_text_and_ruler_are_consistent():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=5)},
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, peak_start_min=420, peak_end_min=540, peak_headway_min=5.0)
    assert events[0].period == "peak"
    assert events[0].planned_headway_min == 5.0
    assert "高峰计划 5.0" in events[0].suggestion
    assert "平峰计划" not in events[0].suggestion

def test_detect_without_peak_config_matches_early_base_behavior():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=8)},
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    assert events[0].period is None
    assert events[0].planned_headway_min == 8.0
    assert "间隔接近计划 8.0" in events[0].suggestion

def test_threshold_fields_still_drive_status():
    # 串车阈/大间隔阈/计划间隔含义不变:峰窗内串车与大间隔仍只看两个阈值
    base = datetime(2026, 1, 1, 8, 0)
    bunch = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=2)},
    ]
    large = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=20)},
    ]
    kw = dict(peak_start_min=420, peak_end_min=540, peak_headway_min=5.0)
    assert detect_bunching(bunch, 8.0, 3.0, 15.0, **kw)[0].status == "bunching"
    assert detect_bunching(large, 8.0, 3.0, 15.0, **kw)[0].status == "large_gap"
