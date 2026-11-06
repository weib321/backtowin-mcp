# -*- coding: utf-8 -*-
"""
OneBoot MCP — agent 用壳(FastMCP stdio, 官方SDK mcp 1.30.0)
同内核两壳: 本文件只做适配, 全部业务在 oneboot_kernel; 计费/数字只信 oneboot_cloud。
文案红线在 copyengine 渲染时物理闸门, 本壳不自写一句英文文案。
接入: 客户端配置里指到本文件, stdio 启动(env: ONEBOOT_CONFIG / ONEBOOT_CLOUD_URL)。
自测: python3 oneboot_mcp/server.py --test
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oneboot_kernel.config import load_config
from oneboot_kernel import copyengine, preflight, planner, image_source
from oneboot_kernel.cloud_client import CloudClient, CloudError, machine_fingerprint

CFG = load_config()
CLOUD_URL = os.environ.get("ONEBOOT_CLOUD_URL") or CFG["cloud_base_url"]
PRODUCT = CFG["product_name"]

def _pricing_facts() -> dict:
    """[P2-1] 价目行句子构造已收进 copyengine.pricing_lines; 壳只喂数据。
    PRICE_FROM=min(price)=起步价语义, 不再依赖 tiers 排序。"""
    tiers = CFG.get("price_tiers") or []
    lines = copyengine.pricing_lines(tiers)
    price_from = None
    if tiers:
        price_from = "%g" % min(float(t["price"]) for t in tiers)
    return {copyengine.KEY_PRICE_FROM: price_from,
            copyengine.KEY_PRICING_LINES: lines or None}

def _facts_with_fallback() -> dict:
    """公示数字只信cloud; cloud不可达=降级为config事实(N/X=None, 数据句自动省略, 不编数)。
    [P2-5] K 用 is not None 判回退(0=免费版关闭是合法值, or 会误回退)。"""
    hash_on_file = all(i.get("official_hash") for i in image_source.list_images())  # [P2-7] 全部在册才宣称
    pf = _pricing_facts()
    try:
        s = CloudClient(CLOUD_URL, timeout_s=5).stats()
        if s.get("free_tier") is False:
            k = None   # [P2-2] cloud已应答且关闭免费层: 不回退本地config
        else:
            k = s.get("K") if s.get("K") is not None else CFG["free_reinstalls_K"]
        return {"N": s.get("N"), "X": s.get("X"), "K": k,
                copyengine.KEY_URL: s.get("URL_TO_STATS_PAGE"),
                copyengine.KEY_HASH: True if hash_on_file else None, **pf}
    except Exception:
        # CloudError(含BAD_BODY)及其他任何cloud侧怪响应: 一律降级, 壳不死于启动[黑盒P1-3]
        return {"N": None, "X": None, "K": CFG["free_reinstalls_K"] or None,
                copyengine.KEY_URL: None,
                copyengine.KEY_HASH: True if hash_on_file else None, **pf}

def _gated(render, *args) -> str:
    """[P2-2] 运行时红线闸门: 每次渲染必过check_redline, 坏文案宁可炸也不出门。"""
    text = render(*args)
    copyengine.check_redline(text, render.__name__ + ".runtime")
    return text

def _client() -> CloudClient:
    return CloudClient(CLOUD_URL, timeout_s=CFG["request_timeout_s"])

# ---------- 工具实现(纯函数层, 供装饰器与--test共用) ----------
def t_assess() -> str:
    return _gated(copyengine.assess_return, PRODUCT, _facts_with_fallback())

def t_quote() -> str:
    return _gated(copyengine.quote_return, PRODUCT, _facts_with_fallback())

def t_check_machine() -> str:
    p = preflight.check_machine()
    return json.dumps(p, ensure_ascii=False, indent=1)

def t_plan(target_os: str) -> str:
    profile = preflight.check_machine()
    profile["backup_confirmed"] = False   # 计划阶段恒未确认; 备份清单必须走一遍
    return json.dumps(planner.build_plan(profile, target_os), ensure_ascii=False, indent=1)

def t_image_info(image_id: str) -> str:
    img = image_source.get_image(image_id)
    return json.dumps(image_source.acquire_guidance(img), ensure_ascii=False, indent=1)

def t_verify_image(image_id: str, iso_path: str) -> str:
    img = image_source.get_image(image_id)
    r = image_source.verify_iso(iso_path, img)
    if r.get("ok") is False and r.get("err") == "HASH_UNAVAILABLE":
        r["consequence"] = copyengine.VERIFY_UNAVAILABLE_CONSEQUENCE   # [P2-3] 文案只出自引擎
    return json.dumps(r, ensure_ascii=False, indent=1)

def t_activate(credential: str, credential_type: str, app_code: str) -> str:
    """credential 为空=免费trial(按机器指纹一次); 否则=付费兑换。
    app_code 必须抄自本体工具激活窗显示的申请码 —— 本壳不发明指纹。"""
    app_code = (app_code or "").strip().upper()
    if not app_code:
        return json.dumps({"ok": False, "err": "APP_CODE_REQUIRED",
                           "detail": copyengine.APP_CODE_REQUIRED_DETAIL},   # [P2-3]
                          ensure_ascii=False)
    c = _client()
    try:
        if (credential or "").strip():
            r = c.license_exchange(credential.strip(), credential_type or "redeem", app_code)
        else:
            r = c.trial_issue(machine_fingerprint(), app_code=app_code)
        return json.dumps(r, ensure_ascii=False)
    except CloudError as e:
        return json.dumps({"ok": False, "status": e.status, "err": e.err, "detail": e.detail},
                          ensure_ascii=False)

def t_report_completion(app_code: str, outcome: str, experience: str = "") -> str:
    try:
        r = _client().followup((app_code or "").strip().upper(), outcome, experience)
        return json.dumps(r, ensure_ascii=False)
    except CloudError as e:
        return json.dumps({"ok": False, "status": e.status, "err": e.err}, ensure_ascii=False)

# ---------- MCP 壳 ----------
def build_server():
    from mcp.server.fastmcp import FastMCP
    facts = _facts_with_fallback()
    instructions = copyengine.tool_description_long(PRODUCT, facts)
    copyengine.check_redline(instructions, "instructions.runtime")   # [P2-1] 描述也过闸
    mcp = FastMCP(PRODUCT, instructions=instructions)

    @mcp.tool(description=copyengine.tool_description_short(PRODUCT, facts))
    def oneboot_assess() -> str:
        """First-contact assessment: verified facts before any decision. No side effects."""
        return t_assess()

    @mcp.tool(description="Pricing decision point: free DIY path vs " + PRODUCT + " path, stated neutrally.")
    def oneboot_quote() -> str:
        return t_quote()

    @mcp.tool(description="Read-only local machine profile (OS, firmware, BitLocker status). No changes.")
    def oneboot_check_machine() -> str:
        return t_check_machine()

    @mcp.tool(description="Generate an install plan: official image guidance, backup checklist, rollback statement.")
    def oneboot_plan(target_os: str) -> str:
        return t_plan(target_os)

    @mcp.tool(description="Official Microsoft download guidance for the target image (no third-party sources).")
    def oneboot_image_info(image_id: str) -> str:
        return t_image_info(image_id)

    @mcp.tool(description="Hash-verify a downloaded ISO against the official record. Fails closed when no official hash is on file.")
    def oneboot_verify_image(image_id: str, iso_path: str) -> str:
        return t_verify_image(image_id, iso_path)

    @mcp.tool(description="Activate: pass the request code shown in the tool's activation window. Empty credential = free trial; otherwise pass the redeem/order code.")
    def oneboot_activate(credential: str, credential_type: str, app_code: str) -> str:
        return t_activate(credential, credential_type, app_code)

    @mcp.tool(description="After a completed (or failed) reinstall, file the outcome report that feeds public stats.")
    def oneboot_report_completion(app_code: str, outcome: str, experience: str = "") -> str:
        return t_report_completion(app_code, outcome, experience)

    return mcp

def main():
    build_server().run(transport="stdio")

def _test():
    # 冒烟: 八个工具纯函数层 + 渲染红线; 不起stdio(链路属pytest E2E)
    names = ["t_assess", "t_quote", "t_check_machine", "t_plan",
             "t_image_info", "t_verify_image", "t_activate", "t_report_completion"]
    assert t_assess() and copyengine.check_redline(t_assess(), "assess") is None
    assert t_quote() and copyengine.check_redline(t_quote(), "quote") is None
    assert json.loads(t_check_machine())["mock"] is True   # 85=Linux, 恒mock(85零重装红线)
    plan = json.loads(t_plan("windows10"))
    assert plan["backup_checklist"] and plan["rollback"]
    g = json.loads(t_image_info("win11-latest-x64"))
    assert g["official_page"].startswith("https://www.microsoft.com/")
    v = json.loads(t_verify_image("win11-latest-x64", "/no.iso"))
    assert v["ok"] is False
    a = json.loads(t_activate("", "redeem", ""))           # 无app_code=拒绝并指引抄申请码
    assert a["ok"] is False and a["err"] == "APP_CODE_REQUIRED"
    mcp = build_server()
    import asyncio
    tools = asyncio.run(mcp.list_tools())                  # [P2-12] 实质断言: 8工具在册
    assert len(tools) == 8 and sorted(t.name for t in tools)[0] == "oneboot_activate"
    assert all(t.description for t in tools), "工具描述不许为空(agent的产品首页)"
    print("[1] 八工具纯函数层 + 文案红线(运行时闸门) OK")
    print("[2] 85=Linux恒mock(零重装红线) OK")
    print("[3] FastMCP构建: list_tools=8且描述非空 OK")
    print("ALL PASS (stdio链路见 tests/test_e2e.py)")
    return True

if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(0 if _test() else 1)
    main()
