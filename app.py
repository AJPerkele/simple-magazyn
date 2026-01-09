import sys
import os
from datetime import datetime, timedelta
from PySide6.QtWidgets import *
from PySide6.QtCore import QDate, Qt, QTimer, QSize
from PySide6.QtGui import QFont, QAction, QKeySequence, QIcon

from db import DB
from currency import get_eur_rate
from config import Config

PLATFORMS = ["Vinted", "OLX", "Allegro Lokalnie", "Inne"]

# ================== WERSJA ==================
try:
    from version import __version__, display_version
    APP_VERSION = __version__
except ImportError:
    APP_VERSION = "2.1.0"
    def display_version():
        print(f"System Magazynowo-Sprzedażowy v{APP_VERSION}")

# ================== STYL ==================
RED_WHITE_QSS = """
QWidget {
    background-color: white;
    font-family: Segoe UI, Arial;
    font-size: 12px;
    color: black
}
QPushButton {
    background-color: #c62828;
    color: white;
    padding: 6px 10px;
    border-radius: 6px;
}
QPushButton:hover {
    background-color: #b71c1c;
}
QHeaderView::section {
    background-color: #f2f2f2;
    padding: 4px;
    color: black;
    border: 1px solid #ddd;
}
QHeaderView::section:checked {
    background-color: #e0e0e0;
}
QTableWidget {
    border: 1px solid #ddd;
    color: black;
}
QTableWidget::item {
    padding: 4px;
}
QCheckBox {
    spacing: 5px;
}
QGroupBox {
    border: 1px solid #ddd;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
}
/* Styl dla menu ribbon - POPRAWIONE */
QMenuBar {
    background-color: #2c3e50;
    color: white;
    font-weight: bold;
    spacing: 5px;
}
QMenuBar::item {
    background-color: transparent;
    color: white;
    padding: 8px 15px;
    margin: 0 1px;
    border-radius: 3px;
}
QMenuBar::item:selected {
    background-color: #34495e;
}
QMenuBar::item:pressed {
    background-color: #2c3e50;
}
/* Menu rozwijane - POPRAWIONE DO POZIOMEGO */
QMenu {
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 3px;
    margin: 0;
    padding: 5px;
}
QMenu::item {
    padding: 8px 25px 8px 15px;
    margin: 2px 0;
    border-radius: 3px;
}
QMenu::item:selected {
    background-color: #c62828;
    color: white;
}
QMenu::item:disabled {
    color: #999;
}
QMenu::separator {
    height: 1px;
    background: #ddd;
    margin: 5px 10px;
}
/* Dla menu podręcznych - POPRAWIONE */
QMenu::right-arrow {
    image: none;
    width: 0;
}
/* Toolbar */
QToolBar {
    background-color: #f8f9fa;
    border-bottom: 1px solid #ddd;
    spacing: 5px;
    padding: 5px;
}
QToolButton {
    padding: 6px 10px;
    border-radius: 4px;
    margin: 0 2px;
    text-align: center;
}
QToolButton:hover {
    background-color: #e9ecef;
}
QToolButton:pressed {
    background-color: #dee2e6;
}
QToolButton[popupMode="1"] {
    padding-right: 20px;
}
/* Styl dla akcji */
QAction {
    spacing: 8px;
}
"""

# ================== POMOCNICZE ==================
def product_combo(db):
    combo = QComboBox()
    for p in db.list_products():
        combo.addItem(
            f"{p['id']} | {p['sku']} | {p['title']}",
            p["id"]
        )
    return combo

# ================== DIALOG DODAWANIA PRODUKTU ==================
class AddProductDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Dodaj nowy produkt")
        self.resize(400, 200)

        v = QVBoxLayout(self)

        # Formularz
        form = QFormLayout()

        self.sku_input = QLineEdit()
        self.sku_input.setPlaceholderText("np. PROD001")
        form.addRow("SKU:", self.sku_input)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("np. Koszulka bawełniana")
        form.addRow("Nazwa:", self.title_input)

        self.initial_stock = QSpinBox()
        self.initial_stock.setRange(0, 100000)
        self.initial_stock.setValue(0)
        form.addRow("Stan początkowy:", self.initial_stock)

        v.addLayout(form)

        # Przyciski
        button_layout = QHBoxLayout()
        
        btn_save = QPushButton("Zapisz")
        btn_save.clicked.connect(self.save_product)
        btn_save.setStyleSheet("background-color: #2E7D32; font-weight: bold;")
        
        btn_cancel = QPushButton("Anuluj")
        btn_cancel.clicked.connect(self.reject)
        
        button_layout.addWidget(btn_save)
        button_layout.addWidget(btn_cancel)
        v.addLayout(button_layout)

    def save_product(self):
        sku = self.sku_input.text().strip()
        title = self.title_input.text().strip()
        
        if not sku:
            QMessageBox.warning(self, "Błąd", "SKU nie może być puste.")
            return
            
        if not title:
            QMessageBox.warning(self, "Błąd", "Nazwa nie może być pusta.")
            return
        
        try:
            # Sprawdź czy SKU już istnieje
            existing = self.db.check_sku_exists(sku)
            if existing:
                QMessageBox.warning(self, "Błąd", f"SKU '{sku}' już istnieje w bazie.")
                return
            
            # Dodaj produkt
            self.db.add_product(sku, title)
            
            # Jeśli stan początkowy > 0, dodaj zakup
            initial_qty = self.initial_stock.value()
            if initial_qty > 0:
                pid = self.db.get_product_id_by_sku(sku)
                if pid:
                    self.db.add_purchase_order(
                        0.0,
                        datetime.now().strftime("%Y-%m-%d"),
                        [(pid, initial_qty)]
                    )
            
            QMessageBox.information(self, "Sukces", "Produkt został dodany.")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie udało się dodać produktu:\n{str(e)}")

# ================== DIALOG KONFIGURACJI DANYCH OSOBOWYCH ==================
class BusinessInfoDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Dane osobiste dla ewidencji uproszczonej")
        self.resize(500, 400)
        
        v = QVBoxLayout(self)
        
        info = self.config.get_business_info()
        
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setText(info.get("name", ""))
        self.name_input.setPlaceholderText("Imię i nazwisko")
        form.addRow("Imię i nazwisko:", self.name_input)
        
        self.address_input = QLineEdit()
        self.address_input.setText(info.get("address", ""))
        self.address_input.setPlaceholderText("Ulica, nr domu/mieszkania")
        form.addRow("Adres zamieszkania:", self.address_input)
        
        self.postal_input = QLineEdit()
        self.postal_input.setText(info.get("postal_code", ""))
        self.postal_input.setPlaceholderText("00-000")
        form.addRow("Kod pocztowy:", self.postal_input)
        
        self.city_input = QLineEdit()
        self.city_input.setText(info.get("city", ""))
        self.city_input.setPlaceholderText("Miejscowość")
        form.addRow("Miejscowość:", self.city_input)
        
        self.pesel_input = QLineEdit()
        self.pesel_input.setText(info.get("pesel", ""))
        self.pesel_input.setPlaceholderText("11-cyfrowy numer PESEL")
        form.addRow("PESEL:", self.pesel_input)
        
        self.nip_input = QLineEdit()
        self.nip_input.setText(info.get("nip", ""))
        self.nip_input.setPlaceholderText("NIP (opcjonalnie)")
        form.addRow("NIP:", self.nip_input)
        
        self.regon_input = QLineEdit()
        self.regon_input.setText(info.get("regon", ""))
        self.regon_input.setPlaceholderText("REGON (opcjonalnie)")
        form.addRow("REGON:", self.regon_input)
        
        v.addLayout(form)
        
        # Przyciski
        button_layout = QHBoxLayout()
        
        btn_save = QPushButton("Zapisz")
        btn_save.clicked.connect(self.save_info)
        btn_save.setStyleSheet("background-color: #2E7D32; font-weight: bold;")
        
        btn_cancel = QPushButton("Anuluj")
        btn_cancel.clicked.connect(self.reject)
        
        button_layout.addWidget(btn_save)
        button_layout.addWidget(btn_cancel)
        
        v.addLayout(button_layout)
    
    def save_info(self):
        info = {
            "name": self.name_input.text().strip(),
            "address": self.address_input.text().strip(),
            "postal_code": self.postal_input.text().strip(),
            "city": self.city_input.text().strip(),
            "pesel": self.pesel_input.text().strip(),
            "nip": self.nip_input.text().strip(),
            "regon": self.regon_input.text().strip()
        }
        
        # Walidacja
        if not info["name"]:
            QMessageBox.warning(self, "Błąd", "Imię i nazwisko jest wymagane.")
            return
            
        if not info["address"]:
            QMessageBox.warning(self, "Błąd", "Adres jest wymagany.")
            return
            
        if not info["postal_code"]:
            QMessageBox.warning(self, "Błąd", "Kod pocztowy jest wymagany.")
            return
            
        if not info["city"]:
            QMessageBox.warning(self, "Błąd", "Miejscowość jest wymagana.")
            return
            
        if not info["pesel"] or len(info["pesel"]) != 11 or not info["pesel"].isdigit():
            QMessageBox.warning(self, "Błąd", "PESEL musi składać się z 11 cyfr.")
            return
        
        self.config.update_business_info(info)
        QMessageBox.information(self, "Sukces", "Dane zostały zapisane.")
        self.accept()

