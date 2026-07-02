"""AI Food Analysis Service using OpenAI Vision"""
import base64
import json
import os
from typing import Optional

import httpx
from openai import OpenAI
from sqlalchemy.orm import Session

from app.models.settings import UserSettings
from app.schemas.food import AIAnalysisResult, FoodItem

ANALYSIS_PROMPT = """Analyze this food image and estimate nutritional information.
Return a JSON object with this exact structure:
{
  "food_items": [
    {
      "name": "food name in Chinese",
      "calories": estimated kcal as integer,
      "portion": "estimated portion (e.g. 1碗, 100g, 1份)",
      "protein_g": grams of protein as number,
      "carbs_g": grams of carbs as number,
      "fat_g": grams of fat as number
    }
  ],
  "total_calories": sum of all items calories,
  "total_protein": sum of protein,
  "total_carbs": sum of carbs,
  "total_fat": sum of fat,
  "analysis_note": "brief analysis in Chinese, including estimation confidence and any notes"
}

Important:
- Estimate calories based on visible portion sizes
- Name foods in Chinese (e.g. 米饭, 红烧肉, 青菜)
- If uncertain about an item, note it in analysis_note
- Be conservative in estimates — slightly overestimate rather than underestimate
- Return ONLY valid JSON, no markdown code blocks
"""


async def analyze_food_image(
    image_path: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> AIAnalysisResult:
    """Analyze a food image using OpenAI Vision and return calorie estimates."""
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    base_url = normalize_base_url(base_url or os.getenv("OPENAI_BASE_URL"))
    model = model or os.getenv("OPENAI_MODEL", "gpt-4o")

    if not api_key:
        # Fallback: mock analysis for demo without API key
        return _mock_analysis()

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=45.0, max_retries=1)

    # Read and encode image
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    # Determine MIME type
    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/jpeg")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": ANALYSIS_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}",
                            "detail": "auto",
                        },
                    },
                ],
            }
        ],
        max_tokens=1000,
        temperature=0.3,  # Lower temperature for more consistent estimates
        timeout=45,
    )

    content = response.choices[0].message.content or "{}"

    # Clean up markdown code blocks if present
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    try:
        data = json.loads(content.strip())
    except json.JSONDecodeError:
        return _mock_analysis(note="AI returned unparseable response, using mock data")

    return AIAnalysisResult(
        food_items=[FoodItem(**item) for item in data.get("food_items", [])],
        total_calories=data.get("total_calories", 0),
        total_protein=data.get("total_protein"),
        total_carbs=data.get("total_carbs"),
        total_fat=data.get("total_fat"),
        analysis_note=data.get("analysis_note"),
    )


def normalize_base_url(base_url: Optional[str]) -> str:
    url = (base_url or "https://api.openai.com/v1").strip().rstrip("/")
    return url or "https://api.openai.com/v1"


def get_ai_settings(db: Session, user_id: int) -> tuple[Optional[str], str, str]:
    settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if not settings:
        return os.getenv("OPENAI_API_KEY"), normalize_base_url(os.getenv("OPENAI_BASE_URL")), os.getenv("OPENAI_MODEL", "gpt-4o")
    return (
        settings.openai_api_key or os.getenv("OPENAI_API_KEY"),
        normalize_base_url(settings.openai_base_url or os.getenv("OPENAI_BASE_URL")),
        settings.openai_model or os.getenv("OPENAI_MODEL", "gpt-4o"),
    )


async def list_models(api_key: str, base_url: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as client:
        res = await client.get(
            f"{normalize_base_url(base_url)}/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        res.raise_for_status()
        data = res.json()
    models = [m.get("id") for m in data.get("data", []) if m.get("id")]
    return {"models": sorted(models)}


async def test_ai_config(api_key: str, base_url: str, model: str) -> dict:
    models = await list_models(api_key, base_url)
    ok = not models["models"] or model in models["models"]
    return {
        "ok": True,
        "message": "连接成功" if ok else f"连接成功，但模型列表中未找到 {model}",
        "models": models["models"],
    }


async def query_balance(api_key: str, base_url: str) -> dict:
    root = normalize_base_url(base_url)
    candidates = [
        f"{root}/dashboard/billing/credit_grants",
        f"{root.replace('/v1', '')}/dashboard/billing/credit_grants",
        f"{root}/user/self",
        f"{root.replace('/v1', '')}/api/user/self",
    ]
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=15) as client:
        for url in dict.fromkeys(candidates):
            try:
                res = await client.get(url, headers=headers)
                if res.status_code == 404:
                    continue
                res.raise_for_status()
                return {"ok": True, "message": "查询成功", "data": res.json()}
            except httpx.HTTPStatusError:
                continue
            except httpx.HTTPError:
                continue
    return {"ok": False, "message": "当前服务商不支持通用余额查询"}


def _mock_analysis(note: Optional[str] = None) -> AIAnalysisResult:
    """Fallback mock analysis for when no API key is configured"""
    return AIAnalysisResult(
        food_items=[
            FoodItem(name="未知食物", calories=300, portion="1份", protein_g=10, carbs_g=30, fat_g=15),
        ],
        total_calories=300,
        total_protein=10,
        total_carbs=30,
        total_fat=15,
        analysis_note=note or "请在设置中配置 OpenAI API Key 以启用AI食物识别功能",
    )
