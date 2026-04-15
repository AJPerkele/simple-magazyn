#!/bin/bash
# Skrypt do budowania paczki .deb dla Systemu Magazynowo-Sprzedażowego

set -e

echo "=========================================="
echo "Budowanie paczki .deb dla"
echo "System Magazynowo-Sprzedażowy v3.1"
echo "=========================================="

# Sprawdzenie wymaganych narzędzi
command -v dpkg-deb >/dev/null 2>&1 || { echo "Błąd: dpkg-deb nie jest zainstalowany. Zainstaluj dpkg."; exit 1; }

# Nazwa paczki
PACKAGE_NAME="system-magazynowy"
VERSION="3.1.0"
ARCH="all"
DEB_NAME="${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"

# Katalog roboczy
BUILD_DIR="deb_build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Tworzenie struktury katalogów
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/usr/bin"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/128x128/apps"
mkdir -p "$BUILD_DIR/usr/share/doc/${PACKAGE_NAME}"
mkdir -p "$BUILD_DIR/usr/share/${PACKAGE_NAME}"
mkdir -p "$BUILD_DIR/etc/${PACKAGE_NAME}"

# Kopiowanie plików kontrolnych
echo "Tworzenie plików kontrolnych..."
cat > "$BUILD_DIR/DEBIAN/control" << 'EOF'
Package: system-magazynowy
Version: 3.1.0
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.8), python3-pip, python3-venv, python3-pyqt6, python3-pyqt6.qtsvg
Recommends: python3-reportlab, python3-openpyxl, python3-requests
Maintainer: @AJPerkele <ajperkele@example.com>
Description: System magazynowo-sprzedażowy dla działalności nierejestrowanej
 System do zarządzania magazynem i sprzedażą z:
  - Dashboard z KPI i wykresami
  - Limitami sprzedaży 29 sztuk/rok/platforma
  - Generowaniem rachunków PDF
  - Raportami CSV/XLSX/PDF
  - Archiwizacją bazy danych
Homepage: https://github.com/AJPerkele/system-magazynowy
EOF

# Skrypt post-instalacyjny
cat > "$BUILD_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

echo "Instalowanie Systemu Magazynowo-Sprzedażowego..."

