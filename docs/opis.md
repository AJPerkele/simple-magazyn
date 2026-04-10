# Architektura projektu

## Technologie

* Python
* PySide6 (GUI)
* SQLite (baza danych)
* Requests (API NBP)
* OpenPyXL (eksport Excel)

---

## Moduły

### 1. DB

* zarządzanie bazą SQLite
* migracje schematu
* operacje CRUD

### 2. Config

* konfiguracja aplikacji
* zapis JSON

### 3. GUI

* Dashboard
* Produkty
* Sprzedaż
* Zakupy

---

## Logika biznesowa

* FIFO dla kosztów
* kontrola limitu działalności
* statystyki roczne/miesięczne

---

## Możliwe rozszerzenia

* REST API
* wersja webowa
* integracja Allegro API
* eksport PDF (faktury VAT)
