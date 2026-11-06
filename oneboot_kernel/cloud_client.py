# -*- coding: utf-8 -*-
"""
OneBoot 内核 — cloud 客户端(licensing/trial/stats/followup 四合一)
cloud 是我方新服务(85:8204); 兑换代理背后是本体 exelock API —— 本模块只对着 cloud 说话。
R5: 全部请求带超时; 错误一律 CloudError 带服务端 err 码, 不吞。
"""
import json, urllib.request, urllib.error

class CloudError(RuntimeError):
    def __init__(self, status: int, err: str, detail: str = ""):
        super().__init__(f"cloud {status} {err} {detail}".strip())
        self.status, self.err, self.detail = status, err, detail

class CloudClient:
    def __init__(self, base_url: str, timeout_s: int = 10):
        self.base = base_url.rstrip("/")
        self.timeout = timeout_s

    def _req(self, method: str, path: str, payload: dict = None) -> dict:
        data = json.dumps(payload).encode() if payload is not None else None
        # UA 必带: Cloudflare 对 Python-urllib 默认UA直接403(2026-11-05实测)
        r = urllib.request.Request(self.base + path, data=data, method=method,
                                   headers={"Content-Type": "application/json",
                                            "User-Agent": "BackToWin-MCP/1.0"})
        try:
            with urllib.request.urlopen(r, timeout=self.timeout) as resp:
                raw = resp.read().decode()
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read().decode())
            except Exception:
                body = {}
            raise CloudError(e.code, body.get("err", "UNKNOWN"), str(body)[:200])
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise CloudError(0, "UNREACHABLE", str(e))
        try:
            return json.loads(raw)
        except ValueError as e:
            # [黑盒P1-3] 200+非JSON(中间盒/认证页/误配)归一CloudError, 壳按cloud不可达降级
            raise CloudError(200, "BAD_BODY", str(e)[:80])

    # -- 公示数字(【N】【X】【K】【P】【URL】唯一来源; 取不到的字段=None) --
    def stats(self) -> dict:
        return self._req("GET", "/stats/public")

    # -- 免费版配额(服务端按指纹记账, 本地说了不算; app_code=本体工具激活窗的申请码) --
    def trial_issue(self, fingerprint: str, app_code: str = "", machine_meta: dict = None) -> dict:
        return self._req("POST", "/trial/issue",
                         {"fingerprint": fingerprint, "app_code": app_code,
                          "machine_meta": machine_meta or {}})

    # -- 付费兑换: credential(兑换码/订单号) + 申请码 -> 激活码与次数(本体台账原生语义) --
    def license_exchange(self, credential: str, credential_type: str, app_code: str) -> dict:
        return self._req("POST", "/license/exchange",
                         {"credential": credential, "credential_type": credential_type,
                          "app_code": app_code})

    # -- 回访: 完成码/使用报告(壳开数据闭: 原始档案只在服务端) --
    def followup(self, app_code: str, outcome: str, experience: str = "", agent_meta: dict = None) -> dict:
        return self._req("POST", "/followup",
                         {"app_code": app_code, "outcome": outcome,
                          "experience": experience[:4000], "agent_meta": agent_meta or {}})

def machine_fingerprint() -> str:
    """客户端便利函数: 服务端把它当不透明串。
    [P2-10] 不可逆派生: HMAC(本地随机盐, MachineGuid|MAC), 不上送原始MAC; 盐首启生成落 ~/.oneboot。"""
    import platform, uuid, hmac, hashlib, os
    base = os.path.join(os.path.expanduser("~"), ".oneboot")
    os.makedirs(base, exist_ok=True)
    sp = os.path.join(base, "device_secret")
    if not os.path.exists(sp):
        with open(sp, "w", encoding="utf-8") as f:
            f.write(uuid.uuid4().hex)
        os.chmod(sp, 0o600)
    with open(sp, encoding="utf-8") as f:
        secret = f.read().strip()
    dev = ""
    if platform.system() == "Windows":
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
            dev, _ = winreg.QueryValueEx(k, "MachineGuid")
        except OSError:
            dev = ""
    if not dev:
        dev = str(uuid.getnode())
    return "ob1-" + hmac.new(secret.encode(), dev.encode(), hashlib.sha256).hexdigest()[:32]

def _test() -> bool:
    from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
    import threading
    class H(BaseHTTPRequestHandler):
        def _j(self, code, obj):
            b = json.dumps(obj).encode()
            self.send_response(code); self.send_header("Content-Length", str(len(b)))
            self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(b)
        def do_GET(self):
            self._j(200, {"N": None, "X": None, "K": 2, "P": "4.99", "URL_TO_STATS_PAGE": None}) if self.path == "/stats/public" else self._j(404, {"err": "NOT_FOUND"})
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n).decode())
            if self.path == "/trial/issue":
                assert body["fingerprint"], "fingerprint required"
                self._j(200, {"ok": True, "remaining": 2, "activation_code": "ABCD1234"})
            elif self.path == "/license/exchange":
                self._j(404, {"err": "NOT_FOUND"})
            else:
                self._j(404, {"err": "NOT_FOUND"})
        def log_message(self, *a): pass
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H); srv.daemon_threads = True
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    c = CloudClient(f"http://127.0.0.1:{port}", timeout_s=5)
    s = c.stats()
    assert s["K"] == 2 and s["N"] is None, "公示数字缺档案=None"
    t = c.trial_issue("mock-aa-bb", app_code="A1B2C3D4", machine_meta={"os": "test"})
    assert t["ok"] is True and t["remaining"] == 2
    try:
        c.license_exchange("nope", "redeem", "A1B2C3D4")
        raise SystemExit("error not raised")
    except CloudError as e:
        assert e.status == 404 and e.err == "NOT_FOUND"
    try:
        CloudClient("http://127.0.0.1:1", timeout_s=2).stats()
        raise SystemExit("unreachable not raised")
    except CloudError as e:
        assert e.err == "UNREACHABLE"
    fp = machine_fingerprint()
    assert fp.startswith("ob1-") and len(fp) == 36
    assert fp == machine_fingerprint(), "指纹稳定(同机同值)"
    print("[1] stats/trial/exchange 正常流 OK")
    print("[2] 4xx err码透传 + 不可达CloudError OK")
    print("[3] 指纹=不可逆派生(ob1-前缀, 稳定, 不含原始MAC) OK")
    return True

if __name__ == "__main__":
    import sys
    sys.exit(0 if _test() else 1)