# ================== DIALOG KONFIGURACJI LIMITÓW ==================
class LimitsConfigDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Konfiguracja limitów US")
        self.resize(600, 500)
        
        v = QVBoxLayout(self)
        
        # Informacja o limitach
        info_group = QGroupBox("Informacje o limitach")
        info_layout = QVBoxLayout()
        
        info_text = QLabel(
            "<b>Od 2026 roku w Polsce obowiązują limity kwartalne dla działalności nierejestrowanej:</b><br><br>"
            "• <b>Limit miesięczny:</b> 75% minimalnego wynagrodzenia<br>"
            "• <b>Limit kwartalny:</b> 225% minimalnego wynagrodzenia<br><br>"
            "System automatycznie oblicza limity na podstawie wprowadzonej kwoty minimalnego wynagrodzenia."
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        info_group.setLayout(info_layout)
        v.addWidget(info_group)
        
        # Grupa: Ogólne ustawienia
        gb_general = QGroupBox("Ogólne ustawienia limitów")
        general_layout = QFormLayout()
        
        self.minimal_wage_input = QDoubleSpinBox()
        self.minimal_wage_input.setRange(0, 10000)
        self.minimal_wage_input.setDecimals(2)
        self.minimal_wage_input.setSuffix(" PLN")
        self.minimal_wage_input.setSingleStep(100)
        
        self.quarterly_multiplier_input = QDoubleSpinBox()
        self.quarterly_multiplier_input.setRange(0, 10)
        self.quarterly_multiplier_input.setDecimals(2)
        self.quarterly_multiplier_input.setSuffix("%")
        self.quarterly_multiplier_input.setSingleStep(0.25)
        
        self.use_quarterly_cb = QCheckBox("Używaj limitów kwartalnych (od 2026 roku)")
        self.use_quarterly_cb.setChecked(True)
        
        general_layout.addRow("Minimalne wynagrodzenie:", self.minimal_wage_input)
        general_layout.addRow("Mnożnik limitu kwartalnego:", self.quarterly_multiplier_input)
        general_layout.addRow("", self.use_quarterly_cb)
        
        gb_general.setLayout(general_layout)
        v.addWidget(gb_general)
        
        # Grupa: Limity dla poszczególnych lat
        gb_years = QGroupBox("Limity dla poszczególnych lat")
        years_layout = QVBoxLayout()
        
        self.years_table = QTableWidget()
        self.years_table.setColumnCount(5)
        self.years_table.setHorizontalHeaderLabels(["Rok", "Minimalne wynagrodzenie", "Limit miesięczny", "Limit kwartalny", "Edytuj"])
        self.years_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        years_layout.addWidget(self.years_table)
        gb_years.setLayout(years_layout)
        v.addWidget(gb_years)
        
        # Obliczone wartości
        gb_calculated = QGroupBox("Obliczone wartości (aktualne)")
        calculated_layout = QVBoxLayout()
        
        self.calculated_label = QLabel()
        self.calculated_label.setStyleSheet("font-weight: bold;")
        calculated_layout.addWidget(self.calculated_label)
        
        gb_calculated.setLayout(calculated_layout)
        v.addWidget(gb_calculated)
        
        # Przyciski
        button_layout = QHBoxLayout()
        
        btn_save = QPushButton("Zapisz konfigurację")
        btn_save.clicked.connect(self.save_config)
        btn_save.setStyleSheet("background-color: #2E7D32; font-weight: bold;")
        
        btn_calculate = QPushButton("Przelicz")
        btn_calculate.clicked.connect(self.calculate_values)
        
        btn_add_year = QPushButton("Dodaj rok")
        btn_add_year.clicked.connect(self.add_year)
        
        btn_cancel = QPushButton("Anuluj")
        btn_cancel.clicked.connect(self.reject)
        
        button_layout.addWidget(btn_save)
        button_layout.addWidget(btn_calculate)
        button_layout.addWidget(btn_add_year)
        button_layout.addWidget(btn_cancel)
        
        v.addLayout(button_layout)
        
        self.load_config()
        self.calculate_values()
    
    def load_config(self):
        """Wczytuje aktualną konfigurację"""
        limits_config = self.config.get_limits_config()
        
        # Ogólne ustawienia
        self.minimal_wage_input.setValue(limits_config.get("minimal_wage", 4242.00))
        self.quarterly_multiplier_input.setValue(limits_config.get("quarterly_limit_multiplier", 2.25))
        self.use_quarterly_cb.setChecked(limits_config.get("use_quarterly_limits", True))
        
        # Tabela z latami
        self.load_years_table()
    
    def load_years_table(self):
        """Wczytuje dane lat do tabeli"""
        limits_config = self.config.get_limits_config()
        year_limits = limits_config.get("year_limits", {})
        
        years = sorted(year_limits.keys(), key=lambda x: int(x))
        self.years_table.setRowCount(len(years))
        
        for i, year in enumerate(years):
            data = year_limits[year]
            
            # Rok
            self.years_table.setItem(i, 0, QTableWidgetItem(year))
            
            # Minimalne wynagrodzenie
            wage_item = QTableWidgetItem(f"{data.get('minimal_wage', 0):.2f} PLN")
            wage_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.years_table.setItem(i, 1, wage_item)
            
            # Limit miesięczny
            monthly_limit = data.get('minimal_wage', 0) * 0.75
            monthly_item = QTableWidgetItem(f"{monthly_limit:.2f} PLN")
            monthly_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.years_table.setItem(i, 2, monthly_item)
            
            # Limit kwartalny
            quarterly_limit = data.get('minimal_wage', 0) * data.get('quarterly_limit_multiplier', 2.25)
            quarterly_item = QTableWidgetItem(f"{quarterly_limit:.2f} PLN")
            quarterly_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.years_table.setItem(i, 3, quarterly_item)
            
            # Przycisk edycji
            edit_btn = QPushButton("Edytuj")
            edit_btn.clicked.connect(lambda checked, y=year: self.edit_year(y))
            self.years_table.setCellWidget(i, 4, edit_btn)
    
    def calculate_values(self):
        """Przelicza wartości na podstawie wprowadzonych danych"""
        minimal_wage = self.minimal_wage_input.value()
        quarterly_multiplier = self.quarterly_multiplier_input.value()
        
        monthly_limit = minimal_wage * 0.75
        quarterly_limit = minimal_wage * quarterly_multiplier
        
        self.calculated_label.setText(
            f"<b>Obliczone wartości (aktualne ustawienia):</b><br>"
            f"Minimalne wynagrodzenie: {minimal_wage:.2f} PLN<br>"
            f"Limit miesięczny (75%): {monthly_limit:.2f} PLN<br>"
            f"Limit kwartalny ({quarterly_multiplier*100:.0f}%): {quarterly_limit:.2f} PLN"
        )
    
    def add_year(self):
        """Dodaje nowy rok do konfiguracji"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Dodaj nowy rok")
        dialog.resize(300, 200)
        
        layout = QVBoxLayout(dialog)
        
        form = QFormLayout()
        
        year_spin = QSpinBox()
        year_spin.setRange(2000, 2100)
        year_spin.setValue(datetime.now().year)
        form.addRow("Rok:", year_spin)
        
        wage_input = QDoubleSpinBox()
        wage_input.setRange(0, 10000)
        wage_input.setDecimals(2)
        wage_input.setValue(self.minimal_wage_input.value())
        wage_input.setSuffix(" PLN")
        form.addRow("Minimalne wynagrodzenie:", wage_input)
        
        layout.addLayout(form)
        
        button_layout = QHBoxLayout()
        btn_ok = QPushButton("Dodaj")
        btn_ok.clicked.connect(dialog.accept)
        btn_cancel = QPushButton("Anuluj")
        btn_cancel.clicked.connect(dialog.reject)
        
        button_layout.addWidget(btn_ok)
        button_layout.addWidget(btn_cancel)
        layout.addLayout(button_layout)
        
        if dialog.exec():
            year = year_spin.value()
            minimal_wage = wage_input.value()
            
            # Dodaj rok do konfiguracji
            config = {
                "minimal_wage": minimal_wage,
                "monthly_limit": minimal_wage * 0.75,
                "quarterly_limit": minimal_wage * self.quarterly_multiplier_input.value()
            }
            
            self.config.update_year_limit_config(year, config)
            self.load_years_table()
    
    def edit_year(self, year):
        """Edytuje konfigurację dla danego roku"""
        limits_config = self.config.get_limits_config()
        year_limits = limits_config.get("year_limits", {})
        
        if str(year) not in year_limits:
            QMessageBox.warning(self, "Błąd", f"Nie znaleziono konfiguracji dla roku {year}")
            return
        
        config = year_limits[str(year)]
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edytuj rok {year}")
        dialog.resize(300, 200)
        
        layout = QVBoxLayout(dialog)
        
        form = QFormLayout()
        
        year_label = QLabel(str(year))
        form.addRow("Rok:", year_label)
        
        wage_input = QDoubleSpinBox()
        wage_input.setRange(0, 10000)
        wage_input.setDecimals(2)
        wage_input.setValue(config.get("minimal_wage", self.minimal_wage_input.value()))
        wage_input.setSuffix(" PLN")
        form.addRow("Minimalne wynagrodzenie:", wage_input)
        
        layout.addLayout(form)
        
        button_layout = QHBoxLayout()
        btn_save = QPushButton("Zapisz")
        btn_save.clicked.connect(dialog.accept)
        btn_delete = QPushButton("Usuń")
        btn_delete.clicked.connect(lambda: self.delete_year(year, dialog))
        btn_cancel = QPushButton("Anuluj")
        btn_cancel.clicked.connect(dialog.reject)
        
        button_layout.addWidget(btn_save)
        button_layout.addWidget(btn_delete)
        button_layout.addWidget(btn_cancel)
        layout.addLayout(button_layout)
        
        if dialog.exec():
            minimal_wage = wage_input.value()
            
            # Zaktualizuj konfigurację
            config = {
                "minimal_wage": minimal_wage,
                "monthly_limit": minimal_wage * 0.75,
                "quarterly_limit": minimal_wage * self.quarterly_multiplier_input.value()
            }
            
            self.config.update_year_limit_config(year, config)
            self.load_years_table()
    
    def delete_year(self, year, dialog):
        """Usuwa konfigurację dla danego roku"""
        if QMessageBox.question(self, "Potwierdź usunięcie", 
                               f"Czy na pewno usunąć konfigurację dla roku {year}?") == QMessageBox.Yes:
            limits_config = self.config.get_limits_config()
            if "year_limits" in limits_config and str(year) in limits_config["year_limits"]:
                del limits_config["year_limits"][str(year)]
                self.config.update_limits_config(limits_config)
                self.load_years_table()
                dialog.reject()
    
    def save_config(self):
        """Zapisuje konfigurację limitów"""
        limits_info = {
            "minimal_wage": self.minimal_wage_input.value(),
            "quarterly_limit_multiplier": self.quarterly_multiplier_input.value(),
            "use_quarterly_limits": self.use_quarterly_cb.isChecked()
        }
        
        self.config.update_limits_config(limits_info)
        QMessageBox.information(self, "Sukces", "Konfiguracja limitów została zapisana.")
        self.accept()

# ================== DIALOG KONFIGURACJI RACHUNKÓW ==================
class InvoiceConfigDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Konfiguracja rachunków")
        self.resize(500, 400)
        
        v = QVBoxLayout(self)
        
        # Grupa: Numeracja
        gb_numbering = QGroupBox("Numeracja rachunków")
        numbering_layout = QFormLayout()
        
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("np. FS, INV, RACH")
        
        self.start_number = QSpinBox()
        self.start_number.setRange(1, 999999)
        self.start_number.setValue(1)
        
        self.digits_input = QSpinBox()
        self.digits_input.setRange(1, 8)
        self.digits_input.setValue(6)
        self.digits_input.setSuffix(" cyfr")
        
        numbering_layout.addRow("Prefiks:", self.prefix_input)
        numbering_layout.addRow("Rozpocznij od:", self.start_number)
        numbering_layout.addRow("Ilość cyfr:", self.digits_input)
        
        gb_numbering.setLayout(numbering_layout)
        v.addWidget(gb_numbering)
        
        # Grupa: Wygląd
        gb_appearance = QGroupBox("Wygląd rachunku")
        appearance_layout = QFormLayout()
        
        self.company_name = QLineEdit()
        self.company_name.setPlaceholderText("Nazwa firmy (opcjonalnie)")
        
        self.company_address = QLineEdit()
        self.company_address.setPlaceholderText("Adres firmy (opcjonalnie)")
        
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Telefon kontaktowy")
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email kontaktowy")
        
        self.footer_text = QTextEdit()
        self.footer_text.setMaximumHeight(80)
        self.footer_text.setPlaceholderText("Tekst stopki rachunku...")
        
        appearance_layout.addRow("Nazwa firmy:", self.company_name)
        appearance_layout.addRow("Adres firmy:", self.company_address)
        appearance_layout.addRow("Telefon:", self.phone_input)
        appearance_layout.addRow("Email:", self.email_input)
        appearance_layout.addRow("Stopka:", self.footer_text)
        
        gb_appearance.setLayout(appearance_layout)
        v.addWidget(gb_appearance)
        
        # Grupa: Ustawienia dodatkowe
        gb_advanced = QGroupBox("Ustawienia zaawansowane")
        advanced_layout = QVBoxLayout()
        
        self.auto_open_cb = QCheckBox("Automatycznie otwieraj wygenerowany rachunek")
        self.auto_open_cb.setChecked(True)
        
        self.save_pdf_cb = QCheckBox("Zapisuj kopię PDF w folderze rachunki/")
        self.save_pdf_cb.setChecked(True)
        
        self.include_logo_cb = QCheckBox("Dołącz logo firmy (jeśli dostępne)")
        self.include_logo_cb.setChecked(False)
        
        advanced_layout.addWidget(self.auto_open_cb)
        advanced_layout.addWidget(self.save_pdf_cb)
        advanced_layout.addWidget(self.include_logo_cb)
        advanced_layout.addStretch()
        
        gb_advanced.setLayout(advanced_layout)
        v.addWidget(gb_advanced)
        
        # Przyciski
        button_layout = QHBoxLayout()
        
        btn_save = QPushButton("Zapisz konfigurację")
        btn_save.clicked.connect(self.save_config)
        btn_save.setStyleSheet("background-color: #2E7D32; font-weight: bold;")
        
        btn_cancel = QPushButton("Anuluj")
        btn_cancel.clicked.connect(self.reject)
        
        btn_reset = QPushButton("Przywróć domyślne")
        btn_reset.clicked.connect(self.reset_to_default)
        
        button_layout.addWidget(btn_save)
        button_layout.addWidget(btn_reset)
        button_layout.addWidget(btn_cancel)
        
        v.addLayout(button_layout)
        
        self.load_current_config()
    
    def load_current_config(self):
        """Wczytuje aktualną konfigurację"""
        config_data = self.config.load()
        
        # Numeracja
        invoice_config = config_data.get("invoice", {})
        self.prefix_input.setText(invoice_config.get("prefix", "FS"))
        self.start_number.setValue(invoice_config.get("next_number", 1))
        
        # Wygląd
        business_info = config_data.get("business", {})
        self.company_name.setText(business_info.get("company_name", ""))
        self.company_address.setText(business_info.get("company_address", ""))
        self.phone_input.setText(business_info.get("phone", ""))
        self.email_input.setText(business_info.get("email", ""))
        self.footer_text.setText(invoice_config.get("footer_text", "Dziękujemy za zakupy!"))
        
        # Ustawienia zaawansowane
        self.auto_open_cb.setChecked(invoice_config.get("auto_open", True))
        self.save_pdf_cb.setChecked(invoice_config.get("save_pdf", True))
        self.include_logo_cb.setChecked(invoice_config.get("include_logo", False))
        
        # Ilość cyfr (domyślnie 6)
        self.digits_input.setValue(invoice_config.get("digits", 6))
    
    def save_config(self):
        """Zapisuje konfigurację"""
        config_data = self.config.load()
        
        # Numeracja
        config_data.setdefault("invoice", {})
        config_data["invoice"]["prefix"] = self.prefix_input.text().strip() or "FS"
        config_data["invoice"]["next_number"] = self.start_number.value()
        config_data["invoice"]["digits"] = self.digits_input.value()
        config_data["invoice"]["footer_text"] = self.footer_text.toPlainText().strip() or "Dziękujemy za zakupy!"
        config_data["invoice"]["auto_open"] = self.auto_open_cb.isChecked()
        config_data["invoice"]["save_pdf"] = self.save_pdf_cb.isChecked()
        config_data["invoice"]["include_logo"] = self.include_logo_cb.isChecked()
        
        # Informacje o firmie
        config_data.setdefault("business", {})
        config_data["business"]["company_name"] = self.company_name.text().strip()
        config_data["business"]["company_address"] = self.company_address.text().strip()
        config_data["business"]["phone"] = self.phone_input.text().strip()
        config_data["business"]["email"] = self.email_input.text().strip()
        
        # Zapisz
        self.config.data = config_data
        self.config.save()
        
        QMessageBox.information(self, "Sukces", "Konfiguracja rachunków została zapisana.")
        self.accept()
    
    def reset_to_default(self):
        """Przywraca domyślne ustawienia"""
        reply = QMessageBox.question(
            self, "Przywróć domyślne",
            "Czy na pewno chcesz przywrócić domyślne ustawienia rachunków?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Resetuj pola do domyślnych wartości
            self.prefix_input.setText("FS")
            self.start_number.setValue(1)
            self.digits_input.setValue(6)
            self.company_name.clear()
            self.company_address.clear()
            self.phone_input.clear()
            self.email_input.clear()
            self.footer_text.setText("Dziękujemy za zakupy!")
            self.auto_open_cb.setChecked(True)
            self.save_pdf_cb.setChecked(True)
            self.include_logo_cb.setChecked(False)

# ================== DIALOG RAPORTU (z drukowaniem) ==================
class ReportDialog(QDialog):
    def __init__(self, db, config, parent=None, report_type="monthly"):
        super().__init__(parent)
        self.db = db
        self.config = config
        self.report_type = report_type  # "monthly", "yearly", "quarterly", "custom"
        
        if report_type == "monthly":
            self.setWindowTitle("Generuj raport miesięczny")
        elif report_type == "yearly":
            self.setWindowTitle("Generuj raport roczny")
        elif report_type == "quarterly":
            self.setWindowTitle("Generuj raport kwartalny")
        else:
            self.setWindowTitle("Generuj raport okresowy")
            
        self.resize(500, 600)

        v = QVBoxLayout(self)

        # Typ raportu (tylko informacyjnie)
        gb_type = QGroupBox("Typ raportu")
        type_layout = QVBoxLayout()
        
        if report_type == "monthly":
            self.type_label = QLabel("Raport miesięczny")
        elif report_type == "yearly":
            self.type_label = QLabel("Raport roczny")
        elif report_type == "quarterly":
            self.type_label = QLabel("Raport kwartalny")
        else:
            self.type_label = QLabel("Raport okresowy")
            
        self.type_label.setStyleSheet("font-weight: bold; color: #2E7D32;")
        type_layout.addWidget(self.type_label)
        gb_type.setLayout(type_layout)
        v.addWidget(gb_type)

        # Kontenery dla różnych typów raportów
        if report_type == "monthly":
            self.monthly_widget = QWidget()
            monthly_layout = QHBoxLayout(self.monthly_widget)
            self.month_combo = QComboBox()
            self.month_combo.addItems([
                "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",
                "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"
            ])
            self.month_combo.setCurrentIndex(datetime.now().month - 1)
            
            self.year_spin = QSpinBox()
            self.year_spin.setRange(2000, 2100)
            self.year_spin.setValue(datetime.now().year)
            
            monthly_layout.addWidget(QLabel("Miesiąc:"))
            monthly_layout.addWidget(self.month_combo)
            monthly_layout.addWidget(QLabel("Rok:"))
            monthly_layout.addWidget(self.year_spin)
            monthly_layout.addStretch()
            
            v.addWidget(self.monthly_widget)
            
        elif report_type == "yearly":
            self.yearly_widget = QWidget()
            yearly_layout = QHBoxLayout(self.yearly_widget)
            self.year_only_spin = QSpinBox()
            self.year_only_spin.setRange(2000, 2100)
            self.year_only_spin.setValue(datetime.now().year)
            
            yearly_layout.addWidget(QLabel("Rok:"))
            yearly_layout.addWidget(self.year_only_spin)
            yearly_layout.addStretch()
            
            v.addWidget(self.yearly_widget)
            
        elif report_type == "quarterly":
            self.quarterly_widget = QWidget()
            quarterly_layout = QHBoxLayout(self.quarterly_widget)
            
            self.quarter_combo = QComboBox()
            self.quarter_combo.addItems([
                "I kwartał (styczeń-marzec)",
                "II kwartał (kwiecień-czerwiec)",
                "III kwartał (lipiec-wrzesień)",
                "IV kwartał (październik-grudzień)"
            ])
            
            # Ustal bieżący kwartał
            current_month = datetime.now().month
            current_quarter = (current_month - 1) // 3
            self.quarter_combo.setCurrentIndex(current_quarter)
            
            self.quarter_year_spin = QSpinBox()
            self.quarter_year_spin.setRange(2000, 2100)
            self.quarter_year_spin.setValue(datetime.now().year)
            
            quarterly_layout.addWidget(QLabel("Kwartał:"))
            quarterly_layout.addWidget(self.quarter_combo)
            quarterly_layout.addWidget(QLabel("Rok:"))
            quarterly_layout.addWidget(self.quarter_year_spin)
            quarterly_layout.addStretch()
            
            v.addWidget(self.quarterly_widget)
            
        else:  # custom
            self.custom_widget = QWidget()
            custom_layout = QHBoxLayout(self.custom_widget)
            self.date_from = QDateEdit(QDate.currentDate().addMonths(-1))
            self.date_from.setCalendarPopup(True)
            self.date_to = QDateEdit(QDate.currentDate())
            self.date_to.setCalendarPopup(True)
            
            custom_layout.addWidget(QLabel("Od:"))
            custom_layout.addWidget(self.date_from)
            custom_layout.addWidget(QLabel("Do:"))
            custom_layout.addWidget(self.date_to)
            custom_layout.addStretch()
            
            v.addWidget(self.custom_widget)

        # Format eksportu
        gb_format = QGroupBox("Format eksportu")
        format_layout = QHBoxLayout()
        
        self.rb_csv = QRadioButton("CSV")
        self.rb_csv.setChecked(True)
        self.rb_excel = QRadioButton("Excel (XLSX)")
        self.rb_pdf = QRadioButton("PDF")
        
        format_layout.addWidget(self.rb_csv)
        format_layout.addWidget(self.rb_excel)
        format_layout.addWidget(self.rb_pdf)
        format_layout.addStretch()
        gb_format.setLayout(format_layout)
        v.addWidget(gb_format)

        # Szczegółowość
        gb_detail = QGroupBox("Szczegółowość")
        detail_layout = QVBoxLayout()
        
        self.cb_purchases = QCheckBox("Uwzględnij zakupy")
        self.cb_purchases.setChecked(True)
        self.cb_sales = QCheckBox("Uwzględnij sprzedaż")
        self.cb_sales.setChecked(True)
        self.cb_summary = QCheckBox("Podsumowanie finansowe")
        self.cb_summary.setChecked(True)
        self.cb_products = QCheckBox("Lista produktów ze stanem")
        self.cb_products.setChecked(False)
        
        self.cb_simple_register = QCheckBox("Uproszczony rejestr sprzedaży z danymi osobowymi")
        self.cb_simple_register.setChecked(False)
        self.cb_simple_register.setToolTip("Wymagane pola dla uproszczonego rozliczenia")
        
        detail_layout.addWidget(self.cb_purchases)
        detail_layout.addWidget(self.cb_sales)
        detail_layout.addWidget(self.cb_summary)
        detail_layout.addWidget(self.cb_products)
        detail_layout.addWidget(self.cb_simple_register)
        gb_detail.setLayout(detail_layout)
        v.addWidget(gb_detail)

        # Przyciski
        button_layout = QHBoxLayout()
        
        btn_generate = QPushButton("Generuj raport")
        btn_generate.clicked.connect(self.generate_report)
        btn_generate.setStyleSheet("background-color: #2E7D32; font-weight: bold;")
        
        btn_print = QPushButton("🖨️ Drukuj")
        btn_print.clicked.connect(self.print_report)
        btn_print.setToolTip("Drukuj raport bezpośrednio na drukarce")
        
        btn_cancel = QPushButton("Anuluj")
        btn_cancel.clicked.connect(self.reject)
        
        button_layout.addWidget(btn_generate)
        button_layout.addWidget(btn_print)
        button_layout.addWidget(btn_cancel)
        v.addLayout(button_layout)

    def get_date_range(self):
        try:
            if self.report_type == "monthly":
                month = self.month_combo.currentIndex() + 1
                year = self.year_spin.value()
                date_from = f"{year}-{month:02d}-01"
                
                if month == 12:
                    date_to = f"{year}-12-31"
                else:
                    next_month = datetime(year, month + 1, 1)
                    last_day = next_month - timedelta(days=1)
                    date_to = last_day.strftime("%Y-%m-%d")
                    
            elif self.report_type == "yearly":
                year = self.year_only_spin.value()
                date_from = f"{year}-01-01"
                date_to = f"{year}-12-31"
                
            elif self.report_type == "quarterly":
                quarter = self.quarter_combo.currentIndex() + 1
                year = self.quarter_year_spin.value()
                
                # Określ miesiące dla kwartału
                if quarter == 1:
                    date_from = f"{year}-01-01"
                    date_to = f"{year}-03-31"
                elif quarter == 2:
                    date_from = f"{year}-04-01"
                    date_to = f"{year}-06-30"
                elif quarter == 3:
                    date_from = f"{year}-07-01"
                    date_to = f"{year}-09-30"
                else:  # quarter == 4
                    date_from = f"{year}-10-01"
                    date_to = f"{year}-12-31"
                
            else:  # custom
                date_from = self.date_from.date().toString("yyyy-MM-dd")
                date_to = self.date_to.date().toString("yyyy-MM-dd")
                
            return date_from, date_to
            
        except Exception as e:
            today = datetime.now()
            date_from = today.replace(day=1).strftime("%Y-%m-%d")
            if today.month == 12:
                date_to = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                date_to = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            return date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d")
    
    def get_quarter_name(self):
        """Pobiera nazwę kwartału"""
        if self.report_type == "quarterly":
            quarter = self.quarter_combo.currentIndex() + 1
            year = self.quarter_year_spin.value()
            
            quarter_names = {
                1: "I kwartał (styczeń-marzec)",
                2: "II kwartał (kwiecień-czerwiec)",
                3: "III kwartał (lipiec-wrzesień)",
                4: "IV kwartał (październik-grudzień)"
            }
            
            return f"{quarter_names[quarter]} {year}"
        return None

    def print_report(self):
        """Bezpośrednie drukowanie raportu"""
        try:
            from PySide6.QtPrintSupport import QPrinter, QPrintDialog
            
            printer = QPrinter()
            
            if printer.printerName() == "":
                QMessageBox.information(self, "Brak drukarki", 
                    "Nie znaleziono domyślnej drukarki. Skonfiguruj drukarkę w systemie.")
                return
            
            date_from, date_to = self.get_date_range()
            personal_data = self.config.get_business_info()
            
            if self.cb_simple_register.isChecked():
                required_fields = ['name', 'address', 'postal_code', 'city', 'pesel']
                missing_fields = [field for field in required_fields if not personal_data.get(field)]
                
                if missing_fields:
                    QMessageBox.warning(self, "Brak danych", 
                                      f"Uzupełnij dane osobowe w konfiguracji.\nBrakujące pola: {', '.join(missing_fields)}")
                    return
            
            register_data = self.db.get_simple_sales_register_with_cumulative(date_from, date_to, personal_data or {})
            
            if not register_data or not register_data.get("transakcje"):
                QMessageBox.warning(self, "Brak danych", "Brak danych do wydrukowania w wybranym okresie.")
                return
            
            html_content = self.generate_print_html(date_from, date_to, register_data)
            
            print_dialog = QPrintDialog(printer, self)
            print_dialog.setWindowTitle("Drukuj raport")
            
            if print_dialog.exec() == QPrintDialog.Accepted:
                from PySide6.QtGui import QTextDocument
                document = QTextDocument()
                document.setHtml(html_content)
                document.print_(printer)
                
                QMessageBox.information(self, "Drukowanie", "Raport został wysłany do druku.")
                
        except ImportError:
            QMessageBox.warning(self, "Błąd drukowania", 
                              "Moduł drukowania nie jest dostępny.\nUpewnij się, że PySide6 jest poprawnie zainstalowany.")
        except Exception as e:
            QMessageBox.critical(self, "Błąd drukowania", 
                               f"Wystąpił błąd podczas drukowania:\n{str(e)}")

    def generate_print_html(self, date_from, date_to, register_data):
        """Generuje HTML do drukowania z uwzględnieniem limitów kwartalnych"""
        try:
            # Tytuł raportu
            if self.report_type == "monthly":
                month_name = self.month_combo.currentText()
                year = self.year_spin.value()
                title = f"Raport miesięczny - {month_name} {year}"
            elif self.report_type == "yearly":
                year = self.year_only_spin.value()
                title = f"Raport roczny - {year}"
            elif self.report_type == "quarterly":
                quarter_name = self.get_quarter_name()
                title = f"Raport kwartalny - {quarter_name}"
            else:
                title = f"Raport okresowy - {date_from} do {date_to}"
            
            # Dane sprzedawcy
            personal_data = self.config.get_business_info()
            seller_info = ""
            if personal_data.get('name'):
                seller_info = f"""
                <div style="margin-bottom: 20px;">
                    <h3>Dane sprzedawcy:</h3>
                    <p><b>Imię i nazwisko:</b> {personal_data.get('name', '')}</p>
                    <p><b>Adres:</b> {personal_data.get('address', '')}</p>
                    <p><b>Kod pocztowy i miejscowość:</b> {personal_data.get('postal_code', '')} {personal_data.get('city', '')}</p>
                    <p><b>PESEL:</b> {personal_data.get('pesel', '')}</p>
                    {"<p><b>NIP:</b> " + personal_data.get('nip', '') + "</p>" if personal_data.get('nip') else ""}
                    {"<p><b>REGON:</b> " + personal_data.get('regon', '') + "</p>" if personal_data.get('regon') else ""}
                </div>
                """
            
            # Podsumowanie ogólne
            summary = register_data["podsumowanie_ogolne"]
            summary_html = f"""
            <div style="margin-bottom: 20px;">
                <h3>Podsumowanie ogólne:</h3>
                <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
                    <tr>
                        <td><b>Przychód całkowity:</b></td>
                        <td align="right">{summary['przychod_calkowity']:.2f} PLN</td>
                    </tr>
                    <tr>
                        <td><b>Koszt całkowity:</b></td>
                        <td align="right">{summary['koszt_calkowity']:.2f} PLN</td>
                    </tr>
                    <tr>
                        <td><b>Zysk całkowity:</b></td>
                        <td align="right">{summary['zysk_calkowity']:.2f} PLN</td>
                    </tr>
                    <tr>
                        <td><b>Liczba transakcji:</b></td>
                        <td align="right">{summary['liczba_transakcji']}</td>
                    </tr>
                    <tr>
                        <td><b>Liczba pozycji:</b></td>
                        <td align="right">{summary['liczba_pozycji']}</td>
                    </tr>
                </table>
            </div>
            """
            
            # Analiza limitów US
            year = int(date_from[:4])
            minimal_wage = self.config.get_minimal_wage(year)
            
            # Określ czy to raport kwartalny
            is_quarterly_report = self.report_type == "quarterly"
            
            if is_quarterly_report and self.config.use_quarterly_limits():
                # Używamy limitów kwartalnych
                limit_type = "kwartalny"
                limit_multiplier = self.config.get_limits_config().get("quarterly_limit_multiplier", 2.25)
                limit = minimal_wage * limit_multiplier
                limit_text = f"{limit_multiplier*100:.0f}% minimalnego wynagrodzenia"
            else:
                # Używamy limitów miesięcznych
                limit_type = "miesięczny"
                limit = minimal_wage * 0.75
                limit_text = "75% minimalnego wynagrodzenia"
            
            total_revenue = summary['przychod_calkowity']
            
            analysis_html = f"""
            <div style="margin-bottom: 20px;">
                <h3>Analiza progu dla US ({year} r.):</h3>
                <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
                    <tr>
                        <td><b>Minimalne wynagrodzenie:</b></td>
                        <td align="right">{minimal_wage:.2f} PLN</td>
                    </tr>
                    <tr>
                        <td><b>{limit_text} (limit {limit_type}):</b></td>
                        <td align="right">{limit:.2f} PLN</td>
                    </tr>
                    <tr>
                        <td><b>Przychód narastająco:</b></td>
                        <td align="right">{total_revenue:.2f} PLN</td>
                    </tr>
                    <tr>
                        <td><b>Stan:</b></td>
                        <td align="right" style="color: {'red' if total_revenue > limit else 'green'}; font-weight: bold;">
                            {'PRZEKROCZONO LIMIT!' if total_revenue > limit else 'W LIMICIE'}
                        </td>
                    </tr>
                </table>
            </div>
            """
            
            # Dodatkowa informacja dla raportów kwartalnych
            if is_quarterly_report and self.config.use_quarterly_limits():
                analysis_html += f"""
                <div style="margin-bottom: 20px; padding: 10px; background-color: #f0f0f0; border-left: 4px solid #2E7D32;">
                    <p><b>UWAGA:</b> Od 2026 roku obowiązują limity kwartalne dla działalności nierejestrowanej.</p>
                    <p>Limit kwartalny wynosi {limit_multiplier*100:.0f}% minimalnego wynagrodzenia.</p>
                    <p>Przychód w tym kwartale: <b>{total_revenue:.2f} PLN</b></p>
                </div>
                """
            
            # Podsumowanie miesięczne (jeśli dostępne)
            monthly_html = ""
            if register_data.get("podsumowanie_miesieczne_narastajaco"):
                monthly_rows = ""
                for month_data in register_data["podsumowanie_miesieczne_narastajaco"]:
                    monthly_rows += f"""
                    <tr>
                        <td>{month_data['miesiac']}</td>
                        <td align="right">{month_data['przychod_miesiac']:.2f} PLN</td>
                        <td align="right">{month_data['zysk_miesiac']:.2f} PLN</td>
                        <td align="right">{month_data['liczba_transakcji']}</td>
                        <td align="right">{month_data.get('liczba_pozycji', 0)}</td>
                        <td align="right">{month_data['przychod_narastajaco']:.2f} PLN</td>
                    </tr>
                    """
                
                monthly_html = f"""
                <div style="margin-bottom: 20px;">
                    <h3>Podsumowanie miesięczne:</h3>
                    <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%; font-size: 10px;">
                        <thead>
                            <tr>
                                <th>Miesiąc</th>
                                <th>Przychód</th>
                                <th>Zysk</th>
                                <th>Transakcje</th>
                                <th>Pozycje</th>
                                <th>Przychód narastająco</th>
                            </tr>
                        </thead>
                        <tbody>
                            {monthly_rows}
                        </tbody>
                    </table>
                </div>
                """
            
            # Stopka
            footer = f"""
            <div style="margin-top: 40px; border-top: 1px solid #ccc; padding-top: 10px; font-size: 9px; color: #666;">
                <p>Raport wygenerowany: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Typ raportu: {self.report_type}</p>
                <p>System Magazynowo-Sprzedażowy v{APP_VERSION}</p>
            </div>
            """
            
            # Cały dokument HTML
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>{title}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #2E7D32; border-bottom: 2px solid #2E7D32; padding-bottom: 10px; }}
                    h3 {{ color: #333; margin-top: 25px; }}
                    table {{ margin-top: 10px; }}
                    th {{ background-color: #f2f2f2; padding: 8px; }}
                    td {{ padding: 6px; }}
                    .footer {{ margin-top: 40px; border-top: 1px solid #ccc; padding-top: 10px; font-size: 9px; color: #666; }}
                    .info-box {{ background-color: #f0f0f0; padding: 10px; border-left: 4px solid #2E7D32; margin: 10px 0; }}
                </style>
            </head>
            <body>
                <h1>{title}</h1>
                <p><b>Okres:</b> {date_from} - {date_to}</p>
                <p><b>Wygenerowano:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                {seller_info}
                {summary_html}
                {analysis_html}
                {monthly_html}
                {footer}
            </body>
            </html>
            """
            
            return html
            
        except Exception as e:
            print(f"Błąd generowania HTML: {e}")
            return f"<html><body><h1>Błąd generowania raportu</h1><p>{str(e)}</p></body></html>"

    def generate_report(self):
        try:
            date_from, date_to = self.get_date_range()
            
            if not self.cb_purchases.isChecked() and not self.cb_sales.isChecked():
                QMessageBox.warning(self, "Brak danych", "Wybierz przynajmniej jeden typ danych (zakupy lub sprzedaż).")
                return
            
            personal_data = self.config.get_business_info()
            
            if self.cb_simple_register.isChecked():
                required_fields = ['name', 'address', 'postal_code', 'city', 'pesel']
                missing_fields = [field for field in required_fields if not personal_data.get(field)]
                
                if missing_fields:
                    QMessageBox.warning(self, "Brak danych", 
                                      f"Uzupełnij dane osobowe w konfiguracji.\nBrakujące pola: {', '.join(missing_fields)}")
                    return
            
            # Ustal format pliku
            if self.rb_csv.isChecked():
                file_filter = "CSV Files (*.csv)"
                default_ext = ".csv"
            elif self.rb_excel.isChecked():
                file_filter = "Excel Files (*.xlsx)"
                default_ext = ".xlsx"
            else:  # PDF
                file_filter = "PDF Files (*.pdf)"
                default_ext = ".pdf"
            
            # Sugerowana nazwa pliku
            if self.report_type == "monthly":
                month_name = self.month_combo.currentText().lower()
                year = self.year_spin.value()
                suggested_name = f"raport_{month_name}_{year}{default_ext}"
            elif self.report_type == "yearly":
                year = self.year_only_spin.value()
                suggested_name = f"raport_{year}{default_ext}"
            elif self.report_type == "quarterly":
                quarter = self.quarter_combo.currentIndex() + 1
                year = self.quarter_year_spin.value()
                suggested_name = f"raport_kwartal{quarter}_{year}{default_ext}"
            else:
                from_str = date_from.replace("-", "")
                to_str = date_to.replace("-", "")
                suggested_name = f"raport_{from_str}_do_{to_str}{default_ext}"
            
            path, _ = QFileDialog.getSaveFileName(
                self, "Zapisz raport", 
                os.path.join(os.getcwd(), suggested_name),
                file_filter
            )
            
            if path:
                try:
                    if self.rb_csv.isChecked():
                        success = self.db.export_detailed_report_csv(
                            path, date_from, date_to,
                            include_purchases=self.cb_purchases.isChecked(),
                            include_sales=self.cb_sales.isChecked(),
                            include_summary=self.cb_summary.isChecked(),
                            include_products=self.cb_products.isChecked(),
                            personal_data=personal_data if self.cb_simple_register.isChecked() else None,
                            report_type=self.report_type,
                            config=self.config
                        )
                    elif self.rb_excel.isChecked():
                        success = self.db.export_detailed_report_excel(
                            path, date_from, date_to,
                            include_purchases=self.cb_purchases.isChecked(),
                            include_sales=self.cb_sales.isChecked(),
                            include_summary=self.cb_summary.isChecked(),
                            include_products=self.cb_products.isChecked(),
                            personal_data=personal_data if self.cb_simple_register.isChecked() else None,
                            report_type=self.report_type,
                            config=self.config
                        )
                    else:  # PDF
                        success = self.export_detailed_report_pdf(
                            path, date_from, date_to,
                            include_purchases=self.cb_purchases.isChecked(),
                            include_sales=self.cb_sales.isChecked(),
                            include_summary=self.cb_summary.isChecked(),
                            include_products=self.cb_products.isChecked(),
                            personal_data=personal_data if self.cb_simple_register.isChecked() else None
                        )
                    
                    if success:
                        QMessageBox.information(self, "Sukces", f"Raport został wygenerowany:\n{path}")
                        self.accept()
                    else:
                        QMessageBox.warning(self, "Błąd", "Nie udało się wygenerować raportu.")
                        
                except Exception as e:
                    error_msg = str(e)
                    if "openpyxl" in error_msg.lower():
                        error_msg += "\n\nUpewnij się, że openpyxl jest zainstalowany:\npip install openpyxl"
                    QMessageBox.critical(self, "Błąd", f"Wystąpił błąd podczas generowania raportu:\n{error_msg}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Wystąpił błąd:\n{str(e)}")
            import traceback
            print(traceback.format_exc())

    def export_detailed_report_pdf(self, path, date_from, date_to,
                                 include_purchases=True, include_sales=True,
                                 include_summary=True, include_products=False,
                                 personal_data=None):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import os
            
            # Próbuj użyć czcionki z polskimi znakami
            font_paths = [
                '/usr/share/fonts/truetype/msttcorefonts/Arial.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                'C:/Windows/Fonts/arial.ttf',
                'arial.ttf'
            ]
            
            font_name = 'Helvetica'
            for font_path in font_paths:
                try:
                    if os.path.exists(font_path):
                        pdfmetrics.registerFont(TTFont('PolishFont', font_path))
                        font_name = 'PolishFont'
                        break
                except:
                    continue
            
            doc = SimpleDocTemplate(
                path,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            story = []
            styles = getSampleStyleSheet()
            
            # Styl tytułu
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName=font_name,
                fontSize=16,
                spaceAfter=30,
                alignment=1
            )
            
            # Styl normalny
            normal_style = ParagraphStyle(
                'Normal',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=10,
                spaceAfter=6
            )
            
            # Styl nagłówka
            header_style = ParagraphStyle(
                'Header',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=11,
                textColor=colors.whitesmoke,
                alignment=1
            )
            
            # Styl podtytułu
            subtitle_style = ParagraphStyle(
                'Subtitle',
                parent=styles['Heading2'],
                fontName=font_name,
                fontSize=12,
                spaceAfter=20,
                alignment=0
            )
            
            # Tytuł raportu
            if self.report_type == "quarterly":
                quarter_name = self.get_quarter_name()
                story.append(Paragraph(f"RAPORT KWARTALNY - {quarter_name}", title_style))
            elif self.report_type == "monthly":
                month_name = self.month_combo.currentText()
                year = self.year_spin.value()
                story.append(Paragraph(f"RAPORT MIESIĘCZNY - {month_name} {year}", title_style))
            elif self.report_type == "yearly":
                year = self.year_only_spin.value()
                story.append(Paragraph(f"RAPORT ROCZNY - {year}", title_style))
            else:
                story.append(Paragraph("RAPORT SZCZEGÓŁOWY", title_style))
                
            story.append(Spacer(1, 10))
            
            # Okres raportu
            period_text = f"Okres: {date_from} - {date_to}"
            story.append(Paragraph(period_text, subtitle_style))
            
            # Data generowania
            gen_date = f"Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            story.append(Paragraph(gen_date, normal_style))
            story.append(Spacer(1, 30))
            
            # Dane sprzedawcy (jeśli dostępne)
            if personal_data and personal_data.get('name'):
                story.append(Paragraph("DANE SPRZEDAWCY", subtitle_style))
                
                seller_info = [
                    f"Imię i nazwisko: {personal_data.get('name', '')}",
                    f"Adres: {personal_data.get('address', '')}",
                    f"{personal_data.get('postal_code', '')} {personal_data.get('city', '')}",
                    f"PESEL: {personal_data.get('pesel', '')}"
                ]
                
                if personal_data.get('nip'):
                    seller_info.append(f"NIP: {personal_data.get('nip', '')}")
                if personal_data.get('regon'):
                    seller_info.append(f"REGON: {personal_data.get('regon', '')}")
                
                for info in seller_info:
                    story.append(Paragraph(info, normal_style))
                
                story.append(Spacer(1, 20))
            
            # Pobierz dane z bazy
            register_data = self.db.get_simple_sales_register_with_cumulative(date_from, date_to, personal_data or {})
            
            if register_data and register_data.get("transakcje"):
                # Podsumowanie ogólne
                story.append(Paragraph("PODSUMOWANIE OGÓLNE", subtitle_style))
                
                summary = register_data["podsumowanie_ogolne"]
                summary_data = [
                    ["Przychód całkowity:", f"{summary['przychod_calkowity']:.2f} PLN"],
                    ["Koszt całkowity:", f"{summary['koszt_calkowity']:.2f} PLN"],
                    ["Zysk całkowity:", f"{summary['zysk_calkowity']:.2f} PLN"],
                    ["Liczba transakcji:", str(summary['liczba_transakcji'])],
                    ["Liczba pozycji:", str(summary['liczba_pozycji'])]
                ]
                
                summary_table = Table(summary_data, colWidths=[8*cm, 5*cm])
                summary_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                    ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ]))
                
                story.append(summary_table)
                story.append(Spacer(1, 30))
                
                # Analiza progu US z uwzględnieniem konfiguracji
                story.append(Paragraph("ANALIZA PROGU DLA US", subtitle_style))
                
                year = int(date_from[:4])
                minimal_wage = self.config.get_minimal_wage(year)
                
                # Określ czy to raport kwartalny
                is_quarterly_report = self.report_type == "quarterly"
                
                if is_quarterly_report and self.config.use_quarterly_limits():
                    # Używamy limitów kwartalnych
                    limit_type = "kwartalny"
                    limit_multiplier = self.config.get_limits_config().get("quarterly_limit_multiplier", 2.25)
                    limit = minimal_wage * limit_multiplier
                    limit_text = f"{limit_multiplier*100:.0f}% minimalnego wynagrodzenia"
                else:
                    # Używamy limitów miesięcznych
                    limit_type = "miesięczny"
                    limit = minimal_wage * 0.75
                    limit_text = "75% minimalnego wynagrodzenia"
                
                total_revenue = summary['przychod_calkowity']
                
                analysis_data = [
                    ["Minimalne wynagrodzenie:", f"{minimal_wage:.2f} PLN"],
                    [f"{limit_text} (limit {limit_type}):", f"{limit:.2f} PLN"],
                    ["Przychód narastająco:", f"{total_revenue:.2f} PLN"],
                    ["Stan:", "PRZEKROCZONO LIMIT!" if total_revenue > limit else "W LIMICIE"]
                ]
                
                analysis_table = Table(analysis_data, colWidths=[8*cm, 5*cm])
                analysis_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                    ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                    ('TEXTCOLOR', (1, 3), (1, 3), colors.red if total_revenue > limit else colors.green),
                ]))
                
                story.append(analysis_table)
                story.append(Spacer(1, 30))
                
                # Dodatkowa informacja dla raportów kwartalnych
                if is_quarterly_report and self.config.use_quarterly_limits():
                    info_text = Paragraph(
                        f"<b>UWAGA:</b> Od 2026 roku obowiązują limity kwartalne dla działalności nierejestrowanej.<br/>"
                        f"Limit kwartalny wynosi {limit_multiplier*100:.0f}% minimalnego wynagrodzenia.<br/>"
                        f"Przychód w tym kwartale: <b>{total_revenue:.2f} PLN</b>",
                        ParagraphStyle('Info', parent=styles['Normal'], fontName=font_name, fontSize=9,
                                     backColor=colors.lightgrey, borderPadding=10,
                                     leftIndent=20, rightIndent=20)
                    )
                    story.append(info_text)
                    story.append(Spacer(1, 20))
                
                # Podsumowanie miesięczne (jeśli dostępne)
                if register_data.get("podsumowanie_miesieczne_narastajaco"):
                    story.append(Paragraph("PODSUMOWANIE MIESIĘCZNE", subtitle_style))
                    
                    headers = ["Miesiąc", "Przychód", "Zysk", "Transakcje", "Pozycje", "Przychód narastająco"]
                    monthly_data = [headers]
                    
                    for month_data in register_data["podsumowanie_miesieczne_narastajaco"]:
                        monthly_data.append([
                            month_data['miesiac'],
                            f"{month_data['przychod_miesiac']:.2f} PLN",
                            f"{month_data['zysk_miesiac']:.2f} PLN",
                            str(month_data['liczba_transakcji']),
                            str(month_data.get('liczba_pozycji', 0)),
                            f"{month_data['przychod_narastajaco']:.2f} PLN"
                        ])
                    
                    monthly_table = Table(monthly_data, colWidths=[3*cm, 3*cm, 3*cm, 2*cm, 2*cm, 3*cm])
                    monthly_table.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (-1, -1), font_name),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                        ('ALIGN', (3, 0), (4, -1), 'CENTER'),
                    ]))
                    
                    story.append(monthly_table)
                    story.append(Spacer(1, 30))
                
                # Jeśli włączone szczegółowe transakcje
                if self.cb_sales.isChecked() and len(register_data["transakcje"]) > 0:
                    story.append(PageBreak())
                    story.append(Paragraph("SZCZEGÓŁOWA EWIDENCJA TRANSAKCJI", subtitle_style))
                    
                    # Ogranicz liczbę transakcji do pierwszej strony
                    max_transactions = 50
                    transactions = register_data["transakcje"][:max_transactions]
                    
                    trans_headers = ["Data", "Platforma", "Produkt", "Ilość", "Cena", "Wartość", "Zysk"]
                    trans_data = [trans_headers]
                    
                    for transaction in transactions:
                        trans_data.append([
                            transaction['data_sprzedazy'],
                            transaction['platforma'],
                            f"{transaction['kod_produktu']}...",
                            str(transaction['ilosc']),
                            f"{transaction['cena_jednostkowa_pln']:.2f}",
                            f"{transaction['wartosc_sprzedazy_pln']:.2f}",
                            f"{transaction['zysk_brutto']:.2f}"
                        ])
                    
                    trans_table = Table(trans_data, colWidths=[2.5*cm, 2*cm, 4*cm, 1.5*cm, 2*cm, 2*cm, 2*cm])
                    trans_table.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (-1, -1), font_name),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
                        ('ALIGN', (4, 0), (-1, -1), 'RIGHT'),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
                    ]))
                    
                    story.append(trans_table)
                    
                    if len(register_data["transakcje"]) > max_transactions:
                        story.append(Spacer(1, 10))
                        remaining = len(register_data["transakcje"]) - max_transactions
                        story.append(Paragraph(f"... i {remaining} kolejnych transakcji", normal_style))
            else:
                story.append(Paragraph("Brak danych sprzedaży w wybranym okresie", subtitle_style))
            
            # Stopka
            story.append(Spacer(1, 30))
            footer = Paragraph(f"Raport wygenerowany przez System Magazynowo-Sprzedażowy v{APP_VERSION}", 
                             ParagraphStyle('Footer', parent=styles['Normal'], fontName=font_name, fontSize=8, alignment=1))
            story.append(footer)
            
            doc.build(story)
            return True
            
        except Exception as e:
            print(f"Błąd w export_detailed_report_pdf: {e}")
            import traceback
            traceback.print_exc()
            return False

