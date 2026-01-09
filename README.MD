# 🏪 System Magazynowo-Sprzedażowy v2.1.0

<div align="center">
  
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-GPL%20v3.0-green)
![Version](https://img.shields.io/badge/version-2.1.0-orange)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20Mac-lightgrey)

**Kompletny system do zarządzania magazynem, sprzedażą i ewidencji dla działalności nierejestrowanej**

</div>

---

## 📋 Spis treści
- [✨ Funkcje](#-funkcje)
- [🚀 Szybki start](#-szybki-start)
- [🖥️ Instalacja](#️-instalacja)
- [📊 Przeznaczenie](#-przeznaczenie)
- [🔧 Konfiguracja](#-konfiguracja)
- [📁 Struktura projektu](#-struktura-projektu)
- [🤝 Wsparcie](#-wsparcie)
- [📄 Licencja](#-licencja)

---

## ✨ Funkcje

### 🏬 **Zarządzanie Magazynem**
- ✅ Dodawanie/usuwanie produktów z unikalnym SKU
- ✅ Śledzenie stanów magazynowych w czasie rzeczywistym
- ✅ System FIFO (First-In-First-Out) dla kosztów zakupu
- ✅ Inwentaryzacja z możliwością korekty stanów
- ✅ Historia zakupów i sprzedaży

### 💰 **Ewidencja Finansowa**
- ✅ Sprzedaż z wyborem platformy (Vinted, OLX, Allegro Lokalnie)
- ✅ Automatyczne kursy EUR z API NBP
- ✅ Kalkulacja zysków z kosztami FIFO
- ✅ Analiza rentowności produktów
- ✅ Eksport danych do CSV i Excel

### 🧾 **Rachunki Uproszczone**
- ✅ Automatyczne generowanie rachunków w PDF
- ✅ Konfigurowalna numeracja i wygląd
- ✅ Dane zgodne z wymogami Urzędu Skarbowego
- ✅ Historia rachunków z możliwością przeglądu
- ✅ Opcja automatycznego otwierania PDF

### 📊 **Raporty dla US**
- ✅ Ewidencja uproszczona z danymi osobowymi
- ✅ Automatyczne liczenie narastające przychodów
- ✅ Analiza progu limitu działalności nierejestrowanej
- ✅ Raporty miesięczne i roczne
- ✅ Podsumowania finansowe

### ⚙️ **Konfiguracja**
- ✅ Konfigurowalne dane sprzedawcy
- ✅ Ustawienia wyglądu rachunków
- ✅ Opcjonalne dane firmy
- ✅ Resetowanie numeracji
- ✅ Backup konfiguracji w JSON

---

## 🚀 Szybki start

### **Wymagania:**
- Python 3.8 lub nowszy
- SQLite3 (zazwyczaj preinstalowany)
- 100MB wolnego miejsca

### **Linux/Mac:**
```bash
# Pobierz i nadaj uprawnienia
chmod +x install.sh run.sh

# Uruchom instalator
./install.sh

# Uruchom aplikację
./run.sh
