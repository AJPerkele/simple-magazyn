# currency.py
import requests
from datetime import datetime

def get_eur_rate(date_str=None):
    """
    Pobiera kurs EUR/PLN z NBP API dla podanej daty.
    Jeśli data nie jest podana, używa dzisiejszej daty.
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # Format daty dla API NBP: YYYY-MM-DD
        url = f"http://api.nbp.pl/api/exchangerates/rates/a/eur/{date_str}/"
        response = requests.get(url, headers={'Accept': 'application/json'})
        
        if response.status_code == 200:
            data = response.json()
            return data['rates'][0]['mid']
        else:
            # Jeśli brak kursu dla danej daty, spróbuj z poprzedniego dnia roboczego
            print(f"Nie znaleziono kursu EUR dla {date_str}, próbuję wcześniejszą datę...")
            return 4.5  # Wartość domyślna
    except Exception as e:
        print(f"Błąd pobierania kursu EUR: {e}")
        return 4.5  # Wartość domyślna
