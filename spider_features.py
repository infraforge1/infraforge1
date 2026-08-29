import secrets
import httpx


def generate_panel_api_key() -> str:
    return "spider_" + secrets.token_urlsafe(32)


def code_to_flag(code: str) -> str:
    code = (code or "").strip().upper()
    if len(code) != 2 or not code.isalpha():
        return "🌐"
    return "".join(chr(127397 + ord(c)) for c in code)


def node_region_prefix(country_code: str) -> str:
    return code_to_flag(country_code)


async def detect_server_info(client=None) -> dict:
    owns_client = client is None

    if owns_client:
        client = httpx.AsyncClient(timeout=10, follow_redirects=True)

    try:
        try:
            r = await client.get("https://ipwho.is/")
            data = r.json()

            if data.get("success", True):
                code = str(data.get("country_code") or "").upper()
                return {
                    "public_ip": data.get("ip", ""),
                    "country": data.get("country", ""),
                    "country_code": code,
                    "country_flag": code_to_flag(code),
                }
        except Exception:
            pass

        return {
            "public_ip": "",
            "country": "",
            "country_code": "",
            "country_flag": "🌐",
        }

    finally:
        if owns_client:
            await client.aclose()


async def tg_api_call(token: str, method: str, **params):
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"https://api.telegram.org/bot{token}/{method}",
            data=params,
        )

        try:
            data = r.json()
        except Exception:
            raise ValueError("Invalid response from Telegram")

        if not data.get("ok"):
            raise ValueError(
                data.get("description") or "Telegram API request failed"
            )

        return data.get("result")


async def validate_bot_token(token: str) -> dict:
    result = await tg_api_call(token, "getMe")
    if not isinstance(result, dict):
        raise ValueError("Bot token is invalid")
    return result


async def check_bot_channel_access(token: str, channel_id: str):
    bot = await validate_bot_token(token)

    result = await tg_api_call(
        token,
        "getChatMember",
        chat_id=channel_id,
        user_id=bot.get("id"),
    )

    status = (result or {}).get("status", "")

    if status not in ("administrator", "creator"):
        raise ValueError("Bot must be an administrator of the channel")

    return result
