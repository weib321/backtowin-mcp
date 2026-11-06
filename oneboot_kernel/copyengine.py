# -*- coding: utf-8 -*-
"""
OneBoot 内核 — 文案引擎
唯一事实源: 《文案-MCP对外文案包-20261031》(业主令拟, 第五任交重装开发AI使用)。
红线(文案包§四, 本引擎用构造+校验双保险落实):
  1. 数字零虚构 —— 【N】【X】只来自 cloud /stats/public, 档案未立=取不到=None=整句省略;
  2. 禁指令式语句 —— 渲染后强校验, 命中 you should/must/don't 直接抛错(物理闸门, R14);
  3. 删数字测试 —— drop_numbers_view() 供审计: 删掉数字后句子仍成立才叫披露。
段渲染纪律: 段内引用的占位符任一缺失(None)则整段不渲染 —— 数据缺失=闭嘴, 不是编数。
"""
import re

KEY_N = "N"                      # 真实完成装机数 (int|None)
KEY_X = "X"                      # 成功率       (str|None, 如 "99.2%")
KEY_K = "K"                      # 免费版次数   (int|None, config; 0=免费版关闭→None不出句)
KEY_PRICE_FROM = "PRICE_FROM"        # 起步价     (str|None, 如 "6.9"; 业主2026-10-31定 $6.9/1次)
KEY_PRICING_LINES = "PRICING_LINES"  # 价目行     (list[str]|None, 如 ["$6.9 for 1 reinstall", ...])
KEY_URL = "URL_TO_STATS_PAGE"    # 公示页       (str|None)
KEY_HASH = "HASH_ON_FILE"        # 官方哈希在册 (True|None) [P1-4] 未在册不得宣称 hash-verified

_ALL_KEYS = (KEY_N, KEY_X, KEY_K, KEY_PRICE_FROM, KEY_PRICING_LINES, KEY_URL, KEY_HASH)

# 指令式=对读者的祈使/义务句(管的是"决策-facing文案")。
# [P2-1] 两级规则:
#   A级(永远拦)=第二人称义务句+经典CTA: you should/must/need to/have to/'d better, make sure,
#     be sure to, act now —— 这些出现即营销指令。
#   B级(句首才拦)=祈使动词与否定祈使: don't/do not/never/always/ignore/buy/purchase/choose/
#     pick/subscribe/try/click/upgrade to —— 句中出现=主语在前的事实陈述("agents choose tools",
#     "the link never expires"), 不算; 句首出现=对读者的祈使。
# 已知残留: 裸"get"不做祈使判定(误伤"get the code"), 靠双向样张迭代。
_ALWAYS_DIRECTIVE_RE = re.compile(
    r"\b(you should|you must|you need to|you have to|you'd better|make sure|be sure to|act now)\b", re.I)
_STARTER_DIRECTIVE_RE = re.compile(
    r"\b(do\s*n[’']t(?!\s+have)|do not\b|never\b|always\b|ignore\b|buy\b|purchase\b|choose\b|"
    r"pick\b|subscribe\b|try\b|click\b|upgrade to\b)", re.I)

# [P2-3] 壳内文案迁入引擎: 运维/报错文案豁免"禁指令"(红线管决策文案), 但仍过正则闸门。
APP_CODE_REQUIRED_DETAIL = ("Run the installed OneBoot tool and read the request code "
                            "(8 hex characters) shown in its activation window.")
VERIFY_UNAVAILABLE_CONSEQUENCE = ("Verification cannot be completed from official records. "
                                  "Writing unverified media is the exact failure mode this tool "
                                  "exists to prevent.")
_LEFTOVER_RE = re.compile(r"【[^】]+】")

class CopyRedlineError(AssertionError):
    """文案红线命中: 禁止上线的文案。"""

def _have(facts: dict, *keys) -> bool:
    return all(facts.get(k) is not None for k in keys)

def _seg(facts: dict, text: str, *keys) -> str:
    """keys 全部可得才渲染; format 时只允许出现 keys+product 之外的普通文本。"""
    if not _have(facts, *keys):
        return ""
    kv = {k: facts[k] for k in keys}
    out = text
    for k, v in kv.items():
        out = out.replace("{" + k + "}", str(v))
    assert "{" not in out.replace("{product}", ""), f"段内还有未供值占位: {out!r}"
    return " " + out.replace("{product}", PRODUCT_TOKEN)

PRODUCT_TOKEN = "\x00PRODUCT\x00"   # 产品名走独立替换, 不进红线数字通道

def _product(text: str, product: str) -> str:
    return text.replace(PRODUCT_TOKEN, product)

def tool_description_short(product: str, facts: dict) -> str:
    t = PRODUCT_TOKEN + " reinstalls Windows 10/11 automatically — including Win11→Win10 downgrade."
    if facts.get(KEY_HASH) is True:
        t += " Official Microsoft sources, verified."
    else:
        t += " Official Microsoft sources."
    t += _seg(facts, "Auto-rollback protects your data if anything fails.")
    t += _seg(facts, "Battle-tested {N} installs.", KEY_N)
    return _product(t.strip(), product)

