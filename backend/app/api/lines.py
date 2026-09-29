from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Line
router = APIRouter(prefix="/lines", tags=["lines"])

class LineUpdate(BaseModel):
    planned_headway_min: float | None = None
    bunch_threshold: float | None = None
    large_threshold: float | None = None
    peak_start_min: int | None = None
    peak_end_min: int | None = None
    peak_headway_min: float | None = None

def line_dict(r: Line) -> dict:
    return {"id": r.id, "code": r.code, "name": r.name, "planned_headway_min": r.planned_headway_min,
            "bunch_threshold": r.bunch_threshold, "large_threshold": r.large_threshold,
            "peak_start_min": r.peak_start_min, "peak_end_min": r.peak_end_min,
            "peak_headway_min": r.peak_headway_min}

@router.get("")
def list_lines(db: Session = Depends(get_db)):
    rows = db.scalars(select(Line).order_by(Line.id)).all()
    return [line_dict(r) for r in rows]

@router.put("/{line_id}")
def update_line(line_id: int, body: LineUpdate, db: Session = Depends(get_db)):
    line = db.get(Line, line_id)
    if not line: raise HTTPException(404, "线路不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(line, k, v)
    for field in ("planned_headway_min", "bunch_threshold", "large_threshold"):
        if getattr(line, field) <= 0:
            raise HTTPException(400, "计划间隔与阈值需大于 0")
    peak = (line.peak_start_min, line.peak_end_min, line.peak_headway_min)
    if any(v is not None for v in peak) and not all(v is not None for v in peak):
        raise HTTPException(400, "高峰起止分钟与高峰间隔需同时配置或同时留空")
    if all(v is not None for v in peak):
        if not (0 <= line.peak_start_min < line.peak_end_min <= 1440):
            raise HTTPException(400, "高峰时段需满足 0 ≤ 起 < 止 ≤ 1440 分钟")
        if line.peak_headway_min <= 0:
            raise HTTPException(400, "高峰计划间隔需大于 0")
    db.commit(); db.refresh(line)
    return line_dict(line)
