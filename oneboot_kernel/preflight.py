# -*- coding: utf-8 -*-
"""
OneBoot 内核 — 本机预检(只读, 零破坏)
85红线: 本模块在非Windows上一律 mock, 在Windows上也只读(注册表/manage-bde -status 查询), 不碰磁盘。
真实执行发生在客户机的本体工具里, 与本模块无关。
"""
import platform

def check_machine(dummy_cmd: str = None) -> dict:
    """返回机器画像。dummy_cmd 仅供测试注入; 真机路径只在 Windows 且无注入时走。"""
    if platform.system() != "Windows" or dummy_cmd is not None:
        return _mock_profile()
    return _windows_profile()

def _mock_profile() -> dict:
    return {"mock": True, "os_family": "windows11", "os_version": "10.0.19045(mock)",
            "arch": "x64", "firmware": "uefi", "bitlocker": "none", "backup_confirmed": False}

def _windows_profile() -> dict:
    import winreg
    ver = platform.win32_ver()
    try:
        win = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SYSTEM\CurrentControlSet\Control")
        pe, _ = winreg.QueryValueEx(win, "PEFirmwareType")
        firmware = "uefi" if int(pe) == 2 else "legacy-bios"
    except OSError:
        firmware = "unknown"
    try:
        win = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\Microsoft\Cryptography")
        machine_guid, _ = winreg.QueryValueEx(win, "MachineGuid")
    except OSError:
        machine_guid = ""
    # BitLocker 只读探测: manage-bde -status C: (查询非破坏; 失败=unknown, 不猜测)
    bitlocker = "unknown"
    try:
        import subprocess
        r = subprocess.run(["manage-bde", "-status", "C:"], capture_output=True,
                           text=True, timeout=10)   # R5: 10s超时
        out = (r.stdout or "").lower()
        if "protection status:    protection on" in out or "protection on" in out:
            bitlocker = "encrypted"
        elif "protection off" in out:
            bitlocker = "none"
    except Exception:
        pass
    # [P1-1修复] win32_ver()=(release, version, csd, ptype); build号在version第三段, Win11>=22000
    try:
        build = int(ver[1].split(".")[2])
    except (IndexError, ValueError):
        build = 0
    fam = "windows11" if build >= 22000 else "windows10"
    return {"mock": False, "os_family": fam, "os_version": ".".join(x for x in ver if x),
            "arch": platform.machine(), "firmware": firmware,
            "bitlocker": bitlocker, "backup_confirmed": False,
            "machine_guid": machine_guid}

def _test() -> bool:
    p = check_machine(dummy_cmd="mock")   # Linux上恒mock; 注入也mock
    assert p["mock"] is True and p["os_family"] in ("windows10", "windows11")
    assert p["firmware"] in ("uefi", "legacy-bios") and p["bitlocker"] in ("none", "encrypted", "unknown")
    print("[1] 非Windows恒mock OK:", {k: p[k] for k in ("os_family", "firmware", "bitlocker")})
    return True

if __name__ == "__main__":
    import sys
    sys.exit(0 if _test() else 1)
