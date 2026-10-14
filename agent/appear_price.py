"""外观上架降价判定。不依赖 maa，方便单独核对。"""

import re

# 与流水线里价格 / 寄售面板 ROI 一致：右下 [640, 420, 620, 280]
PANEL_ROI = (640, 420, 620, 280)

_PRICE = re.compile(r"(\d[\d,，]*)")


def parse_price(text: str):
    """从 OCR 文本取出价格整数。千分位逗号去掉。没有数字则返回 None。"""
    if not text:
        return None
    compact = str(text).replace(" ", "").replace("\u00a0", "")
    matched = _PRICE.search(compact)
    if not matched:
        return None
    digits = matched.group(1).replace(",", "").replace("，", "")
    if not digits.isdigit():
        return None
    return int(digits)


def next_step(prev, price, clicks: int, max_clicks: int) -> str:
    """点过减号之后，连续两次读到同一个价 → consign。

    次数用尽仍对不上同一个价 → fail，调用方不得点寄售。
    其余 → minus。
    """
    if price is not None and prev is not None and price == prev:
        return "consign"
    if clicks >= max_clicks:
        return "fail"
    return "minus"


def choose_price(label_box, digit_hits):
    """在数字框里挑价格。优先「价格」二字右侧、同一行最近的一格。"""
    parsed = []
    for text, box in digit_hits:
        value = parse_price(text)
        if value is None or box is None or len(box) < 4:
            continue
        parsed.append((value, box))
    if not parsed:
        return None, None
    if label_box is not None and len(label_box) >= 4:
        lx = label_box[0] + label_box[2] / 2
        ly = label_box[1] + label_box[3] / 2
        right = []
        for value, box in parsed:
            cx = box[0] + box[2] / 2
            cy = box[1] + box[3] / 2
            if cx >= lx and abs(cy - ly) <= 80:
                right.append((cx - lx, value, box))
        if right:
            right.sort(key=lambda item: item[0])
            _, value, box = right[0]
            return value, box
    value, box = max(parsed, key=lambda item: item[1][2] * item[1][3])
    return value, box


def price_box_left_point(box, panel=PANEL_ROI, gap: int = 32):
    """价格数字框左侧一点，当作减号。点出面板 ROI 则返回 None。"""
    if box is None or len(box) < 4:
        return None
    x = int(box[0] - gap)
    y = int(box[1] + box[3] / 2)
    px, py, pw, ph = panel
    if x < px or x >= px + pw or y < py or y >= py + ph:
        return None
    return x, y