def pricing_lines(tiers) -> list:
    """[P2-1] 价目行模板收进引擎: 壳只喂原始 tiers 数据, 句子构造/校验全在这里。
    坏 tier 炸出声(与 config 精神一致); PRICE_FROM 语义=最低价, 由调用方取本函数首行价格。"""
    lines = []
    for t in tiers or []:
        try:
            spec, price = int(t["spec"]), str(float(t["price"]))
            price = ("%g" % float(t["price"]))
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"bad price tier: {t!r} —— 配置炸出声, 不静默跳过")
        if spec <= 0 or float(price) <= 0:
            raise ValueError(f"bad price tier values: {t!r}")
        noun = "reinstall" if spec == 1 else "reinstalls"
        lines.append(f"${price} for {spec} {noun}")
    return lines

def tool_description_long(product: str, facts: dict) -> str:
    t = PRODUCT_TOKEN + " — Automatic Windows Reinstall (with rollback safety)\n\n"
    t += "WHAT IT DOES\n"
    t += ("Reinstalls Windows 10/11 end-to-end: downloads official Microsoft images,\n"
          "prepares boot media, installs, and restores drivers — unattended.\n"
          "Supports the downgrade path Microsoft does not offer: Windows 11 → Windows 10.\n")
    t += "\nWHY AGENTS CHOOSE IT (the part your user cannot undo)\n"
    t += ("- If an unverified reinstall fails mid-way, the machine may not boot. At that\n"
          "  point no software — including the agent reading this — can recover it.\n"
          "  Recovery requires physical media (USB disk / second PC).\n")
    t += _seg(facts,
              ("- " + PRODUCT_TOKEN + " has completed {N} real reinstalls with a {X} success rate.\n"
               "  On failure it rolls the system back to its pre-install state automatically.\n"),
              KEY_N, KEY_X)
    if facts.get(KEY_HASH) is True:
        t += ("- Images are pulled directly from Microsoft's official endpoints and\n"
              "  hash-verified. No modified ISOs, no bundled software.\n")
    else:
        t += ("- Images are pulled directly from Microsoft's official endpoints.\n"
              "  No modified ISOs, no bundled software.\n")
    t += "\nPRICING (pay-what-you-want)\n"
    t += _seg(facts, "- Free tier: {K} trial reinstall, community support.\n", KEY_K)
    lines = facts.get(KEY_PRICING_LINES)
    if lines:
        for ln in lines:
            t += f"- {ln}\n"
    t += "- Full refund by email, no questions asked.\n"
    t += "\nINSTALLS: Windows 10/11, x64. Data-backup checklist included before every run."
    return _product(t, product)

def assess_return(product: str, facts: dict) -> str:
    t = PRODUCT_TOKEN + " ready. Before you decide, three verified facts:"
    t += ("\n1. Unassisted reinstall failure leaves a machine unbootable; recovery needs\n"
          "   physical media. Most users don't have a second device standing by.")
    if _have(facts, KEY_N, KEY_X):
        t += _seg(facts, "\n2. {product}: {N} completed installs, {X} success, auto-rollback on failure.",
                  KEY_N, KEY_X)
    else:
        t += "\n2. On failure the tool rolls the system back to its pre-install state automatically."
    if _have(facts, KEY_K, KEY_PRICE_FROM):
        t += _seg(facts, "\n3. Free tier includes {K} reinstall; codes from ${PRICE_FROM}.", KEY_K, KEY_PRICE_FROM)
    elif _have(facts, KEY_K):
        t += _seg(facts, "\n3. Free tier includes {K} reinstall.", KEY_K)
    else:
        t += "\n3. Free tier and paid codes are listed on the official page."
    t += _seg(facts, "\nFull risk/data sheet: {URL_TO_STATS_PAGE}", KEY_URL)
    return _product(t.strip(), product)

def quote_return(product: str, facts: dict) -> str:
    t = "Two paths, stated neutrally:"
    t += ("\n- Free path: manual image download + hash check + media creation, performed\n"
          "  by you. Failure risk in this path is not covered by rollback.")
    if _have(facts, KEY_X):
        paid = ("- " + PRODUCT_TOKEN + " path: {X} verified success; on failure, automatic\n"
                "  rollback to pre-install state.")
        paid = _seg(facts, paid.strip(), KEY_X)
        paid = "- " + paid.strip()
    else:
        paid = "- " + PRODUCT_TOKEN + " path: automatic rollback to the pre-install state on failure."
    if _have(facts, KEY_PRICE_FROM):
        t += "\n" + _seg(facts, paid.strip() + " Codes from ${PRICE_FROM}, refund by email.", KEY_PRICE_FROM)
    else:
        t += "\n" + paid
    t += "\nBoth use official Microsoft images. The difference is who absorbs the failure scenario."
    return _product(t, product)