# ================== SORTOWANIE ==================
class SortableTableWidget(QTableWidget):
    def __init__(self, rows=0, columns=0, parent=None):
        super().__init__(rows, columns, parent)
        self.sort_order = {}
        self.current_sorted_column = -1
        self.current_sort_order = Qt.AscendingOrder
        
        self.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        
    def on_header_clicked(self, column):
        if column in self.sort_order:
            self.sort_order[column] = not self.sort_order[column]
        else:
            self.sort_order[column] = True
        
        sort_ascending = self.sort_order[column]
        
        self.current_sorted_column = column
        self.current_sort_order = Qt.AscendingOrder if sort_ascending else Qt.DescendingOrder
        
        self.sort_by_column(column, self.current_sort_order)
        self.mark_sorted_column(column)
    
    def sort_by_column(self, column, order):
        self.sortItems(column, order)
    
    def mark_sorted_column(self, column):
        header = self.horizontalHeader()
        for i in range(header.count()):
            if i == column:
                sort_text = " ↑" if self.sort_order.get(column, True) else " ↓"
                original_text = self.get_column_name(i)
                header.model().setHeaderData(i, Qt.Horizontal, original_text + sort_text)
                
                header.setStyleSheet("""
                    QHeaderView::section {
                        background-color: #e0e0e0;
                        font-weight: bold;
                    }
                """)
            else:
                original_text = self.get_column_name(i)
                header.model().setHeaderData(i, Qt.Horizontal, original_text)
        
        if column == -1:
            header.setStyleSheet("""
                QHeaderView::section {
                    background-color: #f2f2f2;
                    font-weight: normal;
                }
            """)
    
    def get_column_name(self, column):
        header = self.horizontalHeader()
        original_text = header.model().headerData(column, Qt.Horizontal)
        
        if original_text:
            for arrow in [" ↑", " ↓"]:
                if original_text.endswith(arrow):
                    return original_text[:-2]
            return original_text
        
        names = ["ID", "SKU", "Nazwa", "Stan", ""]
        if column < len(names):
            return names[column]
        return f"Kolumna {column+1}"
    
    def load_data(self, data):
        self.setRowCount(len(data))
        for i, row in enumerate(data):
            for j, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                
                if j in [0, 3]:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    try:
                        item.setData(Qt.EditRole, float(value))
                    except ValueError:
                        pass
                
                self.setItem(i, j, item)
        
        self.sort_order = {}
        self.current_sorted_column = -1
        self.mark_sorted_column(-1)

