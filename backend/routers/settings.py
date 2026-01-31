"""Settings management endpoints."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from config import (
    GEMINI_AUTO_EDIT_ENABLED,
    GEMINI_AUTO_EDIT_MAX_COST_PER_STORYBOARD,
    GEMINI_AUTO_EDIT_MAX_RETRIES_PER_SCENE,
    GEMINI_AUTO_EDIT_THRESHOLD,
    logger,
)
from database import get_db
from models import ActivityLog

router = APIRouter(tags=["settings"])


class AutoEditSettingsUpdate(BaseModel):
    """Auto Edit 설정 업데이트 요청"""
    enabled: bool
    threshold: float
    max_cost: float
    max_retries: int


@router.get("/settings/auto-edit")
async def get_auto_edit_settings():
    """현재 Gemini Auto Edit 설정 조회

    Returns:
        {
            "enabled": False,
            "threshold": 0.7,
            "max_cost_per_storyboard": 1.0,
            "max_retries_per_scene": 1
        }
    """
    return {
        "enabled": GEMINI_AUTO_EDIT_ENABLED,
        "threshold": GEMINI_AUTO_EDIT_THRESHOLD,
        "max_cost_per_storyboard": GEMINI_AUTO_EDIT_MAX_COST_PER_STORYBOARD,
        "max_retries_per_scene": GEMINI_AUTO_EDIT_MAX_RETRIES_PER_SCENE,
    }


@router.put("/settings/auto-edit")
async def update_auto_edit_settings(settings: AutoEditSettingsUpdate):
    """Gemini Auto Edit 설정 업데이트 (런타임)

    주의: 이 엔드포인트는 런타임 설정을 업데이트합니다.
    서버 재시작 시 .env 파일의 값으로 초기화됩니다.

    영구적인 변경을 원하면 .env 파일을 직접 수정하세요:
    - GEMINI_AUTO_EDIT_ENABLED=true
    - GEMINI_AUTO_EDIT_THRESHOLD=0.7
    - GEMINI_AUTO_EDIT_MAX_COST=1.0
    - GEMINI_AUTO_EDIT_MAX_RETRIES=1

    Args:
        enabled: 자동 편집 활성화 여부
        threshold: Match Rate 임계값 (0.0~1.0)
        max_cost: 스토리보드당 최대 비용 (USD)
        max_retries: 씬당 최대 재시도 횟수

    Returns:
        {
            "success": True,
            "message": "Runtime settings updated. Restart required for persistence."
        }
    """
    import config

    # Update runtime config
    config.GEMINI_AUTO_EDIT_ENABLED = settings.enabled
    config.GEMINI_AUTO_EDIT_THRESHOLD = settings.threshold
    config.GEMINI_AUTO_EDIT_MAX_COST_PER_STORYBOARD = settings.max_cost
    config.GEMINI_AUTO_EDIT_MAX_RETRIES_PER_SCENE = settings.max_retries

    logger.info(
        f"⚙️ [Settings] Auto Edit updated: enabled={settings.enabled}, "
        f"threshold={settings.threshold}, max_cost=${settings.max_cost}, max_retries={settings.max_retries}"
    )

    return {
        "success": True,
        "message": "Runtime settings updated. Restart required for persistence.",
        "current": {
            "enabled": settings.enabled,
            "threshold": settings.threshold,
            "max_cost": settings.max_cost,
            "max_retries": settings.max_retries,
        }
    }


@router.get("/settings/auto-edit/cost-summary")
async def get_auto_edit_cost_summary(db: Session = Depends(get_db)):
    """Gemini Auto Edit 비용 요약

    Returns:
        {
            "today": 0.12,
            "this_week": 0.45,
            "this_month": 1.23,
            "total": 5.67,
            "edit_count_today": 3,
            "edit_count_month": 31
        }
    """
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)

    # Today
    today_cost = db.query(func.sum(ActivityLog.gemini_cost_usd)).filter(
        ActivityLog.gemini_edited == True,  # noqa: E712
        ActivityLog.created_at >= today_start
    ).scalar() or 0.0

    today_count = db.query(func.count(ActivityLog.id)).filter(
        ActivityLog.gemini_edited == True,  # noqa: E712
        ActivityLog.created_at >= today_start
    ).scalar() or 0

    # This week
    week_cost = db.query(func.sum(ActivityLog.gemini_cost_usd)).filter(
        ActivityLog.gemini_edited == True,  # noqa: E712
        ActivityLog.created_at >= week_start
    ).scalar() or 0.0

    # This month
    month_cost = db.query(func.sum(ActivityLog.gemini_cost_usd)).filter(
        ActivityLog.gemini_edited == True,  # noqa: E712
        ActivityLog.created_at >= month_start
    ).scalar() or 0.0

    month_count = db.query(func.count(ActivityLog.id)).filter(
        ActivityLog.gemini_edited == True,  # noqa: E712
        ActivityLog.created_at >= month_start
    ).scalar() or 0

    # Total
    total_cost = db.query(func.sum(ActivityLog.gemini_cost_usd)).filter(
        ActivityLog.gemini_edited == True  # noqa: E712
    ).scalar() or 0.0

    return {
        "today": round(today_cost, 4),
        "this_week": round(week_cost, 4),
        "this_month": round(month_cost, 4),
        "total": round(total_cost, 4),
        "edit_count_today": today_count,
        "edit_count_month": month_count,
    }
