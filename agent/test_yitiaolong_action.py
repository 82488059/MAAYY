# -*- coding: utf-8 -*-
"""一条龙_编排：勾选标记 → 锚点串与首段。"""
from __future__ import annotations

import types
import unittest
from unittest.mock import MagicMock


def _load():
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    # stub maa if missing in some envs
    try:
        import yitiaolong_action as mod
    except ModuleNotFoundError:
        maa = types.ModuleType("maa")
        sys.modules["maa"] = maa
        for name in ("agent", "agent.agent_server", "context", "custom_action"):
            parts = name.split(".")
            cur = "maa"
            parent = maa
            for p in parts:
                cur = f"{cur}.{p}" if cur != "maa" else f"maa.{p}"
                if cur not in sys.modules:
                    m = types.ModuleType(cur)
                    sys.modules[cur] = m
                    setattr(parent, p.split(".")[-1] if False else p, m)
                    parent = m
                else:
                    parent = sys.modules[cur]

        class AgentServer:
            @staticmethod
            def custom_action(name):
                def deco(cls):
                    cls._caa_name = name
                    return cls

                return deco

        class CustomAction:
            class RunArg:
                pass

        sys.modules["maa.agent.agent_server"].AgentServer = AgentServer
        sys.modules["maa.custom_action"].CustomAction = CustomAction
        sys.modules["maa.context"].Context = object
        import importlib

        import yitiaolong_action as mod

        importlib.reload(mod)
    return mod


class TestYitiaolongArrange(unittest.TestCase):
    def test_all_enabled_chains_anchors(self):
        mod = _load()
        ctx = MagicMock()

        def get_node_data(name):
            if name.startswith("一条龙_勾选_"):
                return {"enabled": True}
            return {}

        ctx.get_node_data.side_effect = get_node_data
        argv = MagicMock()
        argv.node_name = "一条龙"
        ok = mod.YitiaolongArrange().run(ctx, argv)
        self.assertTrue(ok)
        # first next includes popups + 自动买药
        next_arg = ctx.override_next.call_args[0][1]
        self.assertEqual(next_arg[-1], "自动买药")
        self.assertIn("[JumpBack]公共_关花瓣叉弹窗", next_arg)
        # sample anchors
        set_calls = {c.args[0]: c.args[1] for c in ctx.set_anchor.call_args_list}
        self.assertEqual(set_calls.get("买药_结束后"), "离开百业")
        self.assertEqual(set_calls.get("找温无双_结束后"), "退出游戏")
        self.assertEqual(set_calls.get("钱袋_结束后"), "返回百业")

    def test_skip_middle(self):
        mod = _load()
        ctx = MagicMock()
        enabled = {"一条龙_勾选_买药", "一条龙_勾选_炼药", "一条龙_勾选_退出"}

        def get_node_data(name):
            return {"enabled": name in enabled}

        ctx.get_node_data.side_effect = get_node_data
        argv = MagicMock()
        argv.node_name = "一条龙"
        mod.YitiaolongArrange().run(ctx, argv)
        set_calls = {c.args[0]: c.args[1] for c in ctx.set_anchor.call_args_list}
        self.assertEqual(set_calls.get("买药_结束后"), "自动炼药")
        self.assertEqual(set_calls.get("炼药_结束后"), "退出游戏")
        self.assertEqual(set_calls.get("离开百业_结束后"), "")
        next_arg = ctx.override_next.call_args[0][1]
        self.assertEqual(next_arg[-1], "自动买药")

    def test_none_enabled(self):
        mod = _load()
        ctx = MagicMock()
        ctx.get_node_data.return_value = {"enabled": False}
        argv = MagicMock()
        argv.node_name = "一条龙"
        mod.YitiaolongArrange().run(ctx, argv)
        next_arg = ctx.override_next.call_args[0][1]
        self.assertEqual(next_arg[-1], "一条龙_收工")


if __name__ == "__main__":
    unittest.main()
