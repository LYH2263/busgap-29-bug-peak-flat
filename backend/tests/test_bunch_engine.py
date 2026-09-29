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
