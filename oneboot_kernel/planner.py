# -*- coding: utf-8 -*-
"""
OneBoot 内核 — 安装计划生成器(纯逻辑, 确定性)
分工铁律(终局战略§二技术边界): agent 管决策准备, 工具管执行。
  本模块只产"计划", 装机本体由客户机上的工具(远程帮 v1.7.3 同内核)执行 —— 本体零改动。
每个计划必含: 备份清单(破坏性动作前必有确认/证据, 不变量③) + 回滚说明(价值锚) + 移交说明。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 任意cwd可跑(s4_api同款)
from oneboot_kernel import image_source

_BACKUP_CHECKLIST = [
    "Personal files (Documents / Desktop / Pictures / app data) → external drive or cloud",
    "Browser bookmarks and saved passwords (export from the browser)",
    "Software license keys / authenticator exports (an OS reinstall can require re-login)",
    "Wi-Fi passwords and network printer setup notes",
    "Confirm the external backup drive is readable on ANOTHER device before starting",
]

def build_plan(profile: dict, target_os: str) -> dict:
    """profile 来自 preflight.check_machine(); target_os: 'windows10'|'windows11'。"""
    if target_os not in ("windows10", "windows11"):
        raise ValueError("target_os must be windows10 or windows11")
    downgrade = (profile.get("os_family") == "windows11" and target_os == "windows10")
    imgs = image_source.list_images()
    image_id = "win10-22h2-x64" if target_os == "windows10" else "win11-latest-x64"
    image = next(i for i in imgs if i["id"] == image_id)
    warnings = []
    if profile.get("bitlocker") == "encrypted":
        warnings.append("BitLocker is ON: suspend/decrypt or have the recovery key ready — the tool stops on encrypted disks by design.")
    if profile.get("firmware") == "legacy-bios":
        warnings.append("Legacy BIOS/MBR machine: the tool supports MBR; keep the media plan as generated.")
    if not profile.get("backup_confirmed"):
        warnings.append("Backup not confirmed yet: work through the checklist before anything destructive.")
    plan = {
        "target_os": target_os,
        "image": image_source.acquire_guidance(image),
        "downgrade_path": downgrade,   # 官方只升不降, 这里=降级自由(核心卖点, 只陈述事实)
        "backup_checklist": list(_BACKUP_CHECKLIST),
        "rollback": ("On failure the tool rolls the system back to its pre-install state "
                     "automatically. Keep the backup anyway: rollback protects the system, "
                     "not files you chose to delete."),
        "execution_handoff": {
            "who": "the installed OneBoot tool performs the reinstall itself",
            "agent_role": "prepare, license, and follow up — the agent does not run disk operations",
            "activation": ("in the tool's activation window, use order/redeem code entry "
                           "or the activation code issued to this machine"),
        },
        "warnings": warnings,
        "mock": bool(profile.get("mock")),
    }
    return plan

def _test() -> bool:
    p_win11 = {"os_family": "windows11", "bitlocker": "encrypted", "firmware": "uefi", "backup_confirmed": False}
    plan = build_plan(p_win11, "windows10")
    assert plan["downgrade_path"] is True and plan["image"]["official_page"].startswith("https://www.microsoft.com/")
    assert len(plan["backup_checklist"]) == 5 and plan["rollback"] and plan["warnings"]
    assert any("BitLocker" in w for w in plan["warnings"])
    plan2 = build_plan({**p_win11, "bitlocker": "none", "backup_confirmed": True}, "windows11")
    assert plan2["downgrade_path"] is False and not any("BitLocker" in w for w in plan2["warnings"])
    assert plan2["execution_handoff"]["who"].startswith("the installed")
    try:
        build_plan(p_win11, "macos")
        raise SystemExit("bad target not rejected")
    except ValueError:
        pass
    print("[1] 降级路径/镜像指向官方页 OK")
    print("[2] 备份清单/回滚/警告 OK")
    print("[3] 非法目标拒绝 OK")
    return True

if __name__ == "__main__":
    import sys
    sys.exit(0 if _test() else 1)
