# -*- coding: utf-8 -*-
"""
OneBoot 内核 — 官方镜像源注册表
红线(需求§二.3): 只走微软官方下载源, 不得改动此性质。
诚实纪律(R23/R0): 微软直链是会话级生成的, 本模块不伪造直链, 只登记官方页面与可得哈希;
  哈希不可得=校验fail-closed(拒绝继续), 绝不"看起来校验过"。
"""
import hashlib, json, os

# 注册表: 只收微软官方域; verify 分级 fail-closed
# 哈希两级(2026-10-31业主定, 修正版):
#   official_hash  = 微软下载页"Verify your download"一手取证(下载日页面直抄)——现行在售版本唯一能宣称 hash-verified 的级
#   community_hash = ≥2独立来源交叉一致的社区哈希——verify 给 provisional 结论, 文案不出 hash-verified 句
#   业主修正(2026-10-31): 没有官方级哈希的镜像, **如果是往期版本**(官方页已不再提供该版本/已停服,
#   官方一手取证客观不可得), 则参考社区级——往期版本的 community 级=可用依据而非仅参考
#   (依据: 主打卖点=Win11降级Win10, 降级目标 Win10 22H2 本身就是往期版本, 此修正让主打路径可用)
# 来源登记在 hash_sources(证据链, 壳开; 原始检索档案在 research/)
IMAGES = [
    {"id": "win10-22h2-x64", "os": "windows10", "edition": "Windows 10 22H2", "arch": "x64",
     "official_page": "https://www.microsoft.com/en-us/software-download/windows10",
     "official_hash": None, "hash_algorithm": "sha256",
     "note": "page issues session-scoped media links; hash shown on the page under Verify your download"},
    {"id": "win11-latest-x64", "os": "windows11", "edition": "Windows 11 (latest)", "arch": "x64",
     "official_page": "https://www.microsoft.com/en-us/software-download/windows11",
     "official_hash": None, "hash_algorithm": "sha256",
     "note": "page issues session-scoped media links; hash shown on the page under Verify your download"},
    # ---- English 镜像候选(2026-10-31 双源交叉入册; 语言启用待业主拍板"镜像语言"后切换) ----
    {"id": "win10-22h2-english-x64", "os": "windows10", "edition": "Windows 10 22H2 (English)", "arch": "x64",
     "language": "en-US", "enabled": False,
     "official_page": "https://www.microsoft.com/en-us/software-download/windows10",
     "official_hash": None, "community_hash": "f41ba37aa02dcb552dc61cef5c644e55b5d35a8ebdfac346e70f80321343b506",
     "hash_algorithm": "sha256",
     "hash_sources": ["github.com/awesome-windows11/windows11 wiki (ISO page)",
                      "forums.linuxmint.com t=393768 (independent downloader)"],
     "note": "community cross-verified; upgrade to official on download day (Verify your download)"},
    {"id": "win11-24h2-english-x64", "os": "windows11", "edition": "Windows 11 24H2 (English, build 26100.1742)",
     "arch": "x64", "language": "en-US", "enabled": False, "deprecated": True,
     "official_page": "https://www.microsoft.com/en-us/software-download/windows11",
     "official_hash": None, "community_hash": "b56b911bf18a2ceaeb3904d87e7c770bdf92d3099599d61ac2497b91bf190b11",
     "hash_algorithm": "sha256",
     "hash_sources": ["gist.github.com/jpluimers (24H2 hash archive)",
                      "learn.microsoft.com Q&A + rg-adguard.net (build 26100.1742)",
                      "linustechtips forum (independent confirmer)"],
     "note": "DEPRECATED for new installs: 24H2 Home/Pro ended servicing 2026-10-13 (KB5127648 final). "
             "Use 26H2 for new installs; 24H2 entry kept for reinstalling existing 24H2 machines only."},
    {"id": "win11-26h2-english-x64", "os": "windows11",
     "edition": "Windows 11 26H2 (English, GA build 26300.9550, KB5124010)", "arch": "x64", "language": "en-US",
     "enabled": False,
     "official_page": "https://www.microsoft.com/en-us/software-download/windows11",
     "official_hash": None, "community_hash": None, "hash_algorithm": "sha256",
     "hash_sources": [],
     "note": "GA since 2026-09-22 (current annual release; 24H2 EOL 10-13). No hash on record yet: "
             "community double-source not settled (release <2 months old) and official page hash is "
             "session-scoped — record official hash on download day per the hash standard "
             "(Verify your download, one-hand evidence). fail-closed until then."},
]

def _official(url: str) -> bool:
    from urllib.parse import urlparse
    host = (urlparse(url).hostname or "").lower()
    return host == "microsoft.com" or host.endswith(".microsoft.com")

def list_images() -> list:
    return [dict(i) for i in IMAGES]

def get_image(image_id: str) -> dict:
    for i in IMAGES:
        if i["id"] == image_id:
            return dict(i)
    raise KeyError(f"unknown image id: {image_id}")

