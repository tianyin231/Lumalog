"""AI Food Analysis API"""
import os
import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.auth import current_user
from app.database import get_db
from app.models.food import FoodRecord
from app.models.user import User
from app.schemas.food import AIAnalysisResult, FoodResponse
from app.upload_paths import upload_dir, upload_url
from app.services.ai_service import (
    analyze_food_image,
    get_ai_settings,
    list_models,
    query_balance,
    test_ai_config,
)

router = APIRouter()


@router.post("/analyze-food", response_model=AIAnalysisResult)
async def analyze_food(
    image: UploadFile = File(...),
    meal_type: str = Form("snack"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Upload food image and get AI calorie analysis"""
    # Validate
    if meal_type not in ("breakfast", "lunch", "dinner", "snack"):
        raise HTTPException(400, "Invalid meal_type")

    # Save image temporarily for analysis
    ext = os.path.splitext(image.filename or ".jpg")[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = upload_dir("food") / filename

    content = await image.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # Call AI analysis
    try:
        api_key, base_url, model = get_ai_settings(db, user.id)
        result = await analyze_food_image(str(filepath), api_key=api_key, base_url=base_url, model=model)
        result.image_path = upload_url("food", filename)
    except Exception as e:
        # Remove temp file on failure
        if filepath.exists():
            filepath.unlink()
        raise HTTPException(500, f"AI analysis failed: {str(e)}")

    return result


@router.post("/analyze-and-save", response_model=FoodResponse, status_code=201)
async def analyze_and_save(
    image: UploadFile = File(...),
    meal_type: str = Form("snack"),
    recorded_at: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Analyze food image AND save as a food record in one step"""
    if meal_type not in ("breakfast", "lunch", "dinner", "snack"):
        raise HTTPException(400, "Invalid meal_type")

    # Save image
    ext = os.path.splitext(image.filename or ".jpg")[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = upload_dir("food") / filename

    content = await image.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # AI analysis
    try:
        api_key, base_url, model = get_ai_settings(db, user.id)
        result = await analyze_food_image(str(filepath), api_key=api_key, base_url=base_url, model=model)
    except Exception as e:
        if filepath.exists():
            filepath.unlink()
        raise HTTPException(500, f"AI analysis failed: {str(e)}")

    # Create food record
    record = FoodRecord(
        user_id=user.id,
        meal_type=meal_type,
        image_path=upload_url("food", filename),
        total_calories=result.total_calories,
        protein_g=result.total_protein,
        carbs_g=result.total_carbs,
        fat_g=result.total_fat,
        note=result.analysis_note,
        recorded_at=datetime.fromisoformat(recorded_at) if recorded_at else datetime.now(),
    )
    record.food_items = [item.model_dump() for item in result.food_items]
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/test")
async def test_ai(db: Session = Depends(get_db), user: User = Depends(current_user)):
    api_key, base_url, model = get_ai_settings(db, user.id)
    if not api_key:
        return {"ok": False, "message": "请先填写 API Key"}
    try:
        return await test_ai_config(api_key, base_url, model)
    except Exception as e:
        return {"ok": False, "message": f"测试失败：{e}"}


@router.get("/models")
async def get_models(db: Session = Depends(get_db), user: User = Depends(current_user)):
    api_key, base_url, _ = get_ai_settings(db, user.id)
    if not api_key:
        return {"models": [], "message": "请先填写 API Key"}
    try:
        return await list_models(api_key, base_url)
    except Exception as e:
        return {"models": [], "message": f"获取模型失败：{e}"}


@router.get("/balance")
async def get_balance(db: Session = Depends(get_db), user: User = Depends(current_user)):
    api_key, base_url, _ = get_ai_settings(db, user.id)
    if not api_key:
        return {"ok": False, "message": "请先填写 API Key"}
    return await query_balance(api_key, base_url)