# Tworzenie katalogów dla użytkownika
if [ -d "/home" ]; then
    for user_home in /home/*; do
        if [ -d "$user_home" ]; then
            user=$(basename "$user_home")
            mkdir -p "$user_home/.local/share/system-magazynowy/rachunki"
            mkdir -p "$user_home/.local/share/system-magazynowy/backup"
            chown -R "$user:$user" "$user_home/.local/share/system-magazynowy" 2>/dev/null || true
        fi
    done
fi

# Tworzenie wirtualnego środowiska i instalacja zależności
cd /usr/share/system-magazynowy
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install reportlab openpyxl requests
fi

# Aktualizacja bazy danych menu
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database
fi

echo "Instalacja zakończona pomyślnie!"
echo "Aby uruchomić aplikację: system-magazynowy"
EOF

chmod 755 "$BUILD_DIR/DEBIAN/postinst"

# Skrypt przed-usunięciem
cat > "$BUILD_DIR/DEBIAN/prerm" << 'EOF'
#!/bin/bash
set -e

echo "Odinstalowywanie Systemu Magazynowo-Sprzedażowego..."
echo "Czy chcesz usunąć również dane użytkownika? (tak/nie)"
read -r answer
if [ "$answer" = "tak" ]; then
    rm -rf /usr/share/system-magazynowy
    for user_home in /home/*; do
        rm -rf "$user_home/.local/share/system-magazynowy"
    done
    echo "Dane użytkownika zostały usunięte."
fi
echo "Odinstalowanie zakończone."
EOF

chmod 755 "$BUILD_DIR/DEBIAN/prerm"

# Kopiowanie plików aplikacji
echo "Kopiowanie plików aplikacji..."

# Skrypt uruchomieniowy
cat > "$BUILD_DIR/usr/bin/system-magazynowy" << 'EOF'
#!/bin/bash
SCRIPT_DIR="/usr/share/system-magazynowy"
cd "$SCRIPT_DIR"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Sprawdzenie czy istnieje katalog danych użytkownika
USER_DATA_DIR="$HOME/.local/share/system-magazynowy"
mkdir -p "$USER_DATA_DIR/rachunki"
mkdir -p "$USER_DATA_DIR/backup"

# Linkowanie plików konfiguracyjnych jeśli nie istnieją
if [ ! -f "$USER_DATA_DIR/config.json" ] && [ -f "/etc/system-magazynowy/config.json.example" ]; then
    cp "/etc/system-magazynowy/config.json.example" "$USER_DATA_DIR/config.json"
fi

if [ ! -f "$USER_DATA_DIR/data.db" ]; then
    python3 -c "import sqlite3; conn = sqlite3.connect('$USER_DATA_DIR/data.db'); conn.close()" 2>/dev/null
fi

python3 magazyn.py "$@"

if [ $? -ne 0 ]; then
    echo ""
    echo "Wystąpił błąd podczas uruchamiania aplikacji."
    echo "Sprawdź czy masz zainstalowane wszystkie zależności:"
    echo "  sudo apt install python3-pyqt6 python3-reportlab python3-openpyxl python3-requests"
    exit 1
fi
EOF

chmod 755 "$BUILD_DIR/usr/bin/system-magazynowy"

# Skrót w menu
cat > "$BUILD_DIR/usr/share/applications/system-magazynowy.desktop" << 'EOF'
[Desktop Entry]
Version=3.1.0
Type=Application
Name=System Magazynowo-Sprzedażowy
Comment=Zarządzanie magazynem i sprzedażą dla działalności nierejestrowanej
Exec=/usr/bin/system-magazynowy
Icon=system-magazynowy
Terminal=false
Categories=Office;Finance;Accounting;
Keywords=magazyn;sprzedaż;rachunki;faktury;inwentaryzacja
StartupNotify=true
EOF

# Kopiowanie głównego pliku aplikacji
cp magazyn.py "$BUILD_DIR/usr/share/system-magazynowy/"

# Kopiowanie dokumentacji
cp README.md "$BUILD_DIR/usr/share/doc/${PACKAGE_NAME}/"
cp LICENSE "$BUILD_DIR/usr/share/doc/${PACKAGE_NAME}/"

# Tworzenie changelog
cat > "$BUILD_DIR/usr/share/doc/${PACKAGE_NAME}/changelog" << 'EOF'
system-magazynowy (3.1.0) stable; urgency=medium

  * Nowa wersja 3.1.0
  * Dodano motyw dzienny/nocny
  * Dodano limit sprzedaży 29 sztuk/rok/platforma
  * Dodano raporty CSV/XLSX/PDF
  * Dodano archiwizację bazy danych
  * Poprawiono FIFO dla kosztów zakupu

 -- @AJPerkele <ajperkele@example.com>  Wed, 08 Apr 2026 12:00:00 +0100
EOF

gzip -9 "$BUILD_DIR/usr/share/doc/${PACKAGE_NAME}/changelog"

# Konfiguracja przykładowa
cp config.json.example "$BUILD_DIR/etc/system-magazynowy/" 2>/dev/null || cat > "$BUILD_DIR/etc/system-magazynowy/config.json.example" << 'EOF'
{
  "database_path": "data.db",
  "invoice_counter": 1,
  "invoice_prefix": "R",
  "save_pdf": true,
  "theme": "day",
  "business_info": {},
  "invoice_config": {
    "seller_info": "",
    "footer_text": "Dziękuję za zakup!"
  },
  "limits": {
    "minimal_wage": 4666.0,
    "quarterly_multiplier": 2.25,
    "use_quarterly": true
  }
}
EOF

# Tworzenie ikony (proste SVG jako placeholder)
cat > "$BUILD_DIR/usr/share/icons/hicolor/128x128/apps/system-magazynowy.svg" << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <rect width="128" height="128" rx="20" fill="#C62828"/>
  <text x="64" y="45" font-size="28" text-anchor="middle" fill="white" font-weight="bold">M</text>
  <text x="64" y="75" font-size="28" text-anchor="middle" fill="white" font-weight="bold">S</text>
  <text x="64" y="105" font-size="16" text-anchor="middle" fill="#FFCDD2">v3.1</text>
</svg>
EOF

# Budowanie paczki .deb
echo "Budowanie paczki .deb..."
cd "$BUILD_DIR"
dpkg-deb --build . "../${DEB_NAME}"
cd ..

echo ""
echo "=========================================="
echo "Paczka .deb została utworzona:"
echo "  ${DEB_NAME}"
echo ""
echo "Instalacja:"
echo "  sudo dpkg -i ${DEB_NAME}"
echo "  sudo apt-get install -f  # naprawa zależności"
echo ""
echo "Odinstalowanie:"
echo "  sudo dpkg -r system-magazynowy"
echo "=========================================="

# Czyszczenie
rm -rf "$BUILD_DIR"