import os
import requests


def send_telegram_message(message: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_API_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    print(f"[Telegram] token 앞 10자리: {token[:10]}...")
    print(f"[Telegram] chat_id: {chat_id}")

    if not token or not chat_id:
        print("[Telegram] 오류: 환경 변수가 비어 있습니다.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}

    print(f"[Telegram] 요청 URL: {url[:60]}...")
    print(f"[Telegram] payload: {payload}")

    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"[Telegram] HTTP 상태 코드: {response.status_code}")
        print(f"[Telegram] 응답 본문: {response.json()}")
        response.raise_for_status()
        print("[Telegram] 전송 성공!")
        return True
    except requests.HTTPError as e:
        print(f"[Telegram] HTTPError: {e}")
        return False
    except requests.RequestException as e:
        print(f"[Telegram] 네트워크 오류: {e}")
        return False