# ================== HISTORIA Z ZAZNACZANIEM ==================
class HistoryDialog(QDialog):
    def __init__(self, title, headers, rows, delete_cb, parent=None, allow_multiple=True):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(1000, 550)
        self.rows = rows
        self.delete_cb = delete_cb
        self.headers = headers
        self.allow_multiple = allow_multiple

        v = QVBoxLayout(self)

        button_panel = QHBoxLayout()
        
        self.select_all_checkbox = QCheckBox("Zaznacz wszystkie")
        self.select_all_checkbox.stateChanged.connect(self.toggle_select_all)
        button_panel.addWidget(self.select_all_checkbox)
        
        button_panel.addStretch()
        
        b_select_none = QPushButton("Odznacz wszystkie")
        b_select_none.clicked.connect(self.select_none)
        button_panel.addWidget(b_select_none)
        
        v.addLayout(button_panel)

        self.table = SortableTableWidget()
        self.table.setColumnCount(len(headers) + 1)
        table_headers = ["✓"] + list(headers)
        self.table.setHorizontalHeaderLabels(table_headers)
        
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for i in range(1, len(table_headers)):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
        
        v.addWidget(self.table)

        delete_panel = QHBoxLayout()
        
        b_del_selected = QPushButton("🗑️ Usuń zaznaczone")
        b_del_selected.setStyleSheet("background-color: #d32f2f; font-weight: bold;")
        b_del_selected.clicked.connect(self.delete_selected)
        delete_panel.addWidget(b_del_selected)
        
        b_del_single = QPushButton("Usuń pojedynczy")
        b_del_single.clicked.connect(self.delete_single)
        delete_panel.addWidget(b_del_single)
        
        delete_panel.addStretch()
        
        b_close = QPushButton("Zamknij")
        b_close.clicked.connect(self.accept)
        delete_panel.addWidget(b_close)
        
        v.addLayout(delete_panel)

        self.load()

    def load(self):
        self.table.setRowCount(len(self.rows))
        for i, r in enumerate(self.rows):
            checkbox = QCheckBox()
            checkbox.setChecked(False)
            self.table.setCellWidget(i, 0, checkbox)
            
            for j, val in enumerate(r):
                item = QTableWidgetItem(str(val))
                
                if j in [0, 3, 4]:
                    if isinstance(val, (int, float)):
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        try:
                            item.setData(Qt.EditRole, float(val))
                        except (ValueError, TypeError):
                            pass
                
                self.table.setItem(i, j + 1, item)

    def toggle_select_all(self, state):
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(state == Qt.Checked)

    def select_none(self):
        self.select_all_checkbox.setChecked(False)
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)

    def get_selected_ids(self):
        selected_ids = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                id_item = self.table.item(row, 1)
                if id_item:
                    try:
                        selected_ids.append(int(id_item.text()))
                    except ValueError:
                        pass
        return selected_ids

    def delete_selected(self):
        selected_ids = self.get_selected_ids()
        if not selected_ids:
            QMessageBox.warning(self, "Brak zaznaczenia", "Nie zaznaczono żadnych wpisów do usunięcia.")
            return
        
        count = len(selected_ids)
        if QMessageBox.question(
            self, "Potwierdź usunięcie",
            f"Czy na pewno usunąć {count} zaznaczonych wpisów?\n"
            f"Spowoduje to także usunięcie odpowiednich ilości z magazynu.",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            for order_id in selected_ids:
                self.delete_cb(order_id)
            self.accept()

    def delete_single(self):
        selected_ids = self.get_selected_ids()
        if len(selected_ids) == 0:
            QMessageBox.warning(self, "Brak zaznaczenia", "Nie zaznaczono żadnego wpisu do usunięcia.")
            return
        elif len(selected_ids) > 1:
            QMessageBox.warning(self, "Za dużo zaznaczonych", "Zaznaczono więcej niż jeden wpis. Użyj 'Usuń zaznaczone' dla wielu pozycji.")
            return
        
        order_id = selected_ids[0]
        if QMessageBox.question(self, "Potwierdź", "Usunąć wybrany wpis?") == QMessageBox.Yes:
            self.delete_cb(order_id)
            self.accept()

# ================== INWENTARYZACJA ==================
class InventoryDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Inwentaryzacja magazynu")
        self.resize(800, 450)

        v = QVBoxLayout(self)

        self.table = SortableTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["ID", "SKU", "Nazwa", "Stan systemowy", "Stan rzeczywisty"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v.addWidget(self.table)

        b = QPushButton("Zapisz korekty")
        b.clicked.connect(self.apply)
        v.addWidget(b)

        self.load()

    def load(self):
        rows = self.db.list_products()
        data = []
        for r in rows:
            data.append([
                r["id"],
                r["sku"],
                r["title"],
                r["stock"],
                r["stock"]
            ])
        self.table.load_data(data)

    def apply(self):
        for r in range(self.table.rowCount()):
            pid = int(self.table.item(r, 0).text())
            system = int(self.table.item(r, 3).text())
            real = int(self.table.item(r, 4).text())
            delta = real - system
            if delta != 0:
                self.db.update_stock(pid, delta)
        QMessageBox.information(self, "OK", "Inwentaryzacja zapisana")
        self.accept()

# ================== ZAKUP ==================
class PurchaseDialog(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setWindowTitle("Dodaj zakup")
        v = QVBoxLayout(self)

        self.cost = QDoubleSpinBox()
        self.cost.setMaximum(1e9)
        self.date = QDateEdit(QDate.currentDate())
        self.date.setCalendarPopup(True)

        form = QFormLayout()
        form.addRow("Koszt PLN", self.cost)
        form.addRow("Data", self.date)
        v.addLayout(form)

        self.items = SortableTableWidget(0, 2)
        self.items.setHorizontalHeaderLabels(["Produkt", "Ilość"])
        v.addWidget(self.items)

        b_add = QPushButton("Dodaj pozycję")
        b_add.clicked.connect(self.add_item)
        v.addWidget(b_add)

        b_ok = QPushButton("Zapisz")
        b_ok.clicked.connect(self.accept)
        v.addWidget(b_ok)

    def add_item(self):
        r = self.items.rowCount()
        self.items.insertRow(r)
        
        combo = product_combo(self.db)
        self.items.setCellWidget(r, 0, combo)

        qty = QSpinBox()
        qty.setMinimum(1)
        qty.setMaximum(100000)
        self.items.setCellWidget(r, 1, qty)

    def get_items(self):
        return [
            (
                self.items.cellWidget(r, 0).currentData(),
                self.items.cellWidget(r, 1).value()
            )
            for r in range(self.items.rowCount())
        ]

# ================== DIALOG HISTORII RACHUNKÓW ==================
class InvoicesHistoryDialog(QDialog):
    def __init__(self, db, config, parent=None):
        super().__init__(parent)
        self.db = db
        self.config = config
        self.setWindowTitle("Historia wygenerowanych rachunków")
        self.resize(1200, 600)
        
        v = QVBoxLayout(self)
        
        # Filtr daty
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Od:"))
        self.date_from = QDateEdit(QDate.currentDate().addMonths(-1))
        self.date_from.setCalendarPopup(True)
        filter_layout.addWidget(self.date_from)
        
        filter_layout.addWidget(QLabel("Do:"))
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        filter_layout.addWidget(self.date_to)
        
        btn_filter = QPushButton("Filtruj")
        btn_filter.clicked.connect(self.load_invoices)
        filter_layout.addWidget(btn_filter)
        
        btn_refresh = QPushButton("Odśwież")
        btn_refresh.clicked.connect(self.load_invoices)
        filter_layout.addWidget(btn_refresh)
        
        # Przycisk resetu numeracji
        btn_reset_counter = QPushButton("⟳ Resetuj licznik")
        btn_reset_counter.setToolTip("Resetuj licznik numeracji rachunków")
        btn_reset_counter.clicked.connect(self.reset_invoice_counter)
        filter_layout.addWidget(btn_reset_counter)
        
        filter_layout.addStretch()
        v.addLayout(filter_layout)
        
        # Tabela z rachunkami
        self.table = SortableTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "✓", "Numer rachunku", "Data wystawienia", "Klient", "Kwota", 
            "Platforma", "Data sprzedaży", "Ścieżka pliku", "Akcje"
        ])
        
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        
        v.addWidget(self.table)
        
        # Przyciski akcji
        button_layout = QHBoxLayout()
        
        self.select_all_checkbox = QCheckBox("Zaznacz wszystkie")
        self.select_all_checkbox.stateChanged.connect(self.toggle_select_all)
        button_layout.addWidget(self.select_all_checkbox)
        
        btn_open_selected = QPushButton("🗁 Otwórz zaznaczone")
        btn_open_selected.clicked.connect(self.open_selected_invoices)
        button_layout.addWidget(btn_open_selected)
        
        btn_delete_selected = QPushButton("🗑 Usuń zaznaczone")
        btn_delete_selected.setStyleSheet("background-color: #d32f2f; font-weight: bold;")
        btn_delete_selected.clicked.connect(self.delete_selected_invoices)
        button_layout.addWidget(btn_delete_selected)
        
        button_layout.addStretch()
        
        btn_close = QPushButton("Zamknij")
        btn_close.clicked.connect(self.accept)
        button_layout.addWidget(btn_close)
        
        v.addLayout(button_layout)
        
        self.load_invoices()
    
    def load_invoices(self):
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")
        
        invoices = self.db.list_invoices(date_from, date_to)
        self.table.setRowCount(len(invoices))
        
        for i, inv in enumerate(invoices):
            # Checkbox
            checkbox = QCheckBox()
            self.table.setCellWidget(i, 0, checkbox)
            
            # Numer rachunku
            self.table.setItem(i, 1, QTableWidgetItem(inv['invoice_number']))
            
            # Data wystawienia
            self.table.setItem(i, 2, QTableWidgetItem(inv['issue_date']))
            
            # Klient
            customer = inv['customer_name']
            if not customer and inv['sale_order_id']:
                customer = f"Zamówienie #{inv['sale_order_id']}"
            self.table.setItem(i, 3, QTableWidgetItem(customer or "Brak danych"))
            
            # Kwota
            amount_item = QTableWidgetItem(f"{inv['total_amount']:.2f} PLN")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 4, amount_item)
            
            # Platforma
            self.table.setItem(i, 5, QTableWidgetItem(inv['platform'] or "Brak"))
            
            # Data sprzedaży
            self.table.setItem(i, 6, QTableWidgetItem(inv['sale_date'] or inv['issue_date']))
            
            # Ścieżka pliku
            path_item = QTableWidgetItem(inv['file_path'])
            path_item.setToolTip(inv['file_path'])
            self.table.setItem(i, 7, path_item)
            
            # Przyciski akcji
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 4, 4, 4)
            action_layout.setSpacing(4)
            
            btn_open = QPushButton("📄 Otwórz")
            btn_open.setFixedWidth(80)
            btn_open.setToolTip("Otwórz plik PDF")
            btn_open.clicked.connect(lambda checked, path=inv['file_path']: self.open_invoice(path))
            action_layout.addWidget(btn_open)
            
            btn_delete = QPushButton("🗑 Usuń")
            btn_delete.setFixedWidth(80)
            btn_delete.setStyleSheet("background-color: #ff4444; color: white;")
            btn_delete.setToolTip("Usuń rachunek i plik PDF")
            btn_delete.clicked.connect(lambda checked, inv_id=inv['id'], inv_num=inv['invoice_number']: 
                                      self.delete_single_invoice(inv_id, inv_num))
            action_layout.addWidget(btn_delete)
            
            action_layout.addStretch()
            self.table.setCellWidget(i, 8, action_widget)
    
    def toggle_select_all(self, state):
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(state == Qt.Checked)
    
    def get_selected_invoice_ids(self):
        selected_ids = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                invoice_number_item = self.table.item(row, 1)
                if invoice_number_item:
                    invoice_number = invoice_number_item.text()
                    invoice = self.db.get_invoice_by_number(invoice_number)
                    if invoice:
                        selected_ids.append(invoice['id'])
        return selected_ids
    
    def open_selected_invoices(self):
        selected_ids = self.get_selected_invoice_ids()
        if not selected_ids:
            QMessageBox.warning(self, "Brak zaznaczenia", "Nie zaznaczono żadnych rachunków.")
            return
        
        for inv_id in selected_ids:
            invoices = self.db.list_invoices()
            for inv in invoices:
                if inv['id'] == inv_id and os.path.exists(inv['file_path']):
                    self.open_invoice(inv['file_path'])
    
    def open_invoice(self, file_path):
        if os.path.exists(file_path):
            try:
                if os.name == 'nt':
                    os.startfile(file_path)
                elif os.name == 'posix':
                    import subprocess
                    subprocess.call(['open', file_path] if sys.platform == 'darwin' 
                                   else ['xdg-open', file_path])
            except Exception as e:
                QMessageBox.warning(self, "Błąd", f"Nie można otworzyć pliku:\n{file_path}\n\nBłąd: {str(e)}")
        else:
            QMessageBox.warning(self, "Brak pliku", f"Plik nie istnieje:\n{file_path}")
    
    def delete_selected_invoices(self):
        selected_ids = self.get_selected_invoice_ids()
        if not selected_ids:
            QMessageBox.warning(self, "Brak zaznaczenia", "Nie zaznaczono żadnych rachunków do usunięcia.")
            return
        
        count = len(selected_ids)
        reply = QMessageBox.question(
            self, "Potwierdź usunięcie",
            f"Czy na pewno usunąć {count} zaznaczonych rachunków?\n"
            f"UWAGA: Spowoduje to również usunięcie plików PDF z dysku!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success_count = 0
            for inv_id in selected_ids:
                if self.db.delete_invoice(inv_id):
                    success_count += 1
            
            QMessageBox.information(self, "Usunięto", 
                                  f"Usunięto {success_count} z {count} rachunków.")
            self.load_invoices()
    
    def delete_single_invoice(self, invoice_id, invoice_number):
        reply = QMessageBox.question(
            self, "Potwierdź usunięcie",
            f"Czy na pewno usunąć rachunek:\n{invoice_number}?\n\n"
            f"UWAGA: Spowoduje to również usunięcie pliku PDF z dysku!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db.delete_invoice(invoice_id):
                QMessageBox.information(self, "Usunięto", f"Rachunek {invoice_number} został usunięty.")
                self.load_invoices()
    
    def reset_invoice_counter(self):
        """Resetuje licznik numeracji rachunków"""
        reply = QMessageBox.question(
            self, "Resetuj licznik",
            "Czy na pewno chcesz zresetować licznik numeracji rachunków?\n\n"
            "UWAGA: To ustawi następny numer rachunku na 1.\n"
            "Może spowodować duplikaty numerów jeśli stare rachunki nadal istnieją!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Pobierz aktualną konfigurację
            current_config = self.config.load()
            
            # Resetuj licznik
            current_config["invoice"]["next_number"] = 1
            
            # Zapisz z powrotem
            with open("config.json", 'w', encoding='utf-8') as f:
                import json
                json.dump(current_config, f, ensure_ascii=False, indent=2)
            
            # Przeładuj konfigurację
            self.config = Config()
            
            QMessageBox.information(self, "Licznik zresetowany", 
                                  "Licznik numeracji rachunków został zresetowany do 1.")

# ================== SPRZEDAŻ Z RACHUNKIEM ==================
class SaleDialog(QDialog):
    def __init__(self, db, config):
        super().__init__()
        self.db = db
        self.config = config
        self.setWindowTitle("Dodaj sprzedaż")
        v = QVBoxLayout(self)
        
        self.platform = QComboBox()
        self.platform.addItems(PLATFORMS)
        self.pln = QDoubleSpinBox()
        self.pln.setMaximum(1e9)
        self.pln.valueChanged.connect(self.update_fifo_cost)
        
        self.date = QDateEdit(QDate.currentDate())
        self.date.setCalendarPopup(True)

        # Koszt automatyczny z FIFO
        self.auto_cost_label = QLabel("Koszt zakupu (FIFO): 0.00 PLN")
        self.auto_cost_label.setStyleSheet("font-weight: bold; color: #c62828;")
        
        # Checkbox dla rachunku uproszczonego
        self.create_invoice_checkbox = QCheckBox("Wygeneruj rachunek uproszczony")
        self.create_invoice_checkbox.setChecked(False)
        self.create_invoice_checkbox.toggled.connect(self.toggle_invoice_fields)
        
        # Dane klienta (opcjonalne) - UKRYTE DOMYŚLNIE
        self.client_group = QGroupBox("Dane klienta (opcjonalnie dla rachunku)")
        self.client_group.setVisible(False)
        
        client_layout = QFormLayout()
        
        self.client_name = QLineEdit()
        self.client_name.setPlaceholderText("Imię i nazwisko/Nazwa firmy")
        client_layout.addRow("Nabywca:", self.client_name)
        
        self.client_address = QLineEdit()
        self.client_address.setPlaceholderText("Adres")
        client_layout.addRow("Adres:", self.client_address)
        
        self.client_group.setLayout(client_layout)
        
        form = QFormLayout()
        form.addRow("Platforma", self.platform)
        form.addRow("Cena PLN", self.pln)
        form.addRow("Data", self.date)
        form.addRow("", self.auto_cost_label)
        form.addRow("", self.create_invoice_checkbox)
        v.addLayout(form)
        v.addWidget(self.client_group)

        # Tabela z pozycjami
        self.items = SortableTableWidget(0, 2)
        self.items.setHorizontalHeaderLabels(["Produkt", "Ilość"])
        v.addWidget(self.items)

        b_add = QPushButton("Dodaj pozycję")
        b_add.clicked.connect(self.add_item)
        v.addWidget(b_add)

        # Przyciski
        button_layout = QHBoxLayout()
        
        b_ok = QPushButton("Zapisz i wygeneruj rachunek")
        b_ok.clicked.connect(self.save_sale_with_invoice)
        b_ok.setStyleSheet("background-color: #2E7D32; font-weight: bold;")
        
        b_ok_simple = QPushButton("Zapisz bez rachunku")
        b_ok_simple.clicked.connect(self.save_sale_without_invoice)
        
        b_cancel = QPushButton("Anuluj")
        b_cancel.clicked.connect(self.reject)
        
        button_layout.addWidget(b_ok)
        button_layout.addWidget(b_ok_simple)
        button_layout.addWidget(b_cancel)
        
        v.addLayout(button_layout)
        
        self.fifo_cost = 0.0

    def toggle_invoice_fields(self, checked):
        """Pokazuje/ukrywa pola danych klienta w zależności od zaznaczenia checkboxa"""
        self.client_group.setVisible(checked)
        
        if checked:
            self.client_group.setTitle("Dane klienta (opcjonalnie dla rachunku)")
            self.client_name.setEnabled(True)
            self.client_address.setEnabled(True)
        else:
            self.client_name.clear()
            self.client_address.clear()
            self.client_name.setEnabled(False)
            self.client_address.setEnabled(False)

    def add_item(self):
        r = self.items.rowCount()
        self.items.insertRow(r)
        
        combo = product_combo(self.db)
        combo.currentIndexChanged.connect(self.update_fifo_cost)
        self.items.setCellWidget(r, 0, combo)

        qty = QSpinBox()
        qty.setMinimum(1)
        qty.setMaximum(100000)
        qty.valueChanged.connect(self.update_fifo_cost)
        self.items.setCellWidget(r, 1, qty)
        
        QTimer.singleShot(100, self.update_fifo_cost)

    def get_items(self):
        items = []
        for r in range(self.items.rowCount()):
            combo = self.items.cellWidget(r, 0)
            qty_widget = self.items.cellWidget(r, 1)
            if combo and qty_widget:
                pid = combo.currentData()
                qty = qty_widget.value()
                items.append((pid, qty))
        return items

    def update_fifo_cost(self):
        try:
            total_cost = 0.0
            items = self.get_items()
            
            for pid, qty in items:
                fifo_batches = self.db.get_fifo_batches(pid, qty)
                if not fifo_batches:
                    QMessageBox.warning(self, "Brak stanu", 
                        f"Brak wystarczającego stanu dla produktu ID: {pid}\n"
                        f"Wymagane: {qty}, dostępne: 0")
                    total_cost = 0.0
                    break
                
                for batch in fifo_batches:
                    batch_qty = min(qty, batch["available_qty"])
                    total_cost += batch["unit_cost"] * batch_qty
                    qty -= batch_qty
                    if qty <= 0:
                        break
            
            self.fifo_cost = total_cost
            self.auto_cost_label.setText(f"Koszt zakupu (FIFO): {total_cost:.2f} PLN")
            return total_cost
        except Exception as e:
            print(f"Błąd w obliczaniu kosztu FIFO: {e}")
            self.fifo_cost = 0.0
            self.auto_cost_label.setText("Koszt zakupu (FIFO): 0.00 PLN")
            return 0.0

    def generate_invoice(self, sale_id, items, total_pln, fifo_cost, profit):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import os
            
            # Próbuj użyć czcionki z polskimi znakami
            font_paths = [
                '/usr/share/fonts/truetype/msttcorefonts/Arial.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                'C:/Windows/Fonts/arial.ttf',
                'arial.ttf'
            ]
            
            font_name = 'Helvetica'
            for font_path in font_paths:
                try:
                    if os.path.exists(font_path):
                        pdfmetrics.registerFont(TTFont('PolishFont', font_path))
                        font_name = 'PolishFont'
                        break
                except:
                    continue
            
            business_info = self.config.get_business_info()
            invoice_config = self.config.get_invoice_config()
            
            invoice_number = self.config.get_next_invoice_number()
            
            # Sprawdź czy zapisywać PDF
            if not self.config.should_save_pdf():
                # Tymczasowy plik
                import tempfile
                filename = f"rachunek_{invoice_number.replace('/', '_')}.pdf"
                path = os.path.join(tempfile.gettempdir(), filename)
            else:
                filename = f"rachunek_{invoice_number.replace('/', '_')}.pdf"
                path = os.path.join(os.getcwd(), "rachunki", filename)
                os.makedirs(os.path.dirname(path), exist_ok=True)
            
            doc = SimpleDocTemplate(
                path,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            story = []
            styles = getSampleStyleSheet()
            
            # Styl tytułu
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName=font_name,
                fontSize=16,
                spaceAfter=30,
                alignment=1
            )
            
            # Styl normalny
            normal_style = ParagraphStyle(
                'Normal',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=10,
                spaceAfter=6
            )
            
            # Styl nagłówka tabeli
            header_style = ParagraphStyle(
                'Header',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=10,
                textColor=colors.whitesmoke,
                alignment=1
            )
            
            # Styl stopki
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=9,
                alignment=1,
                textColor=colors.grey
            )
            
            # Tytuł
            story.append(Paragraph("RACHUMEK UPROSZCZONY", title_style))
            story.append(Spacer(1, 20))
            
            # Dane sprzedawcy
            seller_data = [
                ["SPRZEDAWCA:", ""],
                [f"Imię i nazwisko: {business_info.get('name', '')}", ""],
                [f"Adres: {business_info.get('address', '')}", ""],
                [f"{business_info.get('postal_code', '')} {business_info.get('city', '')}", ""],
                [f"PESEL: {business_info.get('pesel', '')}", ""],
            ]
            
            # Dodaj opcjonalne dane firmy
            company_name = business_info.get('company_name', '')
            company_address = business_info.get('company_address', '')
            phone = business_info.get('phone', '')
            email = business_info.get('email', '')
            
            if company_name:
                seller_data.insert(1, [f"Nazwa firmy: {company_name}", ""])
            if company_address:
                seller_data.insert(2, [f"Adres firmy: {company_address}", ""])
            if phone:
                seller_data.append([f"Telefon: {phone}", ""])
            if email:
                seller_data.append([f"Email: {email}", ""])
            
            if business_info.get('nip'):
                seller_data.append([f"NIP: {business_info.get('nip', '')}", ""])
            
            if business_info.get('regon'):
                seller_data.append([f"REGON: {business_info.get('regon', '')}", ""])
            
            seller_table = Table(seller_data, colWidths=[12*cm, 6*cm])
            seller_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 0), (0, 0), colors.lightgrey),
            ]))
            
            story.append(seller_table)
            story.append(Spacer(1, 20))
            
            # Dane nabywcy
            client_name = self.client_name.text().strip()
            client_address = self.client_address.text().strip()
            
            if client_name or client_address:
                buyer_data = [
                    ["NABYWCA:", ""],
                    [f"Nazwa: {client_name}", ""],
                    [f"Adres: {client_address}", ""],
                ]
                
                buyer_table = Table(buyer_data, colWidths=[12*cm, 6*cm])
                buyer_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 0), (0, 0), colors.lightgrey),
                ]))
                
                story.append(buyer_table)
                story.append(Spacer(1, 20))
            
            # Informacje o fakturze
            invoice_data = [
                ["Numer rachunku:", invoice_number],
                ["Data sprzedaży:", self.date.date().toString("dd.MM.yyyy")],
                ["Data wystawienia:", QDate.currentDate().toString("dd.MM.yyyy")],
                ["Platforma:", self.platform.currentText()],
            ]
            
            invoice_table = Table(invoice_data, colWidths=[6*cm, 12*cm])
            invoice_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font_name),
            ]))
            story.append(invoice_table)
            story.append(Spacer(1, 30))
            
            # Pozycje faktury
            items_data = [["Lp.", "Nazwa towaru/usługi", "Ilość", "Cena jdn. (PLN)", "Wartość (PLN)"]]
            
            for i, (pid, qty) in enumerate(self.get_items(), 1):
                product_info = self.db.get_product_info(pid)
                if product_info:
                    item_price = total_pln / sum(q for _, q in self.get_items()) if self.get_items() else 0
                    item_total = item_price * qty
                    items_data.append([
                        str(i),
                        f"{product_info['sku']} - {product_info['title']}",
                        str(qty),
                        f"{item_price:.2f}",
                        f"{item_total:.2f}"
                    ])
            
            items_table = Table(items_data, colWidths=[1*cm, 9*cm, 2*cm, 3*cm, 3*cm])
            items_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            
            story.append(items_table)
            story.append(Spacer(1, 20))
            
            # Podsumowanie
            summary_data = [
                ["RAZEM DO ZAPŁATY:", f"{total_pln:.2f} PLN"],
                ["W tym:", ""],
                ["- koszt własny:", f"{fifo_cost:.2f} PLN"],
                ["- zysk brutto:", f"{profit:.2f} PLN"],
            ]
            
            summary_table = Table(summary_data, colWidths=[12*cm, 6*cm])
            summary_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (0, 0), 12),
                ('FONTSIZE', (1, 0), (1, 0), 12),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('TEXTCOLOR', (1, 0), (1, 0), colors.red),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ]))
            
            story.append(summary_table)
            story.append(Spacer(1, 30))
            
            # Stopka
            footer_text = self.config.get_invoice_footer()
            story.append(Paragraph(footer_text, footer_style))
            
            story.append(Paragraph("Rachunek uproszczony jest dokumentem sprzedaży dla potrzeb ewidencji przychodów", 
                                 ParagraphStyle('Info', parent=styles['Normal'], fontName=font_name, fontSize=8, alignment=1)))
            
            doc.build(story)
            
            # Zapisz fakturę do bazy danych
            success = self.db.add_invoice(
                invoice_number=invoice_number,
                sale_order_id=sale_id,
                file_path=path,
                customer_name=client_name,
                customer_address=client_address,
                issue_date=QDate.currentDate().toString("yyyy-MM-dd"),
                total_amount=total_pln
            )
            
            if not success:
                print("Uwaga: Nie udało się zapisać faktury do bazy danych")
            
            # Otwórz automatycznie jeśli ustawione
            if self.config.should_auto_open_invoice():
                import subprocess
                try:
                    if os.name == 'nt':
                        os.startfile(path)
                    elif os.name == 'posix':
                        subprocess.call(['open', path] if sys.platform == 'darwin' else ['xdg-open', path])
                except:
                    pass
            
            return path, invoice_number
            
        except Exception as e:
            print(f"Błąd generowania rachunku: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def save_sale_with_invoice(self):
        if not self.create_invoice_checkbox.isChecked():
            QMessageBox.warning(self, "Informacja", 
                              "Aby wygenerować rachunek, zaznacz opcję 'Wygeneruj rachunek uproszczony'")
            return self.save_sale_without_invoice()
        
        business_info = self.config.get_business_info()
        required_fields = ['name', 'address', 'postal_code', 'city', 'pesel']
        for field in required_fields:
            if not business_info.get(field):
                QMessageBox.warning(self, "Brak danych", 
                                  f"Uzupełnij dane sprzedawcy w konfiguracji.\nBrakujące pole: {field}")
                return
        
        sale_id = self._save_sale()
        if sale_id:
            invoice_path, invoice_number = self.generate_invoice(
                sale_id, 
                self.get_items(), 
                self.pln.value(), 
                self.fifo_cost,
                self.pln.value() - self.fifo_cost
            )
            
            if invoice_path:
                QMessageBox.information(self, "Sukces", 
                                      f"Sprzedaż została dodana.\nRachunek {invoice_number} wygenerowany:\n{invoice_path}")
                self.accept()
    
    def save_sale_without_invoice(self):
        sale_id = self._save_sale()
        if sale_id:
            QMessageBox.information(self, "Sukces", "Sprzedaż została dodana (bez rachunku).")
            self.accept()
    
    def _save_sale(self):
        items = self.get_items()
        if not items:
            QMessageBox.warning(self, "Brak pozycji", "Dodaj przynajmniej jedną pozycję do sprzedaży.")
            return None
            
        for pid, qty in items:
            if not self.db.check_stock(pid, qty):
                product_info = self.db.get_product_info(pid)
                if product_info:
                    QMessageBox.warning(self, "Brak stanu", 
                        f"Brak wystarczającego stanu dla produktu:\n"
                        f"SKU: {product_info['sku']}\n"
                        f"Nazwa: {product_info['title']}\n"
                        f"Wymagane: {qty}, dostępne: {product_info['stock']}")
                return None
        
        fifo_cost = self.update_fifo_cost()
        
        date = self.date.date().toString("yyyy-MM-dd")
        try:
            eur_rate = get_eur_rate(date)
            eur = round(self.pln.value() / eur_rate, 2) if eur_rate else 0
        except:
            eur = 0
        
        try:
            sale_id = self.db.add_sale_order_with_reset(
                self.platform.currentText(),
                self.pln.value(),
                eur,
                date,
                items,
                fifo_cost
            )
            return sale_id
            
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie udało się dodać sprzedaży:\n{str(e)}")
            return None

# ================== NOWE DIALOGI - DODANE FUNKCJE ==================

class OpenDatabaseDialog(QDialog):
    """Dialog do otwierania istniejącej bazy danych"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Otwórz bazę danych")
        self.resize(500, 300)
        
        v = QVBoxLayout(self)
        
        # Informacje
        info_label = QLabel("Wybierz istniejącą bazę danych (.db) lub utwórz nową:")
        v.addWidget(info_label)
        
        # Lista dostępnych baz
        self.db_list = QListWidget()
        self.refresh_db_list()
        v.addWidget(self.db_list)
        
        # Ścieżka ręczna
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Ścieżka do pliku .db...")
        btn_browse = QPushButton("Przeglądaj...")
        btn_browse.clicked.connect(self.browse_db_file)
        
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(btn_browse)
        v.addLayout(path_layout)
        
        # Przyciski akcji
        btn_layout = QHBoxLayout()
        
        btn_open = QPushButton("Otwórz")
        btn_open.clicked.connect(self.open_selected)
        btn_open.setStyleSheet("background-color: #2E7D32; font-weight: bold;")
        
        btn_new = QPushButton("Utwórz nową")
        btn_new.clicked.connect(self.create_new)
        
        btn_cancel = QPushButton("Anuluj")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_open)
        btn_layout.addWidget(btn_new)
        btn_layout.addWidget(btn_cancel)
        
        v.addLayout(btn_layout)
    
    def refresh_db_list(self):
        """Odśwież listę dostępnych baz danych w bieżącym folderze"""
        self.db_list.clear()
        current_dir = os.getcwd()
        
        for file in os.listdir(current_dir):
            if file.endswith('.db'):
                size = os.path.getsize(file)
                size_str = f"({size/1024:.1f} KB)" if size < 1024*1024 else f"({size/(1024*1024):.1f} MB)"
                item_text = f"{file} {size_str}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, file)
                self.db_list.addItem(item)
    
    def browse_db_file(self):
        """Przeglądaj pliki bazy danych"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz bazę danych", 
            os.getcwd(), 
            "Bazy danych (*.db);;Wszystkie pliki (*.*)"
        )
        if path:
            self.path_edit.setText(path)
    
    def open_selected(self):
        """Otwórz wybraną bazę danych"""
        if self.db_list.currentItem():
            db_file = self.db_list.currentItem().data(Qt.UserRole)
            path = os.path.join(os.getcwd(), db_file)
        elif self.path_edit.text().strip():
            path = self.path_edit.text().strip()
        else:
            QMessageBox.warning(self, "Brak wyboru", "Wybierz bazę danych z listy lub podaj ścieżkę.")
            return
        
        if not os.path.exists(path):
            QMessageBox.warning(self, "Brak pliku", f"Plik nie istnieje:\n{path}")
            return
        
        if not path.endswith('.db'):
            QMessageBox.warning(self, "Nieprawidłowy format", "Wybierz plik z rozszerzeniem .db")
            return
        
        self.selected_path = path
        self.accept()
    
    def create_new(self):
        """Utwórz nową bazę danych"""
        path, _ = QFileDialog.getSaveFileName(
            self, "Utwórz nową bazę danych",
            os.getcwd(),
            "Bazy danych (*.db)"
        )
        
        if path:
            if not path.endswith('.db'):
                path += '.db'
            
            # Utwórz pustą bazę
            import shutil
            try:
                # Sprawdź czy istnieje domyślna baza do skopiowania
                if os.path.exists('data.db'):
                    shutil.copy('data.db', path)
                else:
                    # Utwórz pustą bazę przez wywołanie DB
                    from db import DB
                    temp_db = DB(path)
                    temp_db.conn.close()
                
                QMessageBox.information(self, "Sukces", f"Utworzono nową bazę danych:\n{path}")
                self.selected_path = path
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Nie udało się utworzyć bazy:\n{str(e)}")

