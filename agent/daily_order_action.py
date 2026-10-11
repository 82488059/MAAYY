# -*- coding: utf-8 -*-
"""每日号令：点刷新后用卡内标签名判断是否刷成功。"""
from __future__ import annotations

import json
import time

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

# 与业火焚身相对 refresh_yehuo 同构（见 docs/zh_cn/tasks/每日号令.md）
_TITLE_OFFSET = (-200, 24, 130, 42)
_SKIP = {"单人", "多人", "特殊", "公"}
_RF_ROI = [100, 230, 1150, 320]
_RF_THR = 0.88


def _parse_param(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        loaded = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    if isinstance(loaded, str):
        try:
            loaded = json.loads(loaded)
        except json.JSONDecodeError:
            return {}
    return loaded if isinstance(loaded, dict) else {}


def _box(reco):
    if reco is None or not getattr(reco, "hit", False):
        return None
    best = getattr(reco, "best_result", None)
    if best is not None and getattr(best, "box", None) is not None:
        return list(best.box)
    if getattr(reco, "box", None) is not None:
        return list(reco.box)
    return None


def _title_roi(box):
    x, y, _, _ = box
    dx, dy, tw, th = _TITLE_OFFSET
    return [max(0, x + dx), max(0, y + dy), tw, th]


def _pick_title(reco) -> str:
    if reco is None:
        return ""
    texts = []
    best = getattr(reco, "best_result", None)
    if best is not None and getattr(best, "text", None):
        texts.append(str(best.text).strip())
    for key in ("filtered_results", "filterd_results", "all_results"):
        for item in getattr(reco, key, None) or []:
            t = str(getattr(item, "text", "") or "").strip()
            if t and t not in texts:
                texts.append(t)
    for t in texts:
        if t in _SKIP or len(t) < 2:
            continue
        return t
    return ""


def _screencap(context: Context):
    return context.tasker.controller.post_screencap().wait().get()


@AgentServer.custom_action("号令_点刷新验标签")
class DailyOrderClickRefreshVerifyTitle(CustomAction):
    """找 Vertical index 刷新 → OCR 标签 → 点击 → 再 OCR；标签名变化视为成功。

    找不到该档刷新返回 False（走 on_error）。点了但标签未变会重试一次，仍不变仍返回 True 以免卡死后续档位。
    """

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        param = _parse_param(argv.custom_action_param)
        index = int(param.get("index", 0))

        context.override_pipeline(
            {
                "号令_找刷新": {
                    "recognition": "TemplateMatch",
                    "template": "daily_order/refresh_user.png",
                    "roi": _RF_ROI,
                    "threshold": _RF_THR,
                    "order_by": "Vertical",
                    "index": index,
                    "action": "DoNothing",
                }
            }
        )

        img = _screencap(context)
        rf = context.run_recognition("号令_找刷新", img)
        box = _box(rf)
        if box is None:
            print(f"[号令_点刷新验标签] index={index} 无刷新")
            return False

        roi = _title_roi(box)
        context.override_pipeline(
            {
                "号令_读刷新标签": {
                    "recognition": "OCR",
                    "expected": [".*"],
                    "roi": roi,
                    "threshold": 0.35,
                    "action": "DoNothing",
                }
            }
        )
        before = _pick_title(context.run_recognition("号令_读刷新标签", img))
        cx = box[0] + box[2] // 2
        cy = box[1] + box[3] // 2
        print(
            f"[号令_点刷新验标签] index={index} box={box} "
            f"title_roi={roi} before={before!r} click=({cx},{cy})"
        )

        for attempt in range(2):
            context.tasker.controller.post_click(cx, cy).wait()
            time.sleep(0.9)
            img2 = _screencap(context)
            after = _pick_title(context.run_recognition("号令_读刷新标签", img2))
            changed = bool(before) and bool(after) and before != after
            print(
                f"[号令_点刷新验标签] index={index} attempt={attempt} "
                f"{before!r} -> {after!r} changed={changed}"
            )
            if changed:
                return True
            if after and not before:
                # 点前 OCR 空、点后有字，也算推进
                return True
            if before and not after:
                before = before  # keep; retry click
                continue
            if before and after and before == after and attempt == 0:
                continue
            break

        # 有刷新并已点过：不因验签失败阻断后续档位
        print(f"[号令_点刷新验标签] index={index} 验签未通过，仍继续下一档")
        return True
