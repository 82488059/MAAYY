"""无限集英 / 无限太极：把界面上的点后等待（秒）换成毫秒 post_delay。"""

import json
import re

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

# 正整数秒。与 interface.json 的 verify 一致，拒绝 0、小数、前导零。
_POSITIVE_SECONDS = re.compile(r"^[1-9][0-9]*$")

JIYING_NODES = ("集英", "集英_OCR")
JIYING_DEFAULT_SECONDS = 11
TAIJI_NODES = ("太极",)
TAIJI_DEFAULT_SECONDS = 20


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


def _positive_seconds(raw):
    """合法正整数秒返回 int，否则 None。bool 不是秒数。"""
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw if raw > 0 else None
    if isinstance(raw, float):
        if raw.is_integer() and raw > 0:
            return int(raw)
        return None
    if isinstance(raw, str) and _POSITIVE_SECONDS.fullmatch(raw.strip()):
        return int(raw.strip())
    return None


def extract_seconds(raw_param):
    """从 custom_action_param 取出 seconds。缺字段或空参数返回 None。"""
    param = _parse_param(raw_param)
    if "seconds" not in param:
        return None
    return param.get("seconds")


def resolve_post_delay_ms(raw, default_seconds: int) -> tuple[int, bool]:
    """秒 → 毫秒。非法值退回 default_seconds。返回 (毫秒, 是否用了默认)。"""
    seconds = _positive_seconds(raw)
    if seconds is None:
        return default_seconds * 1000, True
    return seconds * 1000, False


def build_post_delay_override(nodes, raw_param, default_seconds: int):
    """生成只含 post_delay（毫秒）的覆盖。不把秒写进 post_delay。"""
    raw = extract_seconds(raw_param)
    ms, used_default = resolve_post_delay_ms(raw, default_seconds)
    override = {name: {"post_delay": ms} for name in nodes}
    return override, ms, used_default, raw


def _apply(context: Context, nodes, raw_param, default_seconds: int, label: str) -> bool:
    try:
        override, ms, used_default, raw = build_post_delay_override(
            nodes, raw_param, default_seconds
        )
        if used_default:
            print(
                f"[{label}] 秒数无效 {raw!r}，改用默认 {default_seconds} 秒 → post_delay {ms}"
            )
        else:
            print(f"[{label}] {raw} 秒 → post_delay {ms}，节点 {list(nodes)}")
        ok = context.override_pipeline(override)
        if ok is False:
            print(f"[{label}] override_pipeline 失败，沿用节点里原来的 post_delay")
    except Exception as exc:
        print(f"[{label}] 写入 post_delay 失败: {exc}，沿用节点里原来的 post_delay")
    return True


@AgentServer.custom_action("集英_应用点后等待")
class JiyingApplyPostDelay(CustomAction):
    """入口每次进入时，把齿轮秒数乘 1000，写到「集英」和「集英_OCR」。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        return _apply(
            context,
            JIYING_NODES,
            argv.custom_action_param,
            JIYING_DEFAULT_SECONDS,
            "集英_应用点后等待",
        )


@AgentServer.custom_action("太极_应用点后等待")
class TaijiApplyPostDelay(CustomAction):
    """入口每次进入时，把齿轮秒数乘 1000，写到「太极」。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        return _apply(
            context,
            TAIJI_NODES,
            argv.custom_action_param,
            TAIJI_DEFAULT_SECONDS,
            "太极_应用点后等待",
        )