class BackupDialog(QDialog):
    """Dialog do tworzenia kopii zapasowej bazy danych"""
    def __init__(self, current_db_path, parent=None):
        super().__init__(parent)
        self.current_db_path = current_db_path
        self.setWindowTitle("Archiwizuj bazę danych")
        self.resize(500, 300)
        
        v = QVBoxLayout(self)
        
        # Informacje o aktualnej bazie
        info_label = QLabel(f"Aktualna baza danych: {os.path.basename(current_db_path)}")
        info_label.setWordWrap(True)
        v.addWidget(info_label)
        
        # Opcje archiwizacji
        group = QGroupBox("Opcje archiwizacji")
        group_layout = QVBoxLayout()
        
        self.rb_default = QRadioButton("Archiwizuj do folderu 'backups' (automatyczna nazwa)")
        self.rb_default.setChecked(True)
        group_layout.addWidget(self.rb_default)
        
        self.rb_custom = QRadioButton("Zapisz kopię jako... (wybierz lokalizację ręcznie)")
        group_layout.addWidget(self.rb_custom)
        
        self.custom_path_edit = QLineEdit()
        self.custom_path_edit.setPlaceholderText("Ścieżka do zapisania kopii...")
        self.custom_path_edit.setEnabled(False)
        
        btn_browse = QPushButton("Wybierz...")
        btn_browse.clicked.connect(self.browse_backup_path)
        btn_browse.setEnabled(False)
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.custom_path_edit)
        path_layout.addWidget(btn_browse)
        group_layout.addLayout(path_layout)
        
        self.rb_default.toggled.connect(lambda: self.update_path_enabled())
        self.rb_custom.toggled.connect(lambda: self.update_path_enabled())
        
        group.setLayout(group_layout)
        v.addWidget(group)
        
        # Kompresja
        self.cb_compress = QCheckBox("Skompresuj kopię (format .zip)")
        self.cb_compress.setChecked(True)
        v.addWidget(self.cb_compress)
        
        # Dodatkowe opcje
        self.cb_backup_config = QCheckBox("Uwzględnij plik konfiguracyjny (config.json)")
        self.cb_backup_config.setChecked(True)
        v.addWidget(self.cb_backup_config)
        
        self.cb_backup_invoices = QCheckBox("Uwzględnij folder z rachunkami (rachunki/)")
        self.cb_backup_invoices.setChecked(True)
        v.addWidget(self.cb_backup_invoices)
        
        v.addStretch()
        
        # Przyciski
        btn_layout = QHBoxLayout()
        
        btn_backup = QPushButton("Utwórz kopię zapasową")
        btn_backup.clicked.connect(self.create_backup)
        btn_backup.setStyleSheet("background-color: #2E7D32; font-weight: bold;")
        
        btn_cancel = QPushButton("Anuluj")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_backup)
        btn_layout.addWidget(btn_cancel)
        
        v.addLayout(btn_layout)
    
    def update_path_enabled(self):
        """Włącz/wyłącz pola edycji ścieżki"""
        enabled = self.rb_custom.isChecked()
        self.custom_path_edit.setEnabled(enabled)
        # Znajdź i włącz przycisk przeglądania
        for i in range(self.layout().count()):
            widget = self.layout().itemAt(i).widget()
            if isinstance(widget, QGroupBox):
                for j in range(widget.layout().count()):
                    item = widget.layout().itemAt(j)
                    if item and item.layout():
                        for k in range(item.layout().count()):
                            sub_widget = item.layout().itemAt(k).widget()
                            if isinstance(sub_widget, QPushButton) and sub_widget.text() == "Wybierz...":
                                sub_widget.setEnabled(enabled)
    
    def browse_backup_path(self):
        """Wybierz ścieżkę do zapisania kopii"""
        default_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        path, _ = QFileDialog.getSaveFileName(
            self, "Zapisz kopię zapasową",
            os.path.join(os.getcwd(), default_name),
            "Bazy danych (*.db);;Wszystkie pliki (*.*)"
        )
        if path:
            self.custom_path_edit.setText(path)
    
    def create_backup(self):
        """Utwórz kopię zapasową"""
        try:
            import shutil
            import zipfile
            
            if self.rb_default.isChecked():
                # Utwórz folder backups jeśli nie istnieje
                backup_dir = os.path.join(os.getcwd(), "backups")
                os.makedirs(backup_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_name = f"backup_{timestamp}.db"
                backup_path = os.path.join(backup_dir, backup_name)
                
                # Skopiuj bazę danych
                shutil.copy2(self.current_db_path, backup_path)
                
                if self.cb_compress.isChecked():
                    zip_path = backup_path.replace('.db', '.zip')
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        zipf.write(backup_path, os.path.basename(backup_path))
                        
                        if self.cb_backup_config.isChecked() and os.path.exists('config.json'):
                            zipf.write('config.json', 'config.json')
                        
                        if self.cb_backup_invoices.isChecked() and os.path.exists('rachunki'):
                            for root, dirs, files in os.walk('rachunki'):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    arcname = os.path.relpath(file_path, start='.')
                                    zipf.write(file_path, arcname)
                    
                    os.remove(backup_path)
                    backup_path = zip_path
                
                QMessageBox.information(self, "Sukces", 
                    f"Utworzono kopię zapasową:\n{backup_path}")
                
            else:
                backup_path = self.custom_path_edit.text().strip()
                if not backup_path:
                    QMessageBox.warning(self, "Brak ścieżki", "Podaj ścieżkę do zapisania kopii.")
                    return
                
                shutil.copy2(self.current_db_path, backup_path)
                
                if self.cb_compress.isChecked():
                    zip_path = backup_path.replace('.db', '.zip')
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        zipf.write(backup_path, os.path.basename(backup_path))
                    
                    os.remove(backup_path)
                    backup_path = zip_path
                
                QMessageBox.information(self, "Sukces", 
                    f"Utworzono kopię zapasową:\n{backup_path}")
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Błąd", 
                f"Nie udało się utworzyć kopii zapasowej:\n{str(e)}")