def acquire_guidance(image: dict) -> dict:
    """获取指引: 官方页 + 步骤(下载由 agent/用户在官方页完成, 本工具不代下不篡改)。"""
    if image.get("deprecated"):
        raise ValueError("DEPRECATED image (servicing ended): use the successor entry — fail-closed")
    if not _official(image["official_page"]):
        raise ValueError("非官方源, 拒绝(需求§二.3)")
    return {
        "image_id": image["id"],
        "official_page": image["official_page"],
        "steps": [
            "Open the official page and download the ISO (or use Microsoft's Media Creation Tool).",
            "Save the ISO path for the verification step.",
        ],
    }

def verify_iso(iso_path: str, image: dict) -> dict:
    """哈希校验分级(2026-10-31):
    - official_hash 在册: 实算比对, 匹配=ok+level=official(文案可出 hash-verified)
    - 仅 community_hash: 实算比对, 匹配=ok+level=community(provisional, 提示官方页升级); 不匹配=fail
    - 都无: HASH_UNAVAILABLE fail-closed"""
    if not os.path.exists(iso_path):
        return {"ok": False, "err": "FILE_NOT_FOUND", "iso_path": iso_path}
    official = image.get("official_hash")
    community = image.get("community_hash")
    algo = image.get("hash_algorithm", "sha256")
    if not official and not community:
        return {"ok": False, "err": "HASH_UNAVAILABLE",
                "detail": "no hash on record; pull it from the official page (Verify your download) first — fail-closed"}
    h = hashlib.new(algo)
    with open(iso_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    got = h.hexdigest()
    import hmac as _hmac
    if official and _hmac.compare_digest(got, str(official).lower()):
        return {"ok": True, "level": "official", "algorithm": algo, "expected": official, "got": got}
    if official:
        # [P2-6] official 在册时 community 不得降级通过(official 失配=fail)
        return {"ok": False, "level": "official", "algorithm": algo, "expected": official, "got": got}
    if community and _hmac.compare_digest(got, str(community).lower()):
        return {"ok": True, "level": "community",
                "detail": "provisionally verified against community cross-checked hash; "
                          "re-verify against the official page hash on download day",
                "algorithm": algo, "expected": community, "got": got}
    return {"ok": False, "level": "community", "algorithm": algo, "expected": community, "got": got}

def save_registry(path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(IMAGES, f, ensure_ascii=False, indent=2)

def _test() -> bool:
    assert all(_official(i["official_page"]) for i in IMAGES), "注册表只准官方域"
    img = get_image("win10-22h2-x64")
    g = acquire_guidance(img)
    assert g["official_page"].startswith("https://www.microsoft.com/")
    try:
        acquire_guidance({**img, "official_page": "https://evil.example/win10.iso"})
        raise SystemExit("non-official source not rejected")
    except ValueError:
        pass
    r = verify_iso("/no/such.iso", img)
    assert r["ok"] is False and r["err"] == "FILE_NOT_FOUND"
    r2 = verify_iso(__file__, img)   # 哈希未登记 -> fail-closed
    assert r2["ok"] is False and r2["err"] == "HASH_UNAVAILABLE", r2
    # 有哈希时: 实算比对(拿本文件自己当样本)
    import hashlib
    img2 = {**img, "official_hash": hashlib.sha256(open(__file__, "rb").read()).hexdigest()}
    r3 = verify_iso(__file__, img2)
    assert r3["ok"] is True and r3["got"] == img2["official_hash"]
    img3 = {**img2, "official_hash": "0" * 64}
    r4 = verify_iso(__file__, img3)
    assert r4["ok"] is False and r4["got"] != r4["expected"]
    # [4] 分级: community 哈希=provisional ok; official 匹配=official 级
    import hashlib as _hl
    en = get_image("win10-22h2-english-x64")
    assert en.get("enabled") is False and en["community_hash"].startswith("f41ba37a"), "英文候选条目在册未启用"
    fp = "/tmp/oneboot_hash_selftest.iso"
    _hl.sha256()  # noqa
    data = b"x" * 1024
    with open(fp, "wb") as f:
        f.write(data)
    chash = _hl.sha256(data).hexdigest()
    fake = {**en, "community_hash": chash}
    r = verify_iso(fp, fake)
    assert r["ok"] is True and r["level"] == "community" and "provisionally" in r["detail"], r
    fake2 = {**fake, "official_hash": chash}
    r2 = verify_iso(fp, fake2)
    assert r2["ok"] is True and r2["level"] == "official", r2
    r3 = verify_iso(fp, {**fake, "community_hash": "0" * 64})
    assert r3["ok"] is False, "社区哈希不匹配必须fail"
    # KEY_HASH 门控语义: 只有 official 在册才点亮(community 不点亮文案)
    # KEY_HASH 门控语义: official 在册才点亮文案 —— mcp壳tests已覆盖
    print("[1] 官方域守卫 OK")
    print("[2] 哈希缺失fail-closed OK")
    print("[3] 哈希实算比对(正/误) OK")
    # [P2-5] deprecated 镜像: get 指引必须拒绝
    dep = get_image("win11-24h2-english-x64")
    assert dep.get("deprecated") is True
    try:
        acquire_guidance(dep)
        raise SystemExit("deprecated not rejected")
    except ValueError:
        pass
    print("[4] 分级验证: community=provisional/official=official/错配fail/英文条目在册未启用/DEPRECATED拒指引 OK")
    return True

if __name__ == "__main__":
    import sys
    sys.exit(0 if _test() else 1)
