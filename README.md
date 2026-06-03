<div align="center">

# 🤖 Vbot

### B 站私信自动回复机器人 · 修 2026 风控版

[![Python](https://img.shields.io/badge/python-3.12+-0E7490.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-F59E0B.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-v1.0.0-0E7490.svg)](#)

Vbot 是基于 [@7Hello80/Bilibili_PrivateMessage_Bot v1.1.1](https://github.com/7Hello80/Bilibili_PrivateMessage_Bot) 的现代化重构. 主要解决了 2025-2026 期间 B 站升级 `web_im/send_msg` 风控导致原项目**发消息 100% HTTP 412 失败**的硬伤, 同时修了死循环 bug + 增强可观测性.

</div>

---

## ✨ Vbot vs 原版 BPMB v1.1.1 改进

| 维度 | 原版 BPMB v1.1.1 | Vbot v1.0.0 |
|---|---|---|
| 发消息 | ❌ HTTP 412 + HTML 风控页 (B 站 2025 升级后) | ✅ HTTP 200 + code 0 业务凭证 |
| Cookie 头 | 3 项 (SESSDATA + bili_jct + bili_ticket) | **13 项** (4 鉴权 + 9 设备指纹) |
| 设备指纹 | ❌ 无 | ✅ buvid3 / buvid4 / b_nut / buvid_fp / DedeUserID__ckMd5 / _uuid / b_lsid / sid |
| 指纹来源 | — | 优先借真实浏览器扫码 (`runtime/browser_cookies.json`), 没有则 SPI 匿名 + 本地持久 fp |
| 失败处理 | ❌ 死循环 (失败不标记 → 5s 一轮重试同一条) | ✅ 失败也 mark_processed (防 spam 触发更深风控) |
| 可观测性 | ❌ 只打 status_code | ✅ 打完整 response body + bili-trace-id headers |

## 🚀 快速开始

```bash
git clone https://github.com/heishiqing/Vbot-B.git
cd Vbot-B
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 web_panel.py
```

访问 http://127.0.0.1:5000, 默认账号 `admin` / `admin123` (**首次登录请立即改密码**).

### 配置账号
1. web 面板 → 账号管理 → 扫码登录
2. 关键词管理 → 加全局关键词或账号专属关键词
3. 启动机器人 → 实时回复就开始了

### 增强: 借真浏览器指纹 (推荐)
完全模拟"老设备" (B 站不当新设备风控), 用 CDP 抠真实浏览器登录后的 cookie 写到 `runtime/browser_cookies.json`:

```json
{
  "DedeUserID__ckMd5": "...",
  "_uuid": "...",
  "b_lsid": "...",
  "sid": "...",
  "buvid_fp": "...",
  "buvid3": "...",
  "buvid4": "...",
  "b_nut": "...",
  "bili_ticket_expires": "..."
}
```

模块 `buvid_spi.py` **优先**读这个文件; 没有则 fallback 调匿名 SPI 接口拿 buvid3/buvid4 + 本地生成 buvid_fp.

## 🛡️ 设计原则

- **不裸读 DB / 不绕过现有入库纪律** — bot 调 B 站官方 API, 不存私库
- **失败 fail-fast + 可观测** — 任何 HTTP 错误都打印 response body, 不让黑盒
- **设备指纹持久化** — buvid_fp 一旦生成不变, 模拟"老设备", 不每次启动都换
- **MIT 协议开源** — 致敬原作者 @7Hello80

## 🔐 安全 / 隐私

仓库严格脱敏, 以下文件**本地特有, 不入 git** (`.gitignore` 覆盖):

| 文件 | 含什么 |
|---|---|
| `config.json` | 账号 cookie (SESSDATA / bili_jct) + 关键词回复内容 |
| `panel_config.json` | web 面板 admin 密码 hash + GitHub OAuth |
| `runtime/browser_cookies.json` | 真实浏览器 9 项设备指纹 cookie |
| `runtime/buvid_fp.txt` | 持久 buvid_fp |
| `bot_runtime.log` | 私信收发流水 (含 talker_id + 消息文本) |
| `reply_state.json` | 已处理 msg_id 列表 |
| `message_activity.json` | 消息处理活动事件 |

部署或 fork 时, 这些文件**只在本地存在**. 仓库里不会找到任何真账号 cookie /
真私信内容 / 真关键词回复 / admin 密码.

## 📜 License

[MIT](LICENSE) · 基于 [@7Hello80/Bilibili_PrivateMessage_Bot](https://github.com/7Hello80/Bilibili_PrivateMessage_Bot) (MIT) fork

## 🙏 致谢

- 原项目 [@7Hello80/Bilibili_PrivateMessage_Bot v1.1.1](https://github.com/7Hello80/Bilibili_PrivateMessage_Bot) (淡意往事)

## 🐛 已知限制

- B 站 `web_im/send_msg` 不支持 self → self (会返 code 21026), 这是业务设计而非 bug
- bili_ticket 7 天过期, 长跑可能需要重新登录刷新 cookie
- 单 worker 部署假设, pending 状态都在进程内存; 多 worker 需 Redis (本项目暂不规划)
