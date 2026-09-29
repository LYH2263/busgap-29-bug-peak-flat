import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Arrival, BunchReport, Line, Trip
from app.services.bunch_engine import detect_bunching, effective_headway, events_to_dicts, peak_configured
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
    # 每次检测都按库里当前的高峰窗/高峰计划现选尺子,改配置后重检不吃改前的尺子
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

def _peak_band_pct(t0: datetime, span: float, peak_start_min: int, peak_end_min: int) -> dict | None:
    """把墙上时间的高峰窗映射到时间轴百分比,色带与真用的峰窗对齐。"""
    day0 = t0.replace(hour=0, minute=0, second=0, microsecond=0)
    start_sec = (day0 - t0).total_seconds() + peak_start_min * 60
    end_sec = (day0 - t0).total_seconds() + peak_end_min * 60
    lo = max(0.0, start_sec)
    hi = min(span, end_sec)
    if hi <= lo:
        return None
    return {"start_pct": round(lo / span * 100, 2), "end_pct": round(hi / span * 100, 2)}

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
    planned = line.planned_headway_min if line else None
    has_peak = peak_configured(peak_start, peak_end, peak_headway)
    marks = []
    for i, a in enumerate(arrivals):
        minute = a.actual_arrive.hour * 60 + a.actual_arrive.minute
        in_band = bool(has_peak and peak_start <= minute < peak_end)
        # ruler 与串车报告同源:双班都落在峰窗内的那个间隔才是高峰尺;
        # 首班没有前车可配成一对、或未配高峰时,不标注 pair 尺子
        if has_peak and i >= 1:
            _, period = effective_headway(arrivals[i - 1].actual_arrive, a.actual_arrive,
                                          line.planned_headway_min, peak_start, peak_end, peak_headway)
            ruler = period
        else:
            ruler = None
        marks.append({
            "trip_no": trip_no_map[a.trip_id],
            "actual_arrive": a.actual_arrive.isoformat(),
            "pct": round((a.actual_arrive - t0).total_seconds() / span * 100, 2),
            "in_peak": in_band,
            "ruler": ruler,
        })
    peak_band = _peak_band_pct(t0, span, peak_start, peak_end) if has_peak else None
    return {"stop_name": stop_name, "marks": flatten_marks(marks),
            "peak_configured": has_peak,
            "peak_start_min": peak_start, "peak_end_min": peak_end,
            "peak_headway_min": peak_headway, "planned_headway_min": planned,
            "peak_band": peak_band}
