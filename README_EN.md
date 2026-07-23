# 📈 419INU Price Monitor for Telegram

> A small private-chat-only allowlisted prototype that fetches one 419INU/USDT pair from DexScreener and edits a personal Telegram message with an estimated balance and PnL.

🌐 **Language:** [Русский](README.md) · [English](README_EN.md)

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![Aiogram](https://img.shields.io/badge/aiogram-3.0.0b7-2CA5E0?logo=telegram&logoColor=white)
![Data](https://img.shields.io/badge/Data-DexScreener-5B5BD6)
![Status](https://img.shields.io/badge/Status-prototype-F59E0B)

## ✨ Overview

The bot tracks a fixed BSC `$419INU/USDT` pair, accepts only Telegram user IDs listed in source, and remembers the latest message ID sent for each allowed user who runs `/start`.

> ⚠️ Use the bot only in a private chat. `USER_MESSAGES` is keyed by Telegram user ID, and the background editor reuses that ID as `chat_id`; a message created by `/start` in a group cannot be updated correctly.

| Area | Current behavior |
| --- | --- |
| 🎯 Market | One fixed DexScreener pair |
| 👤 Access | Local `USER_CONFIG` allowlist; private chat only |
| 💾 State | Process memory only |
| 🔄 Polling | A loop that sleeps for 6 seconds after processing users |
| 💰 Result | Estimated, not exchange-backed, balance and PnL |

## 🚀 Features

- USD price, 24-hour change, and market cap from DexScreener.
- One shared market-response cache with a 6-second TTL.
- Per-user `base_price` and `initial_balance`.
- One active message ID per user in a private chat; another `/start` makes a new message the update target.
- Message edits only when the displayed market values change.
- Access denial for IDs absent from `USER_CONFIG`.

## 🧮 Calculation model

The bot does not connect to a wallet and does not know the actual token quantity. It assumes the position value changes exactly in proportion to price:

```text
current_balance = price_usd / base_price × initial_balance
profit_percent  = (price_usd - base_price) / base_price × 100
PnL             = current_balance - initial_balance
```

`base_price` and `initial_balance` come from `USER_CONFIG`. Fees, slippage, buys, sells, transfers, and changes in token quantity are not included.

## 🔄 Execution flow

```text
/start in a private chat
  └─> check user_id against USER_CONFIG
       └─> synchronous DexScreener GET or 6-second cache
            └─> calculate balance / profit / PnL
                 └─> new Telegram message

background auto_update
  └─> iterate over USER_MESSAGES sequentially
       └─> fetch + calculate
            └─> edit_message_text only when values changed
                 └─> sleep(6)
```

The HTTP call uses `requests` inside an async handler/background task, so a network request blocks the event loop while it is running.

## 🏗️ Structure

```text
Token-DexScreener/
├── main.py              # Config, DexScreener client, handlers, and update loop
├── requirements.txt     # aiogram beta and requests
├── README.md            # Russian documentation
└── README_EN.md         # English documentation
```

## ⚙️ Installation

The project uses Python 3, but no exact version matrix is verified in CI.

```powershell
git clone https://github.com/soroka01/Token-DexScreener.git
cd Token-DexScreener
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On Linux/macOS, activate the environment with `source .venv/bin/activate`.

## 🔐 Current configuration

This version has no environment loader or separate config file. Before running it, edit `main.py` locally:

```python
BOT_TOKEN = "replace-with-telegram-token"

USER_CONFIG = {
    123456789: {
        "base_price": 0.000102,
        "initial_balance": 58.69,
    },
}
```

| Field | Purpose |
| --- | --- |
| `BOT_TOKEN` | Telegram bot token |
| `USER_CONFIG` key | Allowed Telegram user ID |
| `base_price` | Reference price for return calculations |
| `initial_balance` | Initial estimated position value in USD |

> ⚠️ Git tracks `main.py`. Never commit a real bot token or personal financial inputs. Keeping configuration in source is a known prototype limitation.

## ▶️ Running

```powershell
python main.py
```

After startup, an allowed user sends `/start`. An unknown ID receives an unsupported-user response.

## 🔗 Data source

The project calls one specific pair:

```text
https://api.dexscreener.com/latest/dex/pairs/bsc/0x597d9816ddb9624824591360180a70be6fd26182
```

The bot caches the API response itself. DexScreener or its CDN may also cache responses, so polling every 6 seconds does not guarantee a new price on every cycle.

## 🛡️ Security

- The bot reads public market data only and creates no transactions.
- The allowlist restricts `/start`, but it does not replace safe Telegram-token storage.
- Do not publish real Telegram IDs, tokens, or portfolio inputs.
- If a token is committed accidentally, revoke it through BotFather; deleting it in a later Git revision is not enough.

## ⚠️ Limitations

- Only one hard-coded BSC pair is supported; there is no network or asset selector.
- User state, cache, and message IDs disappear on restart.
- `requests.get()` is synchronous and has no timeout or retry.
- Users are processed sequentially, not concurrently.
- Group chats are unsupported: each message ID is stored by `user_id`, which the background editor later reuses as `chat_id`.
- Another `/start` creates an additional message; only the newest one continues to receive updates.
- The effective interval is total processing time plus `sleep(6)`.
- The displayed time is derived from HTTP `Expires`, converted to fixed UTC+5, and shifted by another 57 seconds; it is not a reliable trade or DexScreener-update timestamp.
- `get_current_time()` and the fetched `volume` are not used by the current interface.
- The project pins the old beta `aiogram==3.0.0b7`.
- There is no persistence, graceful task shutdown, or runtime configuration.

## 🧪 Testing

There are no automated tests or CI. Changes need at least:

- fixed-input checks for the formulas;
- mocked DexScreener responses and HTTP/JSON failure cases;
- allowlisted and unknown-user scenarios;
- cache-TTL and unchanged-message checks;
- a manual Telegram smoke test;
- `git diff --check`.

This is a recommended scope, not an existing automated pipeline.

## 📄 License

The repository has no `LICENSE` file. Publishing source code alone does not grant permission to use, modify, or redistribute it; the project owner must choose a license separately.

---

🧪 A compact prototype for one specific pair, with explicit assumptions instead of a full portfolio-tracker claim.
