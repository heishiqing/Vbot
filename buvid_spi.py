"""B 站 cookie 来源 — 优先用真实浏览器拿的, 没有则匿名 SPI fallback.

2026-06-03 owner 修 412: B 站升级了 web_im/send_msg 风控, 需要这些 cookie:
  必需 (主路径有了 SESSDATA+bili_jct+bili_ticket+DedeUserID 已够):
    SESSDATA, bili_jct, bili_ticket, DedeUserID
  风控指纹 (缺会被 WAF 拦 412 + HTML 错误页):
    buvid3, buvid4, b_nut, buvid_fp
  增强 (浏览器登录后才有, 用真值更稳):
    DedeUserID__ckMd5, _uuid, b_lsid, sid

策略:
1. **优先读 runtime/browser_cookies.json** — 用户用 CDP 真浏览器登录后抠的, 9 项设备指纹.
   这是"借用真实浏览器登录的设备身份", 比每次随机 hex 更稳, B 站不当新设备.
2. **缺文件时 fallback 到 SPI 匿名接口** — 调 /x/frontend/finger/spi 拿 buvid3/buvid4,
   buvid_fp 用本地持久随机 hex.

owner 实测 (2026-06-03):
- 真浏览器 fetch send_msg(self→self): HTTP 200 + code 21026 (业务层拒绝 self->self)
- 我 Python 用同样 cookie 复现: HTTP 200 + code 21026 ← 100% 等价
- 这证明 cookie 一致, send_msg 风控已穿透
"""

import os
import secrets
import time
from pathlib import Path

import requests

_SPI_URL = "https://api.bilibili.com/x/frontend/finger/spi"
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

_RUNTIME_DIR = Path(__file__).parent / "runtime"
_BROWSER_PATH = _RUNTIME_DIR / "browser_cookies.json"
_FP_PATH = _RUNTIME_DIR / "buvid_fp.txt"

# 模块级缓存 (启动时 get() 第一次拉, 后续复用)
_cache: dict = {}


_META_KEYS = ("_source", "_note", "_comment")  # 注释/元数据字段, 非 cookie


def _load_browser_cookies() -> dict:
    """读 runtime/browser_cookies.json (CDP 真浏览器拿的). 失败返 {}.

    注意: B 站有 _uuid 这个 cookie 也以 _ 开头, 不能用 startswith("_") 一刀切过滤,
    用白名单 _META_KEYS.
    """
    try:
        if _BROWSER_PATH.exists():
            import json
            data = json.loads(_BROWSER_PATH.read_text())
            return {k: v for k, v in data.items() if k not in _META_KEYS}
    except Exception:
        pass
    return {}


def _get_or_create_fp() -> str:
    """读 / 生成持久 buvid_fp (32 位 hex)."""
    try:
        if _FP_PATH.exists():
            fp = _FP_PATH.read_text().strip()
            if len(fp) == 32 and all(c in "0123456789abcdef" for c in fp):
                return fp
    except Exception:
        pass
    fp = secrets.token_hex(16)
    try:
        _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        _FP_PATH.write_text(fp)
    except Exception:
        pass
    return fp


def get() -> dict:
    """返完整 cookie dict, 缓存. Key: buvid3/buvid4/b_nut/buvid_fp + 可选 ckMd5/_uuid/b_lsid/sid."""
    global _cache
    if _cache:
        return _cache

    # ① 优先借真浏览器拿的
    browser = _load_browser_cookies()
    if browser.get("buvid3") and browser.get("buvid4") and browser.get("buvid_fp"):
        _cache = browser
        return _cache

    # ② Fallback: SPI 匿名拉 buvid3/4, buvid_fp 用本地随机 hex
    out = {
        "buvid_fp": _get_or_create_fp(),
        "buvid3": "",
        "buvid4": "",
        "b_nut": str(int(time.time())),
    }
    try:
        r = requests.get(
            _SPI_URL,
            headers={"User-Agent": _UA, "Referer": "https://www.bilibili.com/"},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("code") == 0:
                d = data.get("data", {}) or {}
                out["buvid3"] = d.get("b_3", "")
                out["buvid4"] = d.get("b_4", "")
    except Exception:
        pass
    _cache = out
    return _cache


def reset():
    """清缓存, 强制下次 get() 重新加载 (eg. 怀疑 buvid 被 B 站拉黑时)."""
    global _cache
    _cache = {}
