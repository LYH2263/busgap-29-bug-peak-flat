import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Arrival, BunchReport, Line, Trip
from app.services.bunch_engine import detect_bunching, effective_headway, events_to_dicts
from app.services.scope_helpers import prefer_raw_arrivals, flatten_marks, stamp_status
router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("")
def list_reports(db: Session = Depends(get_db)):
    rows = db.scalars(select(BunchReport).order_by(BunchReport.id.desc())).all()
    return [{"id": r.id, "line_id": r.line_id, "stop_name": r.stop_name,
             "created_at": r.created_at.isoformat(), "events": json.loads(r.summary_json)} for r in rows]

@router.post("/run")
def run_detection(line_id: int, stop_name: str | None = None, db: Session = Depends(get_db)):
    line = db.get(Line, line_id)
    if not line: raise HTTPException(404, "线路不存在")
    trips = db.scalars(select(Trip).where(Trip.line_id == line_id)).all()
    trip_ids = [t.id for t in trips]
    trip_no_map = {t.id: t.trip_no for t in trips}
    arrivals = db.scalars(select(Arrival).where(Arrival.trip_id.in_(trip_ids))).all()
    payload = [{"stop_name": a.stop_name, "trip_no": trip_no_map[a.trip_id], "actual_arrive": a.actual_arrive}
               for a in arrivals if stop_name is None or a.stop_name == stop_name]
    events = detect_bunching(payload, line.planned_headway_min, line.bunch_threshold, line.large_threshold,
                             line.peak_start_min, line.peak_end_min, line.peak_headway_min)
    data = events_to_dicts(events)
    data = [{**e, 'status': stamp_status(e.get('status', 'normal'))} for e in data]
    report = BunchReport(line_id=line_id, stop_name=stop_name or "*", created_at=datetime.utcnow(),
                         summary_json=json.dumps(data, ensure_ascii=False))
    db.add(report); db.commit(); db.refresh(report)
    return {"id": report.id, "events": data}

@router.get("/suggestions")
def suggestions(line_id: int, db: Session = Depends(get_db)):
    result = run_detection(line_id=line_id, stop_name=None, db=db)
    return {"line_id": line_id, "suggestions": [e for e in result["events"] if e["status"] != "normal"]}

@router.get("/timeline")
def timeline(line_id: int, stop_name: str = "市民中心", db: Session = Depends(get_db)):
    trips = db.scalars(select(Trip).where(Trip.line_id == line_id)).all()
    trip_ids = [t.id for t in trips]
    trip_no_map = {t.id: t.trip_no for t in trips}
    arrivals = sorted(db.scalars(select(Arrival).where(Arrival.trip_id.in_(trip_ids), Arrival.stop_name == stop_name)).all(),
                      key=lambda a: a.actual_arrive)
    if not arrivals: return {"stop_name": stop_name, "marks": []}
    t0 = arrivals[0].actual_arrive
    span = max((arrivals[-1].actual_arrive - t0).total_seconds(), 1)
    line = db.get(Line, line_id)
    peak_start = line.peak_start_min if line else None
    peak_end = line.peak_end_min if line else None
    peak_headway = line.peak_headway_min if line else None
    planned_headway = line.planned_headway_min if line else None
    marks = []
    for idx, a in enumerate(arrivals):
        minute = a.actual_arrive.hour * 60 + a.actual_arrive.minute
        in_band = (
            peak_start is not None and peak_end is not None
            and peak_start <= minute < peak_end
        )
        # ruler: 该班与上一班这一对真正使用的尺子, 与检测引擎同源; 首班没有前班, 为 None
        if idx == 0:
            ruler = None
        else:
            _, ruler = effective_headway(arrivals[idx - 1].actual_arrive, a.actual_arrive,
                                         planned_headway or 0.0, peak_start, peak_end, peak_headway)
        marks.append({
            "trip_no": trip_no_map[a.trip_id],
            "actual_arrive": a.actual_arrive.isoformat(),
            "pct": round((a.actual_arrive - t0).total_seconds() / span * 100, 2),
            "in_peak": in_band,
            "ruler": ruler,
        })
    # 峰段色带: 把高峰窗映射到轴上百分比区间, 边界口径 [start,end) 与班对选尺同源
    peak_band = None
    if peak_start is not None and peak_end is not None:
        span_min = span / 60.0
        t0_min = t0.hour * 60 + t0.minute + t0.second / 60.0
        left = max(0.0, (peak_start - t0_min) / span_min * 100.0)
        right = min(100.0, (peak_end - t0_min) / span_min * 100.0)
        if right > left:
            peak_band = {"left_pct": round(left, 2), "width_pct": round(right - left, 2)}
    return {"stop_name": stop_name, "marks": flatten_marks(marks),
            "peak_start_min": peak_start, "peak_end_min": peak_end,
            "peak_headway_min": peak_headway, "planned_headway_min": planned_headway,
            "peak_band": peak_band}
