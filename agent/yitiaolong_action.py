# -*- coding: utf-8 -*-
"""一条龙步骤 checkbox：按勾选标记编排锚点与首段入口。"""
from __future__ import annotations

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

# (勾选标记节点, 入口节点, 成功结束后锚点名；末段无后继则为 None)
_STAGES: list[tuple[str, str, str | None]] = [
    ("一条龙_勾选_买药", "自动买药", "买药_结束后"),
    ("一条龙_勾选_离开", "离开百业", "离开百业_结束后"),
    ("一条龙_勾选_炼药", "自动炼药", "炼药_结束后"),
    ("一条龙_勾选_买钱", "自动买钱", "钱袋_结束后"),
    ("一条龙_勾选_返回", "返回百业", "回百业_结束后"),
    ("一条龙_勾选_找温", "找温无双", "找温无双_结束后"),
    ("一条龙_勾选_退出", "退出游戏", None),
]

_PREFIX_NEXT = [
    "[JumpBack]公共_关控制器弹窗",
    "[JumpBack]公共_关花瓣叉弹窗",
]


def _enabled_stages(context: Context) -> list[tuple[str, str, str | None]]:
    picked: list[tuple[str, str, str | None]] = []
    for flag, entry, end in _STAGES:
        data = context.get_node_data(flag) or {}
        if data.get("enabled"):
            picked.append((flag, entry, end))
    return picked


@AgentServer.custom_action("一条龙_编排")
class YitiaolongArrange(CustomAction):
    """读各 一条龙_勾选_* enabled，串锚点并 next 到第一段。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        stages = _enabled_stages(context)
        flags = [s[0] for s in stages]
        print(f"[一条龙_编排] enabled={flags}", flush=True)

        anchors: dict[str, str] = {}
        for _, _, end in _STAGES:
            if end:
                anchors[end] = ""

        if not stages:
            print("[一条龙_编排] 未勾选任何步骤 -> 一条龙_收工", flush=True)
            context.override_pipeline({"一条龙": {"anchor": anchors}})
            for name, target in anchors.items():
                context.set_anchor(name, target)
            context.override_next(argv.node_name, _PREFIX_NEXT + ["一条龙_收工"])
            return True

        for i in range(len(stages) - 1):
            _, _, end = stages[i]
            _, next_entry, _ = stages[i + 1]
            if end:
                anchors[end] = next_entry
                print(f"[一条龙_编排] anchor {end} -> {next_entry}", flush=True)

        # 覆盖入口节点的 anchor，避免 JSON 默认全开串线在节点成功时盖掉 set_anchor
        context.override_pipeline({"一条龙": {"anchor": anchors}})
        for name, target in anchors.items():
            context.set_anchor(name, target)

        first_entry = stages[0][1]
        print(f"[一条龙_编排] first -> {first_entry}", flush=True)
        context.override_next(argv.node_name, _PREFIX_NEXT + [first_entry])
        return True