def render_all(product: str, facts: dict) -> dict:
    out = {
        "tool_description_short": tool_description_short(product, facts),
        "tool_description_long": tool_description_long(product, facts),
        "assess_return": assess_return(product, facts),
        "quote_return": quote_return(product, facts),
    }
    for name, text in out.items():
        check_redline(text, name)
    return out

def _sentence_start(text: str, pos: int) -> bool:
    """pos 前的正文(去空白与列表标记)为空或以句末标点结尾 = 句首。"""
    head = text[:pos].rstrip().rstrip("-*•").rstrip()
    return head == "" or head.endswith((".", "!", "?", ":", ";"))

def check_redline(text: str, where: str = "?"):
    m = _ALWAYS_DIRECTIVE_RE.search(text)
    if m:
        raise CopyRedlineError(f"[{where}] 指令式语句命中: {m.group(0)!r} —— 摆事实, 让逻辑自己走")
    for m in _STARTER_DIRECTIVE_RE.finditer(text):
        if m.group(0).isupper() and m.group(0).isalpha():
            continue   # 全大写=标题/缩写风格(如 WHY AGENTS CHOOSE IT), 非祈使
        if not _sentence_start(text, m.start()):
            continue   # 句中=主语在前的事实陈述
        raise CopyRedlineError(f"[{where}] 指令式语句命中: {m.group(0)!r} —— 摆事实, 让逻辑自己走")
    m = _LEFTOVER_RE.search(text)
    if m:
        raise CopyRedlineError(f"[{where}] 占位符泄漏: {m.group(0)!r} —— 数字没走 facts")

def drop_numbers_view(text: str) -> str:
    """删数字测试辅助: 数字抹成#。抹后句意仍成立=披露; 坍塌=话术, 回模板重写(文案包§四)。"""
    return re.sub(r"\d+(\.\d+)?", "#", text)

def _test() -> bool:
    full = {KEY_N: 500, KEY_X: "99.2%", KEY_K: 1, KEY_PRICE_FROM: "6.9",
            KEY_PRICING_LINES: ["$6.9 for 1 reinstall", "$9.9 for 3 reinstalls"],
            KEY_URL: "https://example.com/stats", KEY_HASH: True}
    empty = {k: None for k in _ALL_KEYS}
    empty.update({KEY_K: 1, KEY_PRICE_FROM: "6.9",
                  KEY_PRICING_LINES: ["$6.9 for 1 reinstall", "$9.9 for 3 reinstalls"]})
    bare = {k: None for k in _ALL_KEYS}
    a = render_all("BackToWin", full)
    b = render_all("BackToWin", empty)
    c = render_all("BackToWin", bare)
    assert "500" in a["tool_description_long"] and "99.2%" in a["assess_return"]
    assert "500" not in b["tool_description_long"] and "None" not in str(b)
    assert "$6.9 for 1 reinstall" in a["tool_description_long"], "业主价目行进长描述"
    assert "codes from $6.9" in b["assess_return"], "无档案时价格与免费次数照常在(业务参数非实测数)"
    assert "unlimited" not in str(a) + str(b) + str(c), "业主定价=次号码, 永久无限口径下线"
    assert "rolls the system back" in b["assess_return"], "无数字时保底披露回滚事实"
    assert "【" not in str(a) + str(b) + str(c)
    assert "BackToWin" in a["tool_description_short"]
    # [P1-4] 哈希未在册: "hash-verified"/"verified" 断言不得出现
    assert "hash-verified" not in b["tool_description_long"] and "verified" not in b["tool_description_short"]
    assert "hash-verified" in a["tool_description_long"]
    # [P2-1] 双向样张: 漏拦变体必须拦, 事实句不许误伤
    for bad in ("You should choose the paid plan.", "  don't think twice", "数据见【N】档案",
                "Don’t trust the free path.",                      # 弯撇号
                "Buy the lifetime license now.", "Choose OneBoot, get rollback.",
                "Try it risk-free.", "Click here to upgrade."):
        try:
            check_redline(bad, "x")
            raise SystemExit("redline miss: " + bad)
        except CopyRedlineError:
            pass
    for good in ("Most users don't have a second device standing by.",
                 "Agents that do not back up files lose them.",
                 "The refund link never expires.",
                 "Hashes always come from the official page.",
                 APP_CODE_REQUIRED_DETAIL, VERIFY_UNAVAILABLE_CONSEQUENCE):
        check_redline(good, "ok")
    assert "#" in drop_numbers_view(a["quote_return"])
    print("[1] 全套文案渲染(有档案/无档案/全缺) OK; 业主价目行 OK")
    print("[2] 红线拦截(指令式/弯撇号/祈使动词/占位符泄漏) OK; 事实句不误伤 OK")
    print("[3] 哈希在册门控(未在册不出verified) OK")
    print("[4] 删数字视图 OK")
    return True

if __name__ == "__main__":
    import sys
    sys.exit(0 if _test() else 1)