class ImportExportDialog(QDialog):
    """Dialog do importu/eksportu danych"""
    def __init__(self, db, config, parent=None):
        super().__init__(parent)
        self.db = db
        self.config = config
        self.setWindowTitle("Import/Export danych")
        self.resize(600, 500)
        
        v = QVBoxLayout(self)
        
        # Sekcja importu
        import_group = QGroupBox("Import danych")
        import_layout = QVBoxLayout()
        
        self.import_combo = QComboBox()
        self.import_combo.addItems([
            "Wybierz typ importu...",
            "Towary z pliku CSV/Excel",
            "Cennik dostawcy z CSV/Excel",
            "Transakcje bankowe z CSV",
            "Rachunki z plików PDF"
        ])
        import_layout.addWidget(self.import_combo)
        
        self.import_widget = QStackedWidget()
        
        # Widget dla importu towarów
        import_products_widget = QWidget()
        import_products_layout = QVBoxLayout()
        import_products_layout.addWidget(QLabel("Format pliku: SKU;Nazwa;Stan początkowy;Cena zakupu"))
        import_products_layout.addWidget(QLabel("Wskazówka: Użyj CSV z separatorem średnika"))
        self.import_products_btn = QPushButton("Wybierz plik do importu...")
        self.import_products_btn.clicked.connect(lambda: self.import_products())
        import_products_layout.addWidget(self.import_products_btn)
        import_products_widget.setLayout(import_products_layout)
        self.import_widget.addWidget(import_products_widget)
        
        # Widget dla importu cennika
        import_prices_widget = QWidget()
        import_prices_layout = QVBoxLayout()
        import_prices_layout.addWidget(QLabel("Format pliku: SKU;Cena zakupu;Data ważności"))
        self.import_prices_btn = QPushButton("Wybierz plik cennika...")
        import_prices_layout.addWidget(self.import_prices_btn)
        import_prices_widget.setLayout(import_prices_layout)
        self.import_widget.addWidget(import_prices_widget)
        
        # Pusty widget dla pozostałych opcji
        for _ in range(3):
            empty_widget = QWidget()
            empty_layout = QVBoxLayout()
            empty_layout.addWidget(QLabel("Funkcja w przygotowaniu..."))
            empty_widget.setLayout(empty_layout)
            self.import_widget.addWidget(empty_widget)
        
        import_layout.addWidget(self.import_widget)
        import_group.setLayout(import_layout)
        v.addWidget(import_group)
        
        # Sekcja eksportu
        export_group = QGroupBox("Eksport danych")
        export_layout = QVBoxLayout()
        
        self.export_combo = QComboBox()
        self.export_combo.addItems([
            "Wybierz typ eksportu...",
            "Lista produktów do PDF",
            "Raport magazynowy do Excel",
            "Lista faktur do CSV",
            "Ewidencja sprzedaży do PDF"
        ])
        export_layout.addWidget(self.export_combo)
        
        self.export_widget = QStackedWidget()
        
        # Widget dla eksportu produktów
        export_products_widget = QWidget()
        export_products_layout = QVBoxLayout()
        export_products_layout.addWidget(QLabel("Wygeneruj listę produktów w formacie PDF"))
        self.export_products_btn = QPushButton("Eksportuj produkty do PDF...")
        self.export_products_btn.clicked.connect(lambda: self.export_products_pdf())
        export_products_layout.addWidget(self.export_products_btn)
        export_products_widget.setLayout(export_products_layout)
        self.export_widget.addWidget(export_products_widget)
        
        # Widget dla eksportu magazynu
        export_inventory_widget = QWidget()
        export_inventory_layout = QVBoxLayout()
        export_inventory_layout.addWidget(QLabel("Wygeneruj pełny raport magazynowy"))
        self.export_inventory_btn = QPushButton("Eksportuj raport do Excel...")
        export_inventory_layout.addWidget(self.export_inventory_btn)
        export_inventory_widget.setLayout(export_inventory_layout)
        self.export_widget.addWidget(export_inventory_widget)
        
        # Pusty widget dla pozostałych opcji
        for _ in range(2):
            empty_widget = QWidget()
            empty_layout = QVBoxLayout()
            empty_layout.addWidget(QLabel("Funkcja w przygotowaniu..."))
            empty_widget.setLayout(empty_layout)
            self.export_widget.addWidget(empty_widget)
        
        export_layout.addWidget(self.export_widget)
        export_group.setLayout(export_layout)
        v.addWidget(export_group)
        
        # Przyciski
        btn_layout = QHBoxLayout()
        btn_close = QPushButton("Zamknij")
        btn_close.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        
        v.addLayout(btn_layout)
        
        # Podłączenie sygnałów
        self.import_combo.currentIndexChanged.connect(self.import_widget.setCurrentIndex)
        self.export_combo.currentIndexChanged.connect(self.export_widget.setCurrentIndex)
    
    def import_products(self):
        """Import produktów z pliku CSV"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz plik do importu",
            os.getcwd(),
            "Pliki CSV (*.csv);;Pliki Excel (*.xlsx *.xls);;Wszystkie pliki (*.*)"
        )
        
        if not path:
            return
        
        try:
            imported = 0
            skipped = 0
            errors = []
            
            if path.endswith('.csv'):
                with open(path, 'r', encoding='utf-8') as f:
                    import csv
                    reader = csv.reader(f, delimiter=';')
                    
                    for row_num, row in enumerate(reader, 1):
                        if len(row) < 2:
                            continue
                        
                        sku = row[0].strip()
                        title = row[1].strip()
                        
                        if not sku or not title:
                            errors.append(f"Wiersz {row_num}: Brak SKU lub nazwy")
                            continue
                        
                        if self.db.check_sku_exists(sku):
                            skipped += 1
                            continue
                        
                        try:
                            self.db.add_product(sku, title)
                            imported += 1
                            
                            # Jeśli jest stan początkowy
                            if len(row) >= 3 and row[2].strip():
                                try:
                                    stock = int(row[2].strip())
                                    if stock > 0:
                                        pid = self.db.get_product_id_by_sku(sku)
                                        if pid:
                                            self.db.update_stock(pid, stock)
                                except ValueError:
                                    pass
                            
                        except Exception as e:
                            errors.append(f"Wiersz {row_num}: {str(e)}")
            
            QMessageBox.information(self, "Import zakończony",
                f"Zaimportowano: {imported} produktów\n"
                f"Pominięto (już istnieją): {skipped}\n"
                f"Błędy: {len(errors)}")
            
            if errors:
                QMessageBox.warning(self, "Błędy importu", 
                    "Niektóre wiersze nie zostały zaimportowane:\n\n" + 
                    "\n".join(errors[:10]) + 
                    ("\n\n... i więcej" if len(errors) > 10 else ""))
        
        except Exception as e:
            QMessageBox.critical(self, "Błąd importu", 
                f"Nie udało się zaimportować pliku:\n{str(e)}")
    
    def export_products_pdf(self):
        """Eksport listy produktów do PDF"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
            from reportlab.lib.units import cm
            
            path, _ = QFileDialog.getSaveFileName(
                self, "Zapisz listę produktów",
                os.path.join(os.getcwd(), f"produkty_{datetime.now().strftime('%Y%m%d')}.pdf"),
                "Pliki PDF (*.pdf)"
            )
            
            if not path:
                return
            
            products = self.db.list_products()
            
            doc = SimpleDocTemplate(path, pagesize=A4,
                                  rightMargin=2*cm, leftMargin=2*cm,
                                  topMargin=2*cm, bottomMargin=2*cm)
            
            story = []
            styles = getSampleStyleSheet()
            
            story.append(Paragraph("LISTA PRODUKTÓW W MAGAZYNIE", 
                                 styles['Title']))
            story.append(Spacer(1, 20))
            story.append(Paragraph(f"Data wygenerowania: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                                 styles['Normal']))
            story.append(Spacer(1, 30))
            
            # Tabela z produktami
            data = [["SKU", "Nazwa", "Stan"]]
            
            for p in products:
                data.append([p['sku'], p['title'], str(p['stock'])])
            
            table = Table(data, colWidths=[4*cm, 10*cm, 2*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (2, 1), (2, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke])
            ]))
            
            story.append(table)
            story.append(Spacer(1, 20))
            
            story.append(Paragraph(f"Łącznie produktów: {len(products)}", styles['Normal']))
            
            doc.build(story)
            
            QMessageBox.information(self, "Sukces", 
                f"Lista produktów została wyeksportowana:\n{path}")
        
        except Exception as e:
            QMessageBox.critical(self, "Błąd eksportu", 
                f"Nie udało się wyeksportować do PDF:\n{str(e)}")

