# System Magazynowo-Sprzedażowy

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-GPLv3-green)
![Status](https://img.shields.io/badge/status-stable-brightgreen)

Kompleksowy system do zarządzania magazynem, sprzedażą i ewidencją dla działalności nierejestrowanej z uwzględnieniem polskich przepisów podatkowych.

## ✨ Kluczowe funkcje

### 🆕 Nowości w wersji 2.1.0
- ✅ **FB Marketplace** - dodano nową platformę sprzedażową
- ✅ **Własna nazwa platformy** - dla opcji "Inne" możesz wpisać dowolną nazwę
- ✅ **Limity kwartalne od 2026** - automatyczne obliczanie według nowych przepisów
- ✅ **Zapamiętywanie ostatniej bazy** - program pamięta którą bazę ostatnio otworzyłeś
- ✅ **Raporty kwartalne** - z automatycznymi obliczeniami limitów

### 🏪 Zarządzanie magazynem
- Dodawanie/edycja/usuwanie produktów
- Śledzenie stanów magazynowych
- System zakupów z automatycznym naliczaniem kosztów
- Inwentaryzacja z korektą stanów

### 💰 Sprzedaż i rachunki
- Dodawanie sprzedaży z automatycznym obliczaniem zysku (system FIFO)
- Generowanie rachunków uproszczonych w PDF
- Obsługa platform: Vinted, OLX, Allegro Lokalnie, FB Marketplace, własne nazwy
- Historia sprzedaży i rachunków

### 📊 Raporty i analizy
- Raporty miesięczne, kwartalne, roczne i okresowe
- Ewidencja dla Urzędu Skarbowego
- Automatyczne obliczanie limitów działalności nierejestrowanej
- Eksport do CSV, Excel (XLSX), PDF
- Bezpośrednie drukowanie z programu

### ⚙️ Zaawansowane funkcje
- Konfiguracja danych osobowych
- Ustawienia rachunków (numeracja, stopki, logo)
- Zarządzanie wieloma bazami danych
- Import/export danych
- Kopia zapasowa i archiwizacja
- Integracja z kursem EUR (NBP)

## 📦 Szybka instalacja

1. **Pobierz kod:**
```bash
git clone https://github.com/twoj-uzytkownik/system-magazynowy.git
cd system-magazynowy
```

2. **Zainstaluj zależności:**
```bash
pip install -r requirements.txt
```

3. **Uruchom program:**
```bash
python app.py
```

## 🚀 Szybki start

### Pierwsze uruchomienie
1. Program utworzy domyślną bazę `data.db`
2. Wprowadź swoje dane osobowe w **Konfiguracja → Dane osobiste**
3. Skonfiguruj limity US w **Konfiguracja → Dodatkowe → Limity US**

### Dodawanie produktów
1. Kliknij **➕ Dodaj produkt** na pasku narzędzi
2. Wprowadź SKU i nazwę produktu
3. Ustal stan początkowy (opcjonalnie)

### Sprzedaż z rachunkiem
1. Wybierz **💰 Dodaj sprzedaż**
2. Wybierz platformę (dla "Inne" możesz wpisać własną nazwę)
3. Dodaj produkty i ilości
4. System automatycznie obliczy koszt zakupu (FIFO)
5. Zaznacz "Wygeneruj rachunek uproszczony" jeśli potrzebujesz

### Generowanie raportów
1. Przejdź do **Raporty → Wybierz typ raportu**
2. Ustaw okres (miesiąc, kwartał, rok, lub własny zakres)
3. Wybierz format eksportu
4. Pobierz lub wydrukuj raport

## 📁 Struktura plików

```
system-magazynowy/
├── app.py              # Główna aplikacja
├── config.py           # Obsługa konfiguracji
├── db.py               # Baza danych SQLite
├── currency.py         # Kursy walut NBP
├── config.json         # Ustawienia użytkownika
├── data.db             # Domyślna baza danych
├── backups/            # Kopie zapasowe
├── rachunki/           # Wygenerowane rachunki
└── requirements.txt    # Wymagane pakiety
```

## ⚡ Wymagania minimalne

- **Python 3.8+**
- **Windows 10/11, macOS, lub Linux**
- **2GB RAM**
- **100MB wolnego miejsca na dysku**

## 📞 Wsparcie i pomoc

### Typowe problemy:
- **Brak openpyxl**: `pip install openpyxl`
- **Brak polskich znaków w PDF**: Zainstaluj czcionkę Arial
- **Nie można otworzyć bazy**: Użyj **Plik → Otwórz bazę danych**

### Raportowanie błędów:
1. Sprawdź Issues na GitHub
2. Podaj wersję systemu i Pythona
3. Dołącz zrzut ekranu błędu

## 📄 Licencja

**GNU General Public License v3.0**

- Możesz używać, modyfikować i rozpowszechniać
- Musisz udostępnić kod źródłowy modyfikacji
- Zmodyfikowane wersje muszą mieć tę samą licencję

## 🌟 Dlaczego ten system?

### Dla kogo jest ten program?
- **Sprzedawcy na Vinted/OLX** - ewidencja przychodów
- **Drobni przedsiębiorcy** - zarządzanie magazynem
- **Osoby na działalności nierejestrowanej** - rozliczenia z US
- **Kolekcjonerzy** - inwentaryzacja zbiorów

### Co wyróżnia ten system?
- 🎯 **Prosty interfejs** - bez zbędnych komplikacji
- 🏷️ **Polskie przepisy** - dostosowany do lokalnych wymagań
- 📊 **Automatyczne raporty** - gotowe do wydruku dla US
- 🔒 **Bezpieczeństwo danych** - lokalna baza SQLite
- 💰 **Darmowy i otwarty** - żadnych ukrytych kosztów

---

**Uwaga**: Program jest przeznaczony do użytku osobistego. Przed użyciem do celów biznesowych skonsultuj się z doradcą podatkowym.

*Wersja 2.1.0 | Styczeń 2024*
