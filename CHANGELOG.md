# Historia zmian

## [2.1.0] - 2026-01-06
### Dodano
- Kompletna historia rachunków z przeglądem i filtrowaniem
- Resetowanie numeracji rachunków
- Ewidencja uproszczona z narastającym liczeniem przychodów
- Konfiguracja wyglądu rachunków (prefiks, stopka, dane firmy)
- Analiza progu limitu działalności nierejestrowanej
- Eksport do Excel z formatowaniem i podsumowaniami

### Ulepszono
- Naprawione polskie znaki w generatorze PDF
- Usprawnione sortowanie tabel
- Optymalizacja bazy danych (nowe tabele historii)
- Lepsze komunikaty błędów w języku polskim
- Stabilność systemu FIFO

### Naprawiono
- Błędy w usuwaniu produktów z dodatnim stanem
- Problem z duplikacją ID w bazie danych
- Wycieki pamięci w interfejsie GUI
- Błędy w eksporcie CSV z polskimi znakami

## [2.0.0] - 2025-12-20
### Dodano
- Podstawowy system magazynowy
- Generowanie rachunków uproszczonych
- System FIFO dla kosztów zakupu
- Integracja z API NBP (kursy EUR)
- Eksport danych do CSV

## [1.0.0] - 2025-11-15
### Pierwsze wydanie
- Podstawowe zarządzanie produktami
- Ewidencja zakupów i sprzedaży
- Prosty interfejs GUI
- Baza danych SQLite
