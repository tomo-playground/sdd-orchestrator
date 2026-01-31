"""Analytics endpoints for Gemini Auto Edit."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from database import get_db
from models import ActivityLog

router = APIRouter(tags=["analytics"])


@router.get("/analytics/gemini-edits")
async def get_gemini_edit_analytics(
    storyboard_id: int | None = Query(None, description="필터: 특정 스토리보드만"),
    db: Session = Depends(get_db)
):
    """Gemini Auto Edit 분석 데이터

    Before/After Match Rate 비교, 편집 타입별 성공률, 총 비용 등을 조회합니다.

    Args:
        storyboard_id: 특정 스토리보드만 필터링 (optional)

    Returns:
        {
            "total_edits": 15,
            "avg_cost_usd": 0.0404,
            "total_cost_usd": 0.606,
            "avg_improvement": 0.23,
            "edits": [
                {
                    "id": 123,
                    "storyboard_id": 1,
                    "scene_id": 5,
                    "original_match_rate": 0.65,
                    "final_match_rate": 0.88,
                    "improvement": 0.23,
                    "cost_usd": 0.0404,
                    "created_at": "2026-01-31T10:00:00"
                }
            ],
            "by_improvement_range": {
                "0-10%": 2,
                "10-20%": 5,
                "20-30%": 6,
                "30%+": 2
            }
        }
    """
    # Base query
    query = db.query(ActivityLog).filter(ActivityLog.gemini_edited == True)  # noqa: E712

    if storyboard_id:
        query = query.filter(ActivityLog.storyboard_id == storyboard_id)

    edits = query.all()

    # Calculate statistics
    total_edits = len(edits)
    total_cost = sum(e.gemini_cost_usd or 0 for e in edits)
    avg_cost = total_cost / total_edits if total_edits > 0 else 0

    improvements = [
        (e.final_match_rate or 0) - (e.original_match_rate or 0)
        for e in edits
        if e.final_match_rate is not None and e.original_match_rate is not None
    ]
    avg_improvement = sum(improvements) / len(improvements) if improvements else 0

    # Group by improvement range
    by_range = {
        "0-10%": 0,
        "10-20%": 0,
        "20-30%": 0,
        "30%+": 0,
    }
    for imp in improvements:
        imp_pct = imp * 100
        if imp_pct < 10:
            by_range["0-10%"] += 1
        elif imp_pct < 20:
            by_range["10-20%"] += 1
        elif imp_pct < 30:
            by_range["20-30%"] += 1
        else:
            by_range["30%+"] += 1

    # Edit list
    edit_list = [
        {
            "id": e.id,
            "storyboard_id": e.storyboard_id,
            "scene_id": e.scene_id,
            "original_match_rate": e.original_match_rate,
            "final_match_rate": e.final_match_rate,
            "improvement": (e.final_match_rate or 0) - (e.original_match_rate or 0),
            "cost_usd": e.gemini_cost_usd,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in edits
    ]

    return {
        "total_edits": total_edits,
        "avg_cost_usd": round(avg_cost, 4),
        "total_cost_usd": round(total_cost, 4),
        "avg_improvement": round(avg_improvement, 4),
        "edits": edit_list,
        "by_improvement_range": by_range,
    }


@router.get("/analytics/gemini-edits/summary")
async def get_gemini_edit_summary(db: Session = Depends(get_db)):
    """Gemini Auto Edit 요약 통계

    전체 통계를 간단하게 조회합니다.

    Returns:
        {
            "total_edits": 42,
            "total_cost": 1.6968,
            "success_rate": 0.95,
            "avg_improvement": 0.23
        }
    """
    # Total edits
    total_edits = db.query(func.count(ActivityLog.id)).filter(
        ActivityLog.gemini_edited == True  # noqa: E712
    ).scalar() or 0

    # Total cost
    total_cost = db.query(func.sum(ActivityLog.gemini_cost_usd)).filter(
        ActivityLog.gemini_edited == True  # noqa: E712
    ).scalar() or 0.0

    # Success rate (final_match_rate > original_match_rate)
    successful_edits = db.query(func.count(ActivityLog.id)).filter(
        and_(
            ActivityLog.gemini_edited == True,  # noqa: E712
            ActivityLog.final_match_rate.isnot(None),
            ActivityLog.original_match_rate.isnot(None),
            ActivityLog.final_match_rate > ActivityLog.original_match_rate
        )
    ).scalar() or 0

    success_rate = successful_edits / total_edits if total_edits > 0 else 0

    # Average improvement
    improvements = db.query(
        (ActivityLog.final_match_rate - ActivityLog.original_match_rate).label("improvement")
    ).filter(
        and_(
            ActivityLog.gemini_edited == True,  # noqa: E712
            ActivityLog.final_match_rate.isnot(None),
            ActivityLog.original_match_rate.isnot(None),
        )
    ).all()

    avg_improvement = sum(imp.improvement for imp in improvements) / len(improvements) if improvements else 0

    return {
        "total_edits": total_edits,
        "total_cost": round(total_cost, 4),
        "success_rate": round(success_rate, 4),
        "avg_improvement": round(avg_improvement, 4),
    }
