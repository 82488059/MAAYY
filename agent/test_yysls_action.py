"""集英 / 太极点后等待：秒 → 毫秒 post_delay。不依赖已安装的 maafw。"""

import sys
import types
import unittest


def _install_maa_stubs() -> None:
    if "maa.custom_action" in sys.modules:
        return

    maa = types.ModuleType("maa")
    agent = types.ModuleType("maa.agent")
    agent_server = types.ModuleType("maa.agent.agent_server")
    custom_action = types.ModuleType("maa.custom_action")
    context_mod = types.ModuleType("maa.context")

    class AgentServer:
        @staticmethod
        def custom_action(_name):
            def deco(cls):
                return cls

            return deco

    class CustomAction:
        class RunArg:
            pass

    class Context:
        pass

    agent_server.AgentServer = AgentServer
    custom_action.CustomAction = CustomAction
    context_mod.Context = Context
    agent.agent_server = agent_server
    maa.agent = agent
    maa.custom_action = custom_action
    maa.context = context_mod
    sys.modules["maa"] = maa
    sys.modules["maa.agent"] = agent
    sys.modules["maa.agent.agent_server"] = agent_server
    sys.modules["maa.custom_action"] = custom_action
    sys.modules["maa.context"] = context_mod


_install_maa_stubs()

from yysls_action import (  # noqa: E402
    JIYING_DEFAULT_SECONDS,
    JIYING_NODES,
    TAIJI_DEFAULT_SECONDS,
    TAIJI_NODES,
    JiyingApplyPostDelay,
    TaijiApplyPostDelay,
    build_post_delay_override,
    resolve_post_delay_ms,
)


class _Arg:
    def __init__(self, param):
        self.custom_action_param = param
        self.node_name = "entry"


class _Context:
    def __init__(self, ok=True):
        self.ok = ok
        self.override = None

    def override_pipeline(self, data):
        self.override = data
        return self.ok


class ResolvePostDelayTests(unittest.TestCase):
    def test_defaults_are_milliseconds(self):
        self.assertEqual(resolve_post_delay_ms(11, 11), (11000, False))
        self.assertEqual(resolve_post_delay_ms(20, 20), (20000, False))
        self.assertEqual(resolve_post_delay_ms("11", 11), (11000, False))

    def test_invalid_falls_back_to_default_seconds(self):
        for raw in (None, "", "0", 0, -3, 1.5, True, False, "abc", "{集英点后等待秒}", "01", "  "):
            ms, used_default = resolve_post_delay_ms(raw, 11)
            self.assertEqual(ms, 11000, raw)
            self.assertTrue(used_default, raw)
        ms, used_default = resolve_post_delay_ms(None, 20)
        self.assertEqual((ms, used_default), (20000, True))

    def test_override_targets_click_nodes_in_milliseconds(self):
        override, ms, used_default, raw = build_post_delay_override(
            JIYING_NODES, {"seconds": 5}, JIYING_DEFAULT_SECONDS
        )
        self.assertEqual(raw, 5)
        self.assertFalse(used_default)
        self.assertEqual(ms, 5000)
        self.assertEqual(
            override,
            {"集英": {"post_delay": 5000}, "集英_OCR": {"post_delay": 5000}},
        )
        self.assertEqual(set(override["集英"]), {"post_delay"})
        self.assertEqual(override["集英"]["post_delay"], 5000)

    def test_missing_seconds_uses_task_default(self):
        override, ms, used_default, _raw = build_post_delay_override(
            TAIJI_NODES, {}, TAIJI_DEFAULT_SECONDS
        )
        self.assertTrue(used_default)
        self.assertEqual(ms, 20000)
        self.assertEqual(override, {"太极": {"post_delay": 20000}})

    def test_json_string_param(self):
        override, ms, used_default, _raw = build_post_delay_override(
            JIYING_NODES, '{"seconds": 8}', JIYING_DEFAULT_SECONDS
        )
        self.assertFalse(used_default)
        self.assertEqual(ms, 8000)
        self.assertEqual(override["集英"]["post_delay"], 8000)
        self.assertEqual(override["集英_OCR"]["post_delay"], 8000)

    def test_actions_apply_and_keep_running(self):
        jiying = _Context()
        self.assertTrue(JiyingApplyPostDelay().run(jiying, _Arg({"seconds": 3})))
        self.assertEqual(jiying.override["集英"]["post_delay"], 3000)
        self.assertEqual(jiying.override["集英_OCR"]["post_delay"], 3000)

        taiji = _Context()
        self.assertTrue(TaijiApplyPostDelay().run(taiji, _Arg({"seconds": "9"})))
        self.assertEqual(taiji.override, {"太极": {"post_delay": 9000}})

        bad = _Context()
        self.assertTrue(JiyingApplyPostDelay().run(bad, _Arg({"seconds": ""})))
        self.assertEqual(bad.override["集英"]["post_delay"], 11000)

        failed = _Context(ok=False)
        self.assertTrue(TaijiApplyPostDelay().run(failed, _Arg({"seconds": 4})))
        self.assertEqual(failed.override["太极"]["post_delay"], 4000)

        class _Boom:
            def override_pipeline(self, _data):
                raise RuntimeError("boom")

        self.assertTrue(JiyingApplyPostDelay().run(_Boom(), _Arg({"seconds": 6})))


if __name__ == "__main__":
    unittest.main()
