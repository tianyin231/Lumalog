"""Mi Fitness integration backed by the local mi-fitness-sync package."""
from __future__ import annotations

import uuid
from html import escape
from dataclasses import asdict, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlparse
import re

from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import Response
from fastapi.responses import RedirectResponse

from app.models.exercise import ExerciseActivityDetail, ExerciseRecord
from mi_fitness_sync.activity.client import MiFitnessActivitiesClient
from mi_fitness_sync.activity.models import Activity, ActivityDetail
from mi_fitness_sync.auth.client import DEFAULT_SERVICE_ID, MetaLoginData, MiFitnessAuthClient
from mi_fitness_sync.auth.state import AuthState, utc_now_iso
from mi_fitness_sync.auth.store import delete_state, load_state, resolve_state_path, save_state
from mi_fitness_sync.exceptions import (
    AuthStateNotFoundError,
    CaptchaRequiredError,
    MiFitnessError,
    NotificationRequiredError,
    Step2RequiredError,
    XiaomiApiError,
)


PENDING_LOGINS: dict[str, dict[str, Any]] = {}
MI_FIT_STATE_DIR = Path("data/mi_fit")
HTML_ATTR_RE = re.compile(r'(?P<attr>\b(?:href|src|action)=)(?P<quote>["\'])(?P<url>[^"\']+)(?P=quote)', re.IGNORECASE)


def get_mi_fit_status(app_user_id: int) -> dict[str, Any]:
    state_path = resolve_state_path(_state_path(app_user_id))
    state = load_state(_state_path(app_user_id))
    return {
        "authenticated": state is not None,
        "email": state.email if state else None,
        "user_id": state.user_id if state else None,
        "updated_at": state.updated_at if state else None,
        "state_path": str(state_path),
    }


def logout_mi_fit(app_user_id: int) -> dict[str, Any]:
    path = delete_state(_state_path(app_user_id))
    _clear_pending_logins(app_user_id)
    return {"ok": True, "message": "已退出小米运动健康", "state_path": str(path)}