class PrintDialog(QDialog):
    """Dialog do drukowania"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Drukowanie")
        self.resize(500, 400)
        
        v = QVBoxLayout(self)
        
        # Wybór drukarki
        printer_group = QGroupBox("Wybór drukarki")
        printer_layout = QVBoxLayout()
        
        self.printer_combo = QComboBox()
        self.refresh_printers()
        printer_layout.addWidget(QLabel("Drukarka:"))
        printer_layout.addWidget(self.printer_combo)
        
        btn_refresh = QPushButton("Odśwież listę")
        btn_refresh.clicked.connect(self.refresh_printers)
        printer_layout.addWidget(btn_refresh)
        
        btn_properties = QPushButton("Właściwości drukarki...")
        btn_properties.clicked.connect(self.show_printer_properties)
        printer_layout.addWidget(btn_properties)
        
        printer_group.setLayout(printer_layout)
        v.addWidget(printer_group)
        
        # Ustawienia druku
        settings_group = QGroupBox("Ustawienia druku")
        settings_layout = QVBoxLayout()
        
        # Zakres stron
        pages_layout = QHBoxLayout()
        pages_layout.addWidget(QLabel("Zakres stron:"))
        
        self.rb_all = QRadioButton("Wszystkie")
        self.rb_all.setChecked(True)
        pages_layout.addWidget(self.rb_all)
        
        self.rb_range = QRadioButton("Strony:")
        pages_layout.addWidget(self.rb_range)
        
        self.page_from = QSpinBox()
        self.page_from.setRange(1, 999)
        self.page_from.setValue(1)
        self.page_from.setEnabled(False)
        pages_layout.addWidget(self.page_from)
        
        pages_layout.addWidget(QLabel("do"))
        
        self.page_to = QSpinBox()
        self.page_to.setRange(1, 999)
        self.page_to.setValue(1)
        self.page_to.setEnabled(False)
        pages_layout.addWidget(self.page_to)
        
        pages_layout.addStretch()
        
        self.rb_all.toggled.connect(self.update_page_range_enabled)
        self.rb_range.toggled.connect(self.update_page_range_enabled)
        
        settings_layout.addLayout(pages_layout)
        
        # Liczba kopii
        copies_layout = QHBoxLayout()
        copies_layout.addWidget(QLabel("Liczba kopii:"))
        
        self.copies_spin = QSpinBox()
        self.copies_spin.setRange(1, 99)
        self.copies_spin.setValue(1)
        copies_layout.addWidget(self.copies_spin)
        
        copies_layout.addStretch()
        settings_layout.addLayout(copies_layout)
        
        # Orientacja
        orientation_layout = QHBoxLayout()
        orientation_layout.addWidget(QLabel("Orientacja:"))
        
        self.rb_portrait = QRadioButton("Pionowa")
        self.rb_portrait.setChecked(True)
        orientation_layout.addWidget(self.rb_portrait)
        
        self.rb_landscape = QRadioButton("Pozioma")
        orientation_layout.addWidget(self.rb_landscape)
        
        orientation_layout.addStretch()
        settings_layout.addLayout(orientation_layout)
        
        # Zaawansowane
        self.cb_color = QCheckBox("Druk kolorowy")
        self.cb_color.setChecked(True)
        settings_layout.addWidget(self.cb_color)
        
        self.cb_duplex = QCheckBox("Druk dwustronny")
        settings_layout.addWidget(self.cb_duplex)
        
        settings_group.setLayout(settings_layout)
        v.addWidget(settings_group)
        
        # Podgląd
        preview_group = QGroupBox("Podgląd wydruku")
        preview_layout = QVBoxLayout()
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(100)
        self.preview_text.setPlainText("Przykładowy podgląd wydruku...\nTutaj będzie wyświetlana zawartość dokumentu przed drukiem.")
        preview_layout.addWidget(self.preview_text)
        
        preview_group.setLayout(preview_layout)
        v.addWidget(preview_group)
        
        # Przyciski
        btn_layout = QHBoxLayout()
        
        btn_print = QPushButton("Drukuj")
        btn_print.clicked.connect(self.print_document)
        btn_print.setStyleSheet("background-color: #2E7D32; font-weight: bold;")
        
        btn_preview = QPushButton("Podgląd wydruku...")
        btn_preview.clicked.connect(self.print_preview)
        
        btn_cancel = QPushButton("Anuluj")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_print)
        btn_layout.addWidget(btn_preview)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        
        v.addLayout(btn_layout)
    
    def refresh_printers(self):
        """Odśwież listę dostępnych drukarek"""
        from PySide6.QtPrintSupport import QPrinterInfo
        self.printer_combo.clear()
        
        printers = QPrinterInfo.availablePrinters()
        for printer in printers:
            self.printer_combo.addItem(printer.printerName(), printer)
    
    def update_page_range_enabled(self):
        """Włącz/wyłącz pola zakresu stron"""
        enabled = self.rb_range.isChecked()
        self.page_from.setEnabled(enabled)
        self.page_to.setEnabled(enabled)
    
    def show_printer_properties(self):
        """Pokaż właściwości wybranej drukarki"""
        if self.printer_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Brak drukarki", "Nie wybrano drukarki.")
            return
        
        printer_info = self.printer_combo.currentData()
        printer_name = printer_info.printerName()
        
        QMessageBox.information(self, "Właściwości drukarki",
            f"Drukarka: {printer_name}\n\n"
            f"Stan: {'Gotowa' if printer_info.isDefault() else 'Dostępna'}\n"
            f"Obsługuje kolor: {'Tak' if printer_info.supportsCustomPageSizes() else 'Nie'}\n"
            f"Obsługuje duplex: {'Tak' if printer_info.supportsMultipleCopies() else 'Nie'}")
    
    def print_document(self):
        """Wydrukuj dokument"""
        if self.printer_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Brak drukarki", "Wybierz drukarkę z listy.")
            return
        
        printer_info = self.printer_combo.currentData()
        
        # Tutaj można dodać logikę drukowania konkretnego dokumentu
        QMessageBox.information(self, "Drukowanie",
            f"Rozpoczęto drukowanie na drukarce:\n{printer_info.printerName()}\n\n"
            f"Kopie: {self.copies_spin.value()}\n"
            f"Orientacja: {'Pionowa' if self.rb_portrait.isChecked() else 'Pozioma'}\n"
            f"Zakres stron: {'Wszystkie' if self.rb_all.isChecked() else f'{self.page_from.value()}-{self.page_to.value()}'}")
        
        self.accept()
    
    def print_preview(self):
        """Pokaż podgląd wydruku"""
        QMessageBox.information(self, "Podgląd wydruku",
            "Ta funkcja jest w przygotowaniu.\n"
            "W przyszłości będzie tutaj wyświetlany podgląd dokumentu przed drukiem.")

# ================== MAIN (Z MENU RIBBON - POPRAWIONYM) ==================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        
        # Wczytaj ścieżkę bazy z konfiguracji
        self.db_path = self.config.get_database_path()
        self.db = DB(self.db_path)
        
        # Ustaw tytuł okna z nazwą bazy
        db_info = self.config.get_database_info()
        self.setWindowTitle(f"System Magazynowo-Sprzedażowy v{APP_VERSION} - {db_info['filename']}")
        self.resize(1200, 700)

        self.setup_ui()
        self.setup_menu_bar()
        self.setup_toolbar()
        
        self.refresh()

    def setup_ui(self):
        """Konfiguruje główny interfejs"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Tabela produktów
        self.table = SortableTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "SKU", "Nazwa", "Stan", ""])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        main_layout.addWidget(self.table)
        
        # Pasek statusu z informacją o bazie danych
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status_bar()

    def update_status_bar(self):
        """Aktualizuje pasek statusu z informacją o bazie danych"""
        db_info = self.config.get_database_info()
        status_text = f"Baza danych: {db_info['filename']}"
        
        if db_info['last_opened']:
            status_text += f" | Ostatnio otwarta: {db_info['last_opened']}"
        
        self.status_bar.showMessage(status_text)

    def setup_menu_bar(self):
        """Konfiguruje menu ribbon - POPRAWIONE DO POZIOMEGO"""
        menu_bar = self.menuBar()
        
        # ========== MENU PLIK ==========
        file_menu = menu_bar.addMenu("&Plik")
        
        # Nowe funkcje
        open_last_action = QAction("&Otwórz ostatnią bazę", self)
        open_last_action.triggered.connect(self.open_last_database)
        open_last_action.setToolTip("Otwórz ostatnio używaną bazę danych")
        file_menu.addAction(open_last_action)
        
        open_db_action = QAction("&Otwórz bazę danych...", self)
        open_db_action.triggered.connect(self.open_database)
        file_menu.addAction(open_db_action)
        
        backup_action = QAction("&Archiwizuj bazę danych...", self)
        backup_action.triggered.connect(self.backup_database)
        file_menu.addAction(backup_action)
        
        file_menu.addSeparator()
        
        # Import/Export
        import_export_action = QAction("&Import/Export...", self)
        import_export_action.triggered.connect(self.import_export)
        file_menu.addAction(import_export_action)
        
        file_menu.addSeparator()
        
        # Drukowanie
        print_action = QAction("&Drukowanie...", self)
        print_action.setShortcut("Ctrl+P")
        print_action.triggered.connect(self.print_dialog)
        file_menu.addAction(print_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("&Zakończ", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # ========== MENU MAGAZYN ==========
        warehouse_menu = menu_bar.addMenu("&Magazyn")
        
        add_product_action = QAction("&Dodaj produkt...", self)
        add_product_action.setShortcut("Ctrl+N")
        add_product_action.triggered.connect(self.add_product)
        warehouse_menu.addAction(add_product_action)
        
        delete_product_action = QAction("&Usuń produkt...", self)
        delete_product_action.setShortcut("Ctrl+Shift+P")
        delete_product_action.triggered.connect(self.delete_product)
        warehouse_menu.addAction(delete_product_action)
        
        warehouse_menu.addSeparator()
        
        add_purchase_action = QAction("&Dodaj zakup...", self)
        add_purchase_action.setShortcut("Ctrl+Z")
        add_purchase_action.triggered.connect(self.add_purchase)
        warehouse_menu.addAction(add_purchase_action)
        
        view_purchases_action = QAction("&Historia zakupów...", self)
        view_purchases_action.setShortcut("Ctrl+Shift+Z")
        view_purchases_action.triggered.connect(self.show_purchases)
        warehouse_menu.addAction(view_purchases_action)
        
        warehouse_menu.addSeparator()
        
        inventory_action = QAction("&Inwentaryzacja magazynu", self)
        inventory_action.triggered.connect(self.inventory)
        warehouse_menu.addAction(inventory_action)
        
        # ========== MENU SPRZEDAŻ ==========
        sales_menu = menu_bar.addMenu("&Sprzedaż")
        
        add_sale_action = QAction("&Dodaj sprzedaż...", self)
        add_sale_action.setShortcut("Ctrl+S")
        add_sale_action.triggered.connect(self.add_sale)
        sales_menu.addAction(add_sale_action)
        
        view_sales_action = QAction("&Historia sprzedaży...", self)
        view_sales_action.setShortcut("Ctrl+Shift+S")
        view_sales_action.triggered.connect(self.show_sales)
        sales_menu.addAction(view_sales_action)
        
        sales_menu.addSeparator()
        
        view_invoices_action = QAction("&Historia rachunków...", self)
        view_invoices_action.triggered.connect(self.show_invoices)
        sales_menu.addAction(view_invoices_action)
        
        # ========== MENU RAPORTY ==========
        reports_menu = menu_bar.addMenu("&Raporty")
        
        monthly_report_action = QAction("&Raport miesięczny...", self)
        monthly_report_action.triggered.connect(lambda: self.show_report_dialog("monthly"))
        reports_menu.addAction(monthly_report_action)
        
        quarterly_report_action = QAction("&Raport kwartalny...", self)
        quarterly_report_action.triggered.connect(lambda: self.show_report_dialog("quarterly"))
        reports_menu.addAction(quarterly_report_action)
        
        yearly_report_action = QAction("&Raport roczny...", self)
        yearly_report_action.triggered.connect(lambda: self.show_report_dialog("yearly"))
        reports_menu.addAction(yearly_report_action)
        
        custom_report_action = QAction("&Raport okresowy...", self)
        custom_report_action.triggered.connect(lambda: self.show_report_dialog("custom"))
        reports_menu.addAction(custom_report_action)
        
        # ========== MENU KONFIGURACJA ==========
        config_menu = menu_bar.addMenu("&Konfiguracja")
        
        business_info_action = QAction("&Dane osobiste...", self)
        business_info_action.triggered.connect(self.business_info)
        config_menu.addAction(business_info_action)
        
        invoice_config_action = QAction("&Konfiguracja rachunków...", self)
        invoice_config_action.triggered.connect(self.invoice_config)
        config_menu.addAction(invoice_config_action)
        
        # NOWE: Submenu Konfiguracja dodatkowe
        config_submenu = QMenu("&Dodatkowe", self)
        
        limits_config_action = QAction("&Limity US...", self)
        limits_config_action.triggered.connect(self.limits_config)
        config_submenu.addAction(limits_config_action)
        
        config_menu.addMenu(config_submenu)
        
        # ========== MENU POMOC ==========
        help_menu = menu_bar.addMenu("&Pomoc")
        
        refresh_action = QAction("&Odśwież", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh)
        help_menu.addAction(refresh_action)
        
        help_menu.addSeparator()
        
        about_action = QAction("&O programie...", self)
        about_action.triggered.connect(self.about)
        help_menu.addAction(about_action)

    def setup_toolbar(self):
        """Konfiguruje pasek narzędzi - UPROSZCZONY"""
        toolbar = QToolBar("Główne narzędzia")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # Przycisk dodaj produkt
        add_product_btn = QAction("➕ Dodaj produkt", self)
        add_product_btn.triggered.connect(self.add_product)
        toolbar.addAction(add_product_btn)
        
        toolbar.addSeparator()
        
        # Przycisk dodaj zakup
        add_purchase_btn = QAction("📦 Dodaj zakup", self)
        add_purchase_btn.triggered.connect(self.add_purchase)
        toolbar.addAction(add_purchase_btn)
        
        toolbar.addSeparator()
        
        # Przycisk dodaj sprzedaż
        add_sale_btn = QAction("💰 Dodaj sprzedaż", self)
        add_sale_btn.triggered.connect(self.add_sale)
        toolbar.addAction(add_sale_btn)
        
        toolbar.addSeparator()
        
        # Przycisk odśwież
        refresh_btn = QAction("⟳ Odśwież", self)
        refresh_btn.triggered.connect(self.refresh)
        toolbar.addAction(refresh_btn)
        
        toolbar.addSeparator()
        
        # Przycisk raportu miesięcznego
        report_btn = QAction("📊 Raport miesięczny", self)
        report_btn.triggered.connect(lambda: self.show_report_dialog("monthly"))
        toolbar.addAction(report_btn)

    def open_last_database(self):
        """Otwiera ostatnio używaną bazę danych"""
        db_info = self.config.get_database_info()
        
        if db_info["exists"]:
            try:
                # Zamknij aktualną bazę
                if hasattr(self.db, 'conn'):
                    self.db.conn.close()
                
                # Otwórz ostatnią bazę
                self.db_path = db_info["path"]
                self.db = DB(self.db_path)
                
                # Odśwież interfejs
                self.refresh()
                
                # Zaktualizuj tytuł
                self.setWindowTitle(f"System Magazynowo-Sprzedażowy v{APP_VERSION} - {db_info['filename']}")
                self.update_status_bar()
                
                QMessageBox.information(self, "Sukces", 
                    f"Załadowano ostatnią bazę danych:\n{self.db_path}")
                    
            except Exception as e:
                QMessageBox.critical(self, "Błąd", 
                    f"Nie udało się załadować bazy danych:\n{str(e)}")
        else:
            QMessageBox.warning(self, "Brak pliku", 
                f"Ostatnia baza danych nie istnieje:\n{db_info['path']}")

    def open_database(self):
        """Otwórz istniejącą bazę danych"""
        dialog = OpenDatabaseDialog(self)
        if dialog.exec():
            try:
                new_db_path = dialog.selected_path
                
                # Zamknij aktualną bazę
                if hasattr(self.db, 'conn'):
                    self.db.conn.close()
                
                # Zapisz nową ścieżkę w konfiguracji
                self.config.set_database_path(new_db_path)
                self.db_path = new_db_path
                
                # Otwórz nową bazę
                self.db = DB(self.db_path)
                
                # Odśwież interfejs
                self.refresh()
                
                # Zaktualizuj tytuł okna
                db_info = self.config.get_database_info()
                self.setWindowTitle(f"System Magazynowo-Sprzedażowy v{APP_VERSION} - {db_info['filename']}")
                
                # Zaktualizuj pasek statusu
                self.update_status_bar()
                
                QMessageBox.information(self, "Sukces", 
                    f"Załadowano bazę danych:\n{self.db_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Błąd", 
                    f"Nie udało się załadować bazy danych:\n{str(e)}")
                
                # Przywróć poprzednią bazę
                self.db_path = self.config.get_database_path()
                self.db = DB(self.db_path)
                self.refresh()

    def backup_database(self):
        """Utwórz kopię zapasową bazy danych"""
        dialog = BackupDialog(self.db_path, self)
        dialog.exec()

    def import_export(self):
        """Otwórz dialog importu/eksportu"""
        dialog = ImportExportDialog(self.db, self.config, self)
        dialog.exec()

    def print_dialog(self):
        """Otwórz dialog drukowania"""
        dialog = PrintDialog(self)
        dialog.exec()

    def show_report_dialog(self, report_type):
        """Pokazuje dialog raportu w zależności od typu"""
        dialog = ReportDialog(self.db, self.config, self, report_type)
        dialog.exec()

    def refresh(self):
        rows = self.db.list_products()
        data = []
        for r in rows:
            data.append([
                r["id"],
                r["sku"],
                r["title"],
                r["stock"],
                "" 
            ])
        
        current_column = self.table.current_sorted_column
        current_order = self.table.current_sort_order
        
        self.table.setRowCount(len(data))
        for i, row in enumerate(data):
            for j, value in enumerate(row[:4]):
                item = QTableWidgetItem(str(value))
                
                if j in [0, 3]:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    try:
                        item.setData(Qt.EditRole, float(value))
                    except ValueError:
                        pass
                
                self.table.setItem(i, j, item)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedWidth(30)
            delete_btn.setToolTip("Usuń produkt")
            delete_btn.clicked.connect(lambda checked, pid=row[0]: self.delete_single_product(pid))
            self.table.setCellWidget(i, 4, delete_btn)
        
        if current_column >= 0:
            self.table.sort_by_column(current_column, current_order)
            self.table.mark_sorted_column(current_column)
        
        self.status_bar.showMessage(f"Załadowano {len(data)} produktów | Baza: {os.path.basename(self.db_path)}")

    def add_product(self):
        dialog = AddProductDialog(self.db, self)
        if dialog.exec():
            self.refresh()

    def delete_product(self):
        products = self.db.list_products()
        if not products:
            QMessageBox.warning(self, "Brak produktów", "Brak produktów do usunięcia.")
            return
            
        items = [f"{p['id']} | {p['sku']} | {p['title']}" for p in products]
        product_str, ok = QInputDialog.getItem(self, "Usuń produkt", "Wybierz produkt:", items, 0, False)
        
        if ok and product_str:
            pid = int(product_str.split("|")[0].strip())
            self.confirm_delete_product(pid)

    def delete_single_product(self, pid):
        self.confirm_delete_product(pid)

    def confirm_delete_product(self, pid):
        product_info = self.db.get_product_info(pid)
        if not product_info:
            QMessageBox.warning(self, "Błąd", "Produkt nie istnieje.")
            return
            
        if QMessageBox.question(
            self, "Potwierdź usunięcie",
            f"Czy na pewno usunąć produkt?\n\n"
            f"SKU: {product_info['sku']}\n"
            f"Nazwa: {product_info['title']}\n"
            f"Stan: {product_info['stock']}",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            success = self.db.delete_product(pid)
            if success:
                self.refresh()
            else:
                QMessageBox.warning(self, "Błąd", 
                    "Nie można usunąć produktu z dodatnim stanem magazynowym!\n"
                    "Najpierw sprzedaj lub skoryguj stan produktu.")

    def add_purchase(self):
        d = PurchaseDialog(self.db)
        if d.exec():
            self.db.add_purchase_order(
                d.cost.value(),
                d.date.date().toString("yyyy-MM-dd"),
                d.get_items()
            )
            self.refresh()

    def add_sale(self):
        d = SaleDialog(self.db, self.config)
        if d.exec():
            self.refresh()

    def show_purchases(self):
        try:
            purchases = self.db.list_purchases()
            HistoryDialog(
                "Historia zakupów",
                ["ID", "SKU", "Nazwa", "Ilość", "PLN", "Data"],
                purchases,
                self.db.delete_purchase,
                self
            ).exec()
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie można załadować historii zakupów:\n{str(e)}")

    def show_sales(self):
        try:
            sales = self.db.list_sales()
            HistoryDialog(
                "Historia sprzedaży",
                ["ID", "Platforma", "PLN", "EUR", "Koszt zakupu", "Zysk", "Data", "Pozycje"],
                sales,
                self.db.delete_sale,
                self
            ).exec()
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie można załadować historii sprzedaży:\n{str(e)}")

    def show_invoices(self):
        dialog = InvoicesHistoryDialog(self.db, self.config, self)
        dialog.exec()

    def invoice_config(self):
        """Konfiguracja ustawień rachunków"""
        dialog = InvoiceConfigDialog(self.config, self)
        dialog.exec()

    def limits_config(self):
        """Konfiguracja limitów US"""
        dialog = LimitsConfigDialog(self.config, self)
        dialog.exec()

    def inventory(self):
        InventoryDialog(self.db, self).exec()
        self.refresh()

    def business_info(self):
        dialog = BusinessInfoDialog(self.config, self)
        dialog.exec()

    def about(self):
        """Wyświetla informacje o wersji programu"""
        try:
            from version import get_version
            version_info = get_version()
            
            about_text = f"""
            <h2>{version_info['app_name']}</h2>
            <p><b>Wersja:</b> {version_info['version']}</p>
            <p><b>Data budowy:</b> {version_info['build_date']}</p>
            <p><b>Autor:</b> {version_info['author']}</p>
            <p><b>Licencja:</b> {version_info['license']}</p>
            
            <h3>Funkcje w tej wersji:</h3>
            <ul>
                <li>Historia rachunków z możliwością usuwania</li>
                <li>Poprawione polskie znaki w PDF</li>
                <li>Inteligentne liczenie transakcji</li>
                <li>Pełna ewidencja dla US</li>
                <li>System FIFO dla kosztów zakupu</li>
                <li>Generowanie raportów Excel/CSV/PDF</li>
                <li>Konfiguracja wyglądu rachunków</li>
                <li>Resetowanie numeracji faktur</li>
                <li>Otwieranie różnych baz danych</li>
                <li>Archiwizacja i kopia zapasowa</li>
                <li>Import/Export danych</li>
                <li>Drukowanie dokumentów (również bezpośrednie z raportów)</li>
                <li><b>NOWE:</b> Limity kwartalne od 2026 roku</li>
                <li><b>NOWE:</b> Raporty kwartalne z automatycznymi obliczeniami</li>
                <li><b>NOWE:</b> Zapamiętywanie ostatnio używanej bazy danych</li>
            </ul>
            
            <h3>Licencja GNU GPL v3.0:</h3>
            <p>Wolne oprogramowanie - możesz używać, modyfikować i rozpowszechniać<br>
            zgodnie z warunkami licencji GNU General Public License wersja 3.</p>
            
            <p><i>Ostatnia aktualizacja: v{version_info['version']}</i></p>
            """
            
            msg = QMessageBox(self)
            msg.setWindowTitle("O programie")
            msg.setTextFormat(Qt.RichText)
            msg.setText(about_text)
            msg.setIcon(QMessageBox.Information)
            msg.exec()
            
        except ImportError:
            about_text = f"""
            <h2>System Magazynowo-Sprzedażowy</h2>
            <p><b>Wersja:</b> {APP_VERSION}</p>
            
            <h3>Funkcje:</h3>
            <ul>
                <li>Zarządzanie magazynem i produktami</li>
                <li>Ewidencja zakupów i sprzedaży</li>
                <li>Generowanie rachunków uproszczonych</li>
                <li>Raporty dla działalności nierejestrowanej</li>
                <li>Otwieranie różnych baz danych</li>
                <li>Archiwizacja i kopia zapasowa</li>
                <li>Import/Export danych</li>
                <li>Drukowanie dokumentów (również bezpośrednie z raportów)</li>
                <li><b>NOWE:</b> Limity kwartalne od 2026 roku</li>
                <li><b>NOWE:</b> Raporty kwartalne z automatycznymi obliczeniami</li>
                <li><b>NOWE:</b> Zapamiętywanie ostatnio używanej bazy danych</li>
            </ul>
            
            <p><i>Ostatnia aktualizacja: v{APP_VERSION}</i></p>
            """
            
            msg = QMessageBox(self)
            msg.setWindowTitle("O programie")
            msg.setTextFormat(Qt.RichText)
            msg.setText(about_text)
            msg.setIcon(QMessageBox.Information)
            msg.exec()
        except Exception as e:
            QMessageBox.information(self, "O programie", 
                                  f"System Magazynowo-Sprzedażowy\nWersja: {APP_VERSION}")

    def closeEvent(self, event):
        """Zapisz stan przed zamknięciem programu"""
        try:
            if hasattr(self.db, 'conn'):
                self.db.conn.close()
        except:
            pass
        
        event.accept()

# ================== START ==================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(RED_WHITE_QSS)
    
    # Sprawdź czy domyślna baza istnieje
    if not os.path.exists("data.db"):
        # Utwórz domyślną bazę
        from db import DB
        temp_db = DB("data.db")
        temp_db.conn.close()
    
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
