import requests
from datetime import datetime, timedelta


def get_eur_rate(date_str: str) -> float:
    date = datetime.strptime(date_str, "%Y-%m-%d")

    for _ in range(7):
        d = date.strftime("%Y-%m-%d")
        try:
            r = requests.get(
                f"https://api.nbp.pl/api/exchangerates/rates/A/EUR/{d}/?format=json",
                timeout=3
            )
            if r.status_code == 200:
                return float(r.json()["rates"][0]["mid"])
        except Exception:
            pass
        date -= timedelta(days=1)

    return 4.50  # fallback