def import_mi_fit_auth_state(app_user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    required = ("email", "user_id", "c_user_id", "service_token", "ssecurity", "cookies")
    missing = [key for key in required if not payload.get(key)]
    if missing:
        return {"ok": False, "message": f"登录状态文件缺少字段：{', '.join(missing)}"}

    try:
        state = AuthState(**payload)
    except Exception as exc:
        return {"ok": False, "message": f"登录状态文件格式不正确：{exc}"}

    state = replace(state, updated_at=utc_now_iso())
    path = save_state(state, _state_path(app_user_id))
    state = _normalize_health_service_token(app_user_id, state)
    _clear_pending_logins(app_user_id)
    return {
        "ok": True,
        "message": "小米登录状态已导入",
        "email": state.email,
        "state_path": str(path),
    }


def start_mi_fit_login(app_user_id: int, email: str, password: str) -> dict[str, Any]:
    _clear_pending_logins(app_user_id)
    existing_state = load_state(_state_path(app_user_id))
    device_id = existing_state.device_id if existing_state else MiFitnessAuthClient.generate_device_id()
    client = MiFitnessAuthClient(service_id=DEFAULT_SERVICE_ID, trust_env=False)
    meta = client._get_meta_login_data(email=email, device_id=device_id)
    return _try_password_login(
        app_user_id=app_user_id,
        client=client,
        email=email,
        password=password,
        device_id=device_id,
        meta=meta,
        existing_created_at=existing_state.created_at if existing_state else None,
        open_browser=False,
    )


def continue_mi_fit_login(
    app_user_id: int,
    session_id: str,
    cookies: list[dict[str, object]] | None = None,
) -> dict[str, Any]:
    pending = PENDING_LOGINS.get(session_id)
    if not pending:
        status = get_mi_fit_status(app_user_id)
        if status["authenticated"]:
            return {
                "ok": True,
                "status": "authenticated",
                "message": "小米运动健康登录成功",
                "email": status["email"],
                "state_path": status["state_path"],
            }
        return {
            "ok": False,
            "status": "expired",
            "message": "登录会话已过期，请重新开始登录",
        }
    if pending.get("app_user_id") != app_user_id:
        return {
            "ok": False,
            "status": "expired",
            "message": "登录会话不属于当前账号，请重新开始登录",
        }

    if cookies:
        _merge_manual_browser_cookies(pending, cookies)
    elif pending.get("context"):
        _merge_pending_browser_cookies(pending)
    return _try_password_login(
        app_user_id=app_user_id,
        client=pending["client"],
        email=pending["email"],
        password=pending["password"],
        device_id=pending["device_id"],
        meta=pending["meta"],
        existing_created_at=pending.get("existing_created_at"),
        session_id=session_id,
        open_browser=False,
    )


def proxy_mi_fit_verification(
    session_id: str,
    key: str,
    target: str | None,
    method: str,
    headers: dict[str, str],
    body: bytes,
) -> Response:
    pending = PENDING_LOGINS.get(session_id)
    if not pending or pending.get("proxy_key") != key:
        return _verification_error_page(
            "验证会话已过期",
            "请回到设置页重新点击“登录小米”。如果服务使用了多个后端进程，请先改成单进程运行后再试。",
        )

    target_url = target or pending.get("verification_url")
    if not isinstance(target_url, str) or not _is_allowed_verification_url(target_url):
        return _verification_error_page("验证地址不允许代理", "请重新开始小米登录。")

    client = pending["client"]
    request_headers = _proxy_request_headers(headers)
    try:
        upstream = client.session.request(
            method,
            target_url,
            headers=request_headers,
            data=body if method.upper() not in {"GET", "HEAD"} else None,
            allow_redirects=False,
            timeout=30,
        )
    except Exception as exc:
        return _verification_error_page("验证页代理失败", str(exc))

    if upstream.is_redirect or upstream.is_permanent_redirect:
        location = upstream.headers.get("location")
        if not location:
            return Response(status_code=upstream.status_code)
        next_url = urljoin(target_url, location)
        if not _is_allowed_verification_url(next_url):
            return _verification_error_page("验证跳转地址不允许代理", next_url)
        return RedirectResponse(_verification_proxy_url(session_id, key, next_url), status_code=302)

    content_type = upstream.headers.get("content-type", "text/html; charset=utf-8")
    content = upstream.content
    if "text/html" in content_type.lower():
        text = upstream.text
        content = _rewrite_verification_html(text, target_url, session_id, key).encode(upstream.encoding or "utf-8")
        content_type = "text/html; charset=utf-8"

    response = Response(content=content, status_code=upstream.status_code, media_type=content_type)
    for name in ("cache-control", "pragma", "expires"):
        value = upstream.headers.get(name)
        if value:
            response.headers[name] = value
    return response


def get_mi_fit_login_browser_status(app_user_id: int, session_id: str) -> dict[str, Any]:
    pending = PENDING_LOGINS.get(session_id)
    if not pending or pending.get("app_user_id") != app_user_id:
        status = get_mi_fit_status(app_user_id)
        if status["authenticated"]:
            return {"ok": True, "status": "authenticated", "message": "小米运动健康登录成功"}
        return {"ok": False, "status": "expired", "message": "登录会话已过期，请重新开始登录"}

    page = pending.get("page")
    if not page:
        return {"ok": True, "status": "manual", "message": "请完成验证后手动确认"}

    try:
        text = page.locator("body").inner_text(timeout=1000).strip().lower()
    except Exception:
        return {"ok": True, "status": "pending", "message": "等待小米验证完成"}

    if text in {"ok", "success"} or any(marker in text for marker in ("验证成功", "验证通过", "已完成")):
        return {"ok": True, "status": "completed", "message": "验证已完成，正在读取凭证"}
    return {"ok": True, "status": "pending", "message": "等待小米验证完成"}


def list_mi_fit_activities(
    db: Session,
    user_id: int,
    *,
    days: int = 30,
    limit: int = 50,
) -> dict[str, Any]:
    client = _activities_client(user_id)
    end_time = int(datetime.now().timestamp())
    start_time = int((datetime.now() - timedelta(days=days)).timestamp())
    activities = client.list_activities(start_time=start_time, end_time=end_time, limit=limit)
    imported_ids = _imported_source_ids(db, user_id)
    return {
        "ok": True,
        "days": days,
        "limit": limit,
        "activities": [_activity_payload(a, a.activity_id in imported_ids) for a in activities],
    }


def import_mi_fit_activities(db: Session, user_id: int, activity_ids: list[str]) -> dict[str, Any]:
    client = _activities_client(user_id)
    imported = 0
    skipped = 0
    failed: list[dict[str, str]] = []

    for activity_id in activity_ids:
        try:
            with db.begin_nested():
                detail = client.get_activity_detail(activity_id)
                result = _save_activity_detail(db, user_id, detail)
            if result == "imported":
                imported += 1
            else:
                skipped += 1
        except Exception as exc:
            failed.append({"activity_id": activity_id, "message": str(exc)})

    db.commit()
    return {
        "ok": not failed,
        "imported": imported,
        "skipped": skipped,
        "failed": failed,
        "message": f"导入完成：新增 {imported} 条，跳过 {skipped} 条，失败 {len(failed)} 条",
    }


def sync_mi_fit_data(db: Session, user_id: int, days: int = 30, limit: int = 100) -> dict[str, Any]:
    listed = list_mi_fit_activities(db, user_id, days=days, limit=limit)
    activity_ids = [a["activity_id"] for a in listed["activities"] if not a["imported"]]
    result = import_mi_fit_activities(db, user_id, activity_ids)
    result["scanned"] = len(listed["activities"])
    result["days"] = days
    return result


def backfill_mi_fit_details(db: Session, user_id: int) -> dict[str, Any]:
    client = _activities_client(user_id)
    records = db.execute(
        select(ExerciseRecord).where(
            ExerciseRecord.user_id == user_id,
            ExerciseRecord.source == "mi_fit",
            ExerciseRecord.source_id.is_not(None),
        )
    ).scalars().all()

    imported = 0
    skipped = 0
    failed: list[dict[str, str]] = []
    for record in records:
        has_detail = db.execute(
            select(ExerciseActivityDetail.id).where(
                ExerciseActivityDetail.user_id == user_id,
                ExerciseActivityDetail.source == "mi_fit",
                ExerciseActivityDetail.source_id == record.source_id,
            )
        ).scalar_one_or_none()
        if has_detail:
            skipped += 1
            continue
        try:
            with db.begin_nested():
                detail = client.get_activity_detail(record.source_id)
                _save_detail_payload(db, record, detail)
            imported += 1
        except Exception as exc:
            failed.append({"source_id": record.source_id or "", "message": str(exc)})

    db.commit()
    return {
        "ok": not failed,
        "imported": imported,
        "skipped": skipped,
        "failed": failed,
        "message": f"补拉完成：新增详情 {imported} 条，跳过 {skipped} 条，失败 {len(failed)} 条",
    }


async def test_mi_fit_connection(db: Session, user_id: int) -> dict[str, Any]:
    status = get_mi_fit_status(user_id)
    if not status["authenticated"]:
        return {"ok": False, "message": "尚未登录小米运动健康"}
    try:
        listed = list_mi_fit_activities(db, user_id, days=30, limit=10)
    except Exception as exc:
        return {"ok": False, "message": f"连接失败：{exc}"}
    return {"ok": True, "message": f"连接成功，读取到 {len(listed['activities'])} 条最近运动"}


def _try_password_login(
    *,
    app_user_id: int,
    client: MiFitnessAuthClient,
    email: str,
    password: str,
    device_id: str,
    meta: MetaLoginData,
    existing_created_at: str | None,
    session_id: str | None = None,
    open_browser: bool = True,
) -> dict[str, Any]:
    try:
        session = client.login_with_password(
            email=email,
            password=password,
            device_id=device_id,
            meta=meta,
        )
    except NotificationRequiredError as exc:
        login_id = session_id or uuid.uuid4().hex
        pending = PENDING_LOGINS.setdefault(login_id, {})
        proxy_key = pending.setdefault("proxy_key", uuid.uuid4().hex)
        pending.update(
            {
                "client": client,
                "app_user_id": app_user_id,
                "email": email,
                "password": password,
                "device_id": device_id,
                "meta": meta,
                "existing_created_at": existing_created_at,
                "verification_url": exc.notification_url,
            }
        )
        opened = _open_verification_browser(pending, exc.notification_url) if open_browser else False
        message = (
            "小米要求二次验证，请在后端弹出的临时浏览器窗口完成验证，不要使用普通浏览器打开"
            if opened
            else "小米要求二次验证，请打开验证页完成验证，然后点击“我已完成验证”"
        )
        if session_id and not open_browser:
            message = "验证还未完成；如果普通重试失败，可以粘贴验证后的 Cookie 再确认"
        return {
            "ok": False,
            "status": "verification_required",
            "session_id": login_id,
            "verification_url": exc.notification_url,
            "verification_proxy_url": _verification_proxy_url(login_id, str(proxy_key), None),
            "opened_browser": opened,
            "message": message,
        }
    except Step2RequiredError as exc:
        return {
            "ok": False,
            "status": "step2_required",
            "message": str(exc),
        }
    except CaptchaRequiredError as exc:
        return {
            "ok": False,
            "status": "captcha_required",
            "captcha_url": exc.captcha_url,
            "message": "小米要求验证码，请先使用命令行登录一次完成验证码流程",
        }
    except (XiaomiApiError, MiFitnessError) as exc:
        return {"ok": False, "status": "failed", "message": str(exc)}

    state = session.to_auth_state()
    if existing_created_at:
        state = replace(state, created_at=existing_created_at, updated_at=utc_now_iso())
    path = save_state(state, _state_path(app_user_id))
    if session_id:
        _close_pending_browser(PENDING_LOGINS.pop(session_id, {}))
    return {
        "ok": True,
        "status": "authenticated",
        "message": "小米运动健康登录成功",
        "email": state.email,
        "state_path": str(path),
    }


def _activities_client(user_id: int) -> MiFitnessActivitiesClient:
    state = load_state(_state_path(user_id))
    if state is None:
        raise AuthStateNotFoundError("尚未登录小米运动健康")
    state = _normalize_health_service_token(user_id, state)
    return MiFitnessActivitiesClient(state, trust_env=False)


def _state_path(app_user_id: int) -> str:
    return str((MI_FIT_STATE_DIR / f"user_{app_user_id}.json").resolve())


def _clear_pending_logins(app_user_id: int) -> None:
    for session_id, pending in list(PENDING_LOGINS.items()):
        if pending.get("app_user_id") == app_user_id:
            _close_pending_browser(PENDING_LOGINS.pop(session_id, {}))


def _verification_proxy_url(session_id: str, key: str, target: str | None) -> str:
    url = f"/api/mi-fit/login/proxy/{session_id}?key={quote(key)}"
    if target:
        url += f"&target={quote(target, safe='')}"
    return url


def _is_allowed_verification_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.hostname or ""
    return host == "mi.com" or host.endswith(".mi.com") or host == "xiaomi.com" or host.endswith(".xiaomi.com")


def _proxy_request_headers(headers: dict[str, str]) -> dict[str, str]:
    blocked = {"host", "cookie", "content-length", "authorization", "connection", "accept-encoding"}
    return {key: value for key, value in headers.items() if key.lower() not in blocked}


def _rewrite_verification_html(html: str, base_url: str, session_id: str, key: str) -> str:
    def replace_attr(match: re.Match[str]) -> str:
        raw_url = match.group("url").strip()
        if not raw_url or raw_url.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
            return match.group(0)
        next_url = urljoin(base_url, raw_url)
        if not _is_allowed_verification_url(next_url):
            return match.group(0)
        return f'{match.group("attr")}{match.group("quote")}{_verification_proxy_url(session_id, key, next_url)}{match.group("quote")}'

    rewritten = HTML_ATTR_RE.sub(replace_attr, html)
    parsed = urlparse(base_url)
    browser_path = parsed.path or "/"
    if parsed.query:
        browser_path += f"?{parsed.query}"
    if parsed.fragment:
        browser_path += f"#{parsed.fragment}"
    shim = (
        "<script>"
        f"history.replaceState(null, '', {browser_path!r});"
        "</script>"
    )
    rewritten = rewritten.replace("<head>", f"<head>{shim}", 1)
    rewritten = rewritten.replace("</head>", '<base href="/"></head>', 1)
    return rewritten


def _verification_error_page(title: str, detail: str) -> Response:
    safe_title = escape(title)
    safe_detail = escape(detail)
    html = f"""
    <!doctype html>
    <html lang="zh-CN">
      <head>
        <meta charset="utf-8" />
        <title>{safe_title}</title>
        <style>
          body {{ font-family: system-ui, sans-serif; padding: 32px; line-height: 1.6; color: #10201f; }}
          main {{ max-width: 680px; margin: 0 auto; }}
          code {{ overflow-wrap: anywhere; }}
        </style>
      </head>
      <body>
        <main>
          <h1>{safe_title}</h1>
          <p>{safe_detail}</p>
          <p>处理后请关闭这个页面，回到 Lumalog 设置页继续。</p>
        </main>
      </body>
    </html>
    """
    return Response(html, status_code=200, media_type="text/html; charset=utf-8")


def _normalize_health_service_token(app_user_id: int, state: Any) -> Any:
    for cookie in reversed(state.cookies):
        if cookie.get("name") != "serviceToken":
            continue
        domain = cookie.get("domain")
        if isinstance(domain, str) and "sts-hlth.io.mi.com" in domain:
            token = cookie.get("value")
            if isinstance(token, str) and token and token != state.service_token:
                state = replace(state, service_token=token, updated_at=utc_now_iso())
                save_state(state, _state_path(app_user_id))
            break
    return state


def _imported_source_ids(db: Session, user_id: int) -> set[str]:
    rows = db.execute(
        select(ExerciseRecord.source_id).where(
            ExerciseRecord.user_id == user_id,
            ExerciseRecord.source == "mi_fit",
            ExerciseRecord.source_id.is_not(None),
        )
    ).all()
    return {row[0] for row in rows if row[0]}


def _activity_payload(activity: Activity, imported: bool) -> dict[str, Any]:
    payload = activity.to_json_dict()
    payload["imported"] = imported
    return payload


def _save_activity_detail(db: Session, user_id: int, detail: ActivityDetail) -> str:
    source_id = detail.activity.activity_id
    record = db.execute(
        select(ExerciseRecord).where(
            ExerciseRecord.user_id == user_id,
            ExerciseRecord.source == "mi_fit",
            ExerciseRecord.source_id == source_id,
        )
    ).scalar_one_or_none()
    if record:
        _save_detail_payload(db, record, detail)
        return "skipped"

    record = ExerciseRecord(
        user_id=user_id,
        exercise_type=_exercise_type(detail.activity.sport_type, detail.activity.category),
        duration_minutes=max(0, round(detail.total_duration_seconds / 60)),
        calories_burned=max(0, detail.total_calories or 0),
        steps=detail.activity.steps or _max_sample_value(detail.samples, "steps"),
        distance_km=round(detail.total_distance_meters / 1000, 2) if detail.total_distance_meters else None,
        avg_heart_rate=_average_heart_rate(detail),
        source="mi_fit",
        source_id=source_id,
        note=detail.activity.title or "小米运动健康同步",
        recorded_at=datetime.fromtimestamp(detail.start_time),
    )
    db.add(record)
    db.flush()
    _save_detail_payload(db, record, detail)
    return "imported"


def _save_detail_payload(db: Session, record: ExerciseRecord, detail: ActivityDetail) -> None:
    payload = detail.to_json_dict()
    existing = db.execute(
        select(ExerciseActivityDetail).where(
            ExerciseActivityDetail.user_id == record.user_id,
            ExerciseActivityDetail.source == "mi_fit",
            ExerciseActivityDetail.source_id == record.source_id,
        )
    ).scalar_one_or_none()
    values = {
        "exercise_record_id": record.id,
        "user_id": record.user_id,
        "source": "mi_fit",
        "source_id": record.source_id or detail.activity.activity_id,
        "track_points_json": payload["track_points"],
        "samples_json": payload["samples"],
        "raw_report_json": detail.activity.raw_report,
        "raw_detail_json": payload["raw_detail"],
        "sport_report_json": asdict(detail.sport_report) if detail.sport_report else None,
        "recovery_rate_json": asdict(detail.recovery_rate) if detail.recovery_rate else None,
    }
    if existing:
        for key, value in values.items():
            setattr(existing, key, value)
        return
    db.add(ExerciseActivityDetail(**values))


def _exercise_type(sport_type: int | None, category: str | None) -> str:
    if sport_type in {1, 3, 5}:
        return "run"
    if sport_type in {2, 4, 15, 207, 333}:
        return "walk"
    if sport_type in {6, 7, 206, 324}:
        return "cycle"
    if sport_type in {9, 10}:
        return "swim"
    if sport_type == 12:
        return "yoga"
    if sport_type in {8, 11, 13, 14, 16, 303, 308, 313, 314, 315, 330, 500}:
        return "gym"
    if category and "swim" in category.lower():
        return "swim"
    return "other"


def _average_heart_rate(detail: ActivityDetail) -> int | None:
    values = [p.heart_rate for p in detail.track_points if p.heart_rate]
    if not values:
        values = [s.heart_rate for s in detail.samples if s.heart_rate]
    if not values:
        return None
    return round(sum(values) / len(values))


def _max_sample_value(samples: list[Any], attr: str) -> int | None:
    values = [getattr(sample, attr) for sample in samples if getattr(sample, attr, None)]
    return max(values) if values else None


def _open_verification_browser(pending: dict[str, Any], verification_url: str) -> bool:
    playwright = None
    context = None
    try:
        from mi_fitness_sync.cli.app import _requests_cookies_for_playwright
        from playwright.sync_api import sync_playwright

        playwright = sync_playwright().start()
        parsed = urlparse(verification_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        context = _launch_persistent_system_context(playwright, pending["app_user_id"])
        context.add_cookies(_requests_cookies_for_playwright(pending["client"], origin))
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(verification_url, wait_until="domcontentloaded")
        pending.update({"playwright": playwright, "context": context, "page": page})
        return True
    except Exception:
        pending["browser_error"] = "后端临时浏览器启动失败，请确认已安装 Playwright Python 包和系统 Chrome/Edge，并重启后端；不需要安装 Playwright 自带 Chromium"
        try:
            if context:
                context.close()
        finally:
            if playwright:
                playwright.stop()
        return False


def _launch_persistent_system_context(playwright: Any, app_user_id: int) -> Any:
    user_data_dir = (MI_FIT_STATE_DIR / "browser_profiles" / f"user_{app_user_id}").resolve()
    user_data_dir.mkdir(parents=True, exist_ok=True)
    for channel in ("chrome", "msedge"):
        try:
            return playwright.chromium.launch_persistent_context(
                str(user_data_dir),
                channel=channel,
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception:
            continue
    raise RuntimeError("no system Chrome or Edge available")


def _merge_pending_browser_cookies(pending: dict[str, Any]) -> None:
    context = pending.get("context")
    if not context:
        return
    try:
        from mi_fitness_sync.cli.app import _merge_playwright_cookies

        _merge_playwright_cookies(pending["client"], context.cookies())
    except Exception:
        return


def _merge_manual_browser_cookies(pending: dict[str, Any], cookies: list[dict[str, object]]) -> None:
    try:
        from mi_fitness_sync.cli.app import _merge_playwright_cookies

        _merge_playwright_cookies(pending["client"], cookies)
    except Exception:
        return


def _close_pending_browser(pending: dict[str, Any]) -> None:
    browser = pending.get("browser")
    context = pending.get("context")
    playwright = pending.get("playwright")
    try:
        if context:
            context.close()
        if browser:
            browser.close()
    finally:
        if playwright:
            playwright.stop()
