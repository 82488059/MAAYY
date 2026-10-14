"""外观上架：反复点价格旁的减号，直到价格不再下降，再交给流水线点寄售。"""

import json

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

from appear_price import choose_price, next_step, price_box_left_point

_state = {"prev": None, "clicks": 0, "box": None}


def _reset() -> None:
    _state["prev"] = None
    _state["clicks"] = 0
    _state["box"] = None


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


def _box_of(result):
    box = getattr(result, "box", None)
    if box is None or len(box) < 4:
        return None
    return [int(box[0]), int(box[1]), int(box[2]), int(box[3])]


def _iter_results(reco):
    if reco is None or not getattr(reco, "hit", False):
        return
    best = getattr(reco, "best_result", None)
    if best is not None:
        yield best
    seen = {id(best)} if best is not None else set()
    for key in ("filterd_results", "filtered_results", "all_results"):
        for result in getattr(reco, key, None) or []:
            if id(result) in seen:
                continue
            seen.add(id(result))
            yield result


def _read_price(context: Context, img):
    price_reco = context.run_recognition("外观_读价格", img)
    label_reco = context.run_recognition("外观_认价格字", img)
    digits = []
    for result in _iter_results(price_reco):
        digits.append((str(getattr(result, "text", "") or ""), _box_of(result)))
    label_box = None
    for result in _iter_results(label_reco):
        label_box = _box_of(result)
        if label_box is not None:
            break
    return choose_price(label_box, digits)


@AgentServer.custom_action("外观_降价重置")
class AppearResetPrice(CustomAction):
    """每次进入降价前清掉上一轮的价格，避免 Agent 进程复用时把旧价当成到底。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        _reset()
        print("[外观_降价重置] 清空上一轮价格")
        return True


@AgentServer.custom_action("外观_降价一步")
class AppearLowerPrice(CustomAction):
    """OCR 价格。与上次相同则改走寄售；否则记下价格，流水线去点减号。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        param = _parse_param(argv.custom_action_param)
        max_clicks = int(param.get("max_clicks", 40))
        img = context.tasker.controller.post_screencap().wait().get()
        price, box = _read_price(context, img)
        decision = next_step(_state["prev"], price, _state["clicks"], max_clicks)
        print(
            f"[外观_降价一步] price={price} prev={_state['prev']} "
            f"clicks={_state['clicks']} max={max_clicks} -> {decision}"
        )
        if decision == "consign":
            _reset()
            context.override_next(argv.node_name, ["外观_点寄售"])
            return True
        if decision == "fail":
            _reset()
            context.override_next(argv.node_name, ["外观_降价失败"])
            return True
        if price is not None:
            _state["prev"] = price
        if box is not None:
            _state["box"] = box
        _state["clicks"] += 1
        return True


@AgentServer.custom_action("外观_点价格左侧")
class AppearClickLeftOfPrice(CustomAction):
    """减号字形没认到时，点价格数字框左侧。点出面板 ROI 则失败，不点寄售。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        point = price_box_left_point(_state.get("box"))
        print(f"[外观_点价格左侧] box={_state.get('box')} point={point}")
        if point is None:
            _reset()
            context.override_next(argv.node_name, ["外观_降价失败"])
            return True
        context.tasker.controller.post_click(point[0], point[1]).wait()
        return True
