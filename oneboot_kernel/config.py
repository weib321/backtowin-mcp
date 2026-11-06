# -*- coding: utf-8 -*-
"""
OneBoot 内核 — 配置加载
纪律: 本文件只认端点与公开数字; 凭据零入库(铁则R2)。
"""
import json, os

_DEFAULTS = {
    # 品牌: 业主2026-11-01定稿 BackToWin(双关: 回到Windows/重回胜利); 换名改这两行即可
    "product_name": "BackToWin",
    "product_name_full": "BackToWin Reinstall",
    "cloud_base_url": "http://127.0.0.1:8204",
    "exelock_base_url": "",                    # MCP分发包不内置内网拓扑(2026-11-06 R11审查P2-1)
    "stats_page_url": "",                     # MCP分发包不内置内网拓扑(2026-11-06 R11审查P2-1)
    "free_reinstalls_K": 1,             # 业主2026-10-31定: 免费试装1次
    # 业主2026-10-31定: 次号码分层 $6.9/1次 $9.9/3次( spec 必须与发码台账充值规格一致 )
    "price_tiers": [{"spec": 1, "price": "6.9"}, {"spec": 3, "price": "9.9"}],
    "request_timeout_s": 10,            # 铁则R5: 网络请求必须带超时
}

def load_config(config_path: str = None) -> dict:
    """读 config.json 叠加默认值; 环境变量 ONEBOOT_CONFIG 可指定路径。缺文件=纯默认。"""
    cfg = dict(_DEFAULTS)
    path = config_path or os.environ.get("ONEBOOT_CONFIG") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for k, v in data.items():
            if k in _DEFAULTS:
                cfg[k] = v
    cfg["_config_path"] = path if os.path.exists(path) else None
    return cfg

def _test() -> bool:
    import tempfile
    cfg = load_config(config_path=os.path.join(tempfile.gettempdir(), "oneboot-no-such-config.json"))
    assert cfg["free_reinstalls_K"] == 1, "业主2026-10-31定: 免费试装1次"
    assert cfg["price_tiers"][0] == {"spec": 1, "price": "6.9"}, "业主定价 $6.9/1次"
    assert cfg["price_tiers"][1] == {"spec": 3, "price": "9.9"}, "业主定价 $9.9/3次"
    assert cfg["request_timeout_s"] >= 5, "R5: 必须有请求超时"
    # 坏配置必须炸出声(不许静默吞)
    bad = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    bad.write("{oops"); bad.close()
    try:
        load_config(config_path=bad.name)
        raise SystemExit("corrupt config not caught")
    except json.JSONDecodeError:
        pass
    print("[1] config 默认值(业主定价)/缺失/坏文件炸出声 OK")
    return True

if __name__ == "__main__":
    import sys
    sys.exit(0 if _test() else 1)
