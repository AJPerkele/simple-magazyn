import sys
import os
from datetime import datetime, timedelta
from PySide6.QtWidgets import *
from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtGui import QFont

from db import DB
from currency import get_eur_rate

PLATFORMS = ["Vinted", "OLX", "Allegro Lokalnie", "Inne"]

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
                # Tworzymy zakup z kosztem 0 PLN
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

# ================== DIALOG RAPORTU ==================
class ReportDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Generuj raport")
        self.resize(500, 400)

        v = QVBoxLayout(self)

        # Typ raportu
        gb_type = QGroupBox("Typ raportu")
        type_layout = QVBoxLayout()
        
        self.rb_monthly = QRadioButton("Miesięczny")
        self.rb_monthly.setChecked(True)
        self.rb_yearly = QRadioButton("Roczny")
        self.rb_custom = QRadioButton("Niestandardowy okres")
        
        type_layout.addWidget(self.rb_monthly)
        type_layout.addWidget(self.rb_yearly)
        type_layout.addWidget(self.rb_custom)
        gb_type.setLayout(type_layout)
        v.addWidget(gb_type)

        # Kontenery dla różnych typów raportów
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
        
        self.yearly_widget = QWidget()
        yearly_layout = QHBoxLayout(self.yearly_widget)
        self.year_only_spin = QSpinBox()
        self.year_only_spin.setRange(2000, 2100)
        self.year_only_spin.setValue(datetime.now().year)
        
        yearly_layout.addWidget(QLabel("Rok:"))
        yearly_layout.addWidget(self.year_only_spin)
        yearly_layout.addStretch()
        
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
        
        # Dodaj wszystkie widżety do głównego layoutu
        v.addWidget(self.monthly_widget)
        v.addWidget(self.yearly_widget)
        v.addWidget(self.custom_widget)
        
        # Pokazuj tylko aktualny typ raportu
        self.show_current_layout()
        self.rb_monthly.toggled.connect(self.show_current_layout)
        self.rb_yearly.toggled.connect(self.show_current_layout)
        self.rb_custom.toggled.connect(self.show_current_layout)

        # Format eksportu
        gb_format = QGroupBox("Format eksportu")
        format_layout = QHBoxLayout()
        
        self.rb_csv = QRadioButton("CSV")
        self.rb_csv.setChecked(True)
        self.rb_excel = QRadioButton("Excel (XLSX)")
        
        format_layout.addWidget(self.rb_csv)
        format_layout.addWidget(self.rb_excel)
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
        
        detail_layout.addWidget(self.cb_purchases)
        detail_layout.addWidget(self.cb_sales)
        detail_layout.addWidget(self.cb_summary)
        detail_layout.addWidget(self.cb_products)
        gb_detail.setLayout(detail_layout)
        v.addWidget(gb_detail)

        # Przyciski
        button_layout = QHBoxLayout()
        
        btn_generate = QPushButton("Generuj raport")
        btn_generate.clicked.connect(self.generate_report)
        btn_generate.setStyleSheet("background-color: #2E7D32; font-weight: bold;")
        
        btn_cancel = QPushButton("Anuluj")
        btn_cancel.clicked.connect(self.reject)
        
        button_layout.addWidget(btn_generate)
        button_layout.addWidget(btn_cancel)
        v.addLayout(button_layout)

    def show_current_layout(self):
        """Pokazuje tylko odpowiedni widżet dla wybranego typu raportu"""
        self.monthly_widget.setVisible(self.rb_monthly.isChecked())
        self.yearly_widget.setVisible(self.rb_yearly.isChecked())
        self.custom_widget.setVisible(self.rb_custom.isChecked())

    def get_date_range(self):
        """Zwraca zakres dat dla wybranego typu raportu"""
        try:
            if self.rb_monthly.isChecked():
                month = self.month_combo.currentIndex() + 1
                year = self.year_spin.value()
                date_from = f"{year}-{month:02d}-01"
                
                # Ostatni dzień miesiąca
                if month == 12:
                    date_to = f"{year}-12-31"
                else:
                    # Utwórz datę pierwszego dnia następnego miesiąca i odejmij 1 dzień
                    next_month = datetime(year, month + 1, 1)
                    last_day = next_month - timedelta(days=1)
                    date_to = last_day.strftime("%Y-%m-%d")
                    
            elif self.rb_yearly.isChecked():
                year = self.year_only_spin.value()
                date_from = f"{year}-01-01"
                date_to = f"{year}-12-31"
                
            else:  # custom
                date_from = self.date_from.date().toString("yyyy-MM-dd")
                date_to = self.date_to.date().toString("yyyy-MM-dd")
                
            return date_from, date_to
            
        except Exception as e:
            print(f"Błąd w get_date_range: {e}")
            # Domyślne wartości w przypadku błędu
            today = datetime.now()
            date_from = today.replace(day=1).strftime("%Y-%m-%d")
            if today.month == 12:
                date_to = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                date_to = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            return date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d")

    def generate_report(self):
        """Generuje raport"""
        try:
            date_from, date_to = self.get_date_range()
            
            if not self.cb_purchases.isChecked() and not self.cb_sales.isChecked():
                QMessageBox.warning(self, "Brak danych", "Wybierz przynajmniej jeden typ danych (zakupy lub sprzedaż).")
                return
            
            # Wybierz format
            if self.rb_csv.isChecked():
                file_filter = "CSV Files (*.csv)"
                default_ext = ".csv"
            else:
                file_filter = "Excel Files (*.xlsx)"
                default_ext = ".xlsx"
            
            # Sugerowana nazwa pliku
            if self.rb_monthly.isChecked():
                month_name = self.month_combo.currentText().lower()
                year = self.year_spin.value()
                suggested_name = f"raport_{month_name}_{year}{default_ext}"
            elif self.rb_yearly.isChecked():
                year = self.year_only_spin.value()
                suggested_name = f"raport_{year}{default_ext}"
            else:
                from_str = date_from.replace("-", "")
                to_str = date_to.replace("-", "")
                suggested_name = f"raport_{from_str}_do_{to_str}{default_ext}"
            
            # Zapisz plik
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
                            include_products=self.cb_products.isChecked()
                        )
                    else:
                        success = self.db.export_detailed_report_excel(
                            path, date_from, date_to,
                            include_purchases=self.cb_purchases.isChecked(),
                            include_sales=self.cb_sales.isChecked(),
                            include_summary=self.cb_summary.isChecked(),
                            include_products=self.cb_products.isChecked()
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

# ================== SORTOWANIE ==================
class SortableTableWidget(QTableWidget):
    """Rozszerzona tabela z sortowaniem po kliknięciu nagłówków"""
    def __init__(self, rows=0, columns=0, parent=None):
        super().__init__(rows, columns, parent)
        self.sort_order = {}
        self.current_sorted_column = -1
        self.current_sort_order = Qt.AscendingOrder
        
        # Połącz kliknięcie nagłówka z funkcją sortującą
        self.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        
    def on_header_clicked(self, column):
        """Obsługa kliknięcia w nagłówek kolumny"""
        if column in self.sort_order:
            # Zmień kolejność sortowania
            self.sort_order[column] = not self.sort_order[column]
        else:
            # Domyślnie sortuj rosnąco
            self.sort_order[column] = True
        
        sort_ascending = self.sort_order[column]
        
        # Zapamiętaj aktualnie sortowaną kolumnę
        self.current_sorted_column = column
        self.current_sort_order = Qt.AscendingOrder if sort_ascending else Qt.DescendingOrder
        
        # Posortuj tabelę z odpowiednim typem sortowania
        self.sort_by_column(column, self.current_sort_order)
        
        # Oznacz sortowaną kolumnę
        self.mark_sorted_column(column)
    
    def sort_by_column(self, column, order):
        """Sortuje tabelę z odpowiednim typem sortowania dla kolumny"""
        # Sortuj standardowo - Qt sam poradzi sobie z liczbami i tekstem
        self.sortItems(column, order)
    
    def mark_sorted_column(self, column):
        """Oznacza sortowaną kolumnę"""
        header = self.horizontalHeader()
        for i in range(header.count()):
            if i == column:
                # Dodaj strzałkę do nagłówka
                sort_text = " ↑" if self.sort_order.get(column, True) else " ↓"
                original_text = self.get_column_name(i)
                header.model().setHeaderData(i, Qt.Horizontal, original_text + sort_text)
                
                # Podświetl nagłówek
                header.setStyleSheet("""
                    QHeaderView::section {
                        background-color: #e0e0e0;
                        font-weight: bold;
                    }
                """)
            else:
                # Przywróć oryginalny tekst
                original_text = self.get_column_name(i)
                header.model().setHeaderData(i, Qt.Horizontal, original_text)
        
        # Jeśli nie ma sortowania, przywróć domyślny styl
        if column == -1:
            header.setStyleSheet("""
                QHeaderView::section {
                    background-color: #f2f2f2;
                    font-weight: normal;
                }
            """)
    
    def get_column_name(self, column):
        """Zwraca oryginalną nazwę kolumny"""
        # Pobierz aktualne nazwy nagłówków
        header = self.horizontalHeader()
        original_text = header.model().headerData(column, Qt.Horizontal)
        
        # Usuń strzałki sortowania jeśli są
        if original_text:
            for arrow in [" ↑", " ↓"]:
                if original_text.endswith(arrow):
                    return original_text[:-2]
            return original_text
        
        # Domyślne nazwy dla głównej tabeli
        names = ["ID", "SKU", "Nazwa", "Stan", ""]
        if column < len(names):
            return names[column]
        return f"Kolumna {column+1}"
    
    def load_data(self, data):
        """Ładuje dane do tabeli"""
        self.setRowCount(len(data))
        for i, row in enumerate(data):
            for j, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                
                # Ustaw wyrównanie dla kolumn numerycznych
                if j in [0, 3]:  # ID i Stan
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    # Dla sortowania numerycznego ustaw dane jako liczby
                    try:
                        item.setData(Qt.EditRole, float(value))
                    except ValueError:
                        pass
                
                self.setItem(i, j, item)
        
        # Zresetuj sortowanie
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

        # Panel przycisków
        button_panel = QHBoxLayout()
        
        self.select_all_checkbox = QCheckBox("Zaznacz wszystkie")
        self.select_all_checkbox.stateChanged.connect(self.toggle_select_all)
        button_panel.addWidget(self.select_all_checkbox)
        
        button_panel.addStretch()
        
        b_select_none = QPushButton("Odznacz wszystkie")
        b_select_none.clicked.connect(self.select_none)
        button_panel.addWidget(b_select_none)
        
        v.addLayout(button_panel)

        # Tabela z checkboxami
        self.table = SortableTableWidget()
        self.table.setColumnCount(len(headers) + 1)  # +1 dla checkboxa
        table_headers = ["✓"] + list(headers)  # Dodaj kolumnę na checkbox
        self.table.setHorizontalHeaderLabels(table_headers)
        
        # Ustaw rozmiary kolumn
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Checkbox
        for i in range(1, len(table_headers)):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
        
        v.addWidget(self.table)

        # Panel przycisków usuwania
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
            # Checkbox w pierwszej kolumnie
            checkbox = QCheckBox()
            checkbox.setChecked(False)
            self.table.setCellWidget(i, 0, checkbox)
            
            # Dane w pozostałych kolumnach
            for j, val in enumerate(r):
                item = QTableWidgetItem(str(val))
                
                # Ustaw wyrównanie dla kolumn numerycznych
                if j in [0, 3, 4]:  # ID, Ilość, PLN dla zakupów
                    if isinstance(val, (int, float)):
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        # Ustaw dane jako liczby dla poprawnego sortowania
                        try:
                            item.setData(Qt.EditRole, float(val))
                        except (ValueError, TypeError):
                            pass
                
                self.table.setItem(i, j + 1, item)  # +1 bo pierwsza kolumna to checkbox

    def toggle_select_all(self, state):
        """Zaznacza/odznacza wszystkie checkboxy"""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(state == Qt.Checked)

    def select_none(self):
        """Odznacza wszystkie checkboxy"""
        self.select_all_checkbox.setChecked(False)
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)

    def get_selected_ids(self):
        """Zwraca listę ID zaznaczonych wierszy"""
        selected_ids = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                # ID jest w kolumnie 1 (bo kolumna 0 to checkbox)
                id_item = self.table.item(row, 1)
                if id_item:
                    try:
                        selected_ids.append(int(id_item.text()))
                    except ValueError:
                        pass
        return selected_ids

    def delete_selected(self):
        """Usuwa wszystkie zaznaczone wpisy"""
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
        """Usuwa pojedynczy zaznaczony wpis"""
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

        # Użyj SortableTableWidget z odpowiednią liczbą wierszy i kolumn
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
        
        # Combo box z produktami
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

# ================== SPRZEDAŻ ==================
class SaleDialog(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setWindowTitle("Dodaj sprzedaż")
        v = QVBoxLayout(self)

        self.platform = QComboBox()
        self.platform.addItems(PLATFORMS)
        self.pln = QDoubleSpinBox()
        self.pln.setMaximum(1e9)
        self.pln.valueChanged.connect(self.update_fifo_cost)
        
        self.date = QDateEdit(QDate.currentDate())
        self.date.setCalendarPopup(True)

        # Koszt automatyczny z FIFO (tylko informacyjny, nie edytowalny)
        self.auto_cost_label = QLabel("Koszt zakupu (FIFO): 0.00 PLN")
        self.auto_cost_label.setStyleSheet("font-weight: bold; color: #c62828;")
        
        # Utwórz form layout
        form = QFormLayout()
        form.addRow("Platforma", self.platform)
        form.addRow("Cena PLN", self.pln)
        form.addRow("Data", self.date)
        form.addRow("", self.auto_cost_label)
        v.addLayout(form)

        # Tabela z pozycjami
        self.items = SortableTableWidget(0, 2)
        self.items.setHorizontalHeaderLabels(["Produkt", "Ilość"])
        v.addWidget(self.items)

        b_add = QPushButton("Dodaj pozycję")
        b_add.clicked.connect(self.add_item)
        v.addWidget(b_add)

        b_ok = QPushButton("Zapisz")
        b_ok.clicked.connect(self.save_sale)
        v.addWidget(b_ok)
        
        # Przechowuj obliczony koszt FIFO
        self.fifo_cost = 0.0

    def add_item(self):
        r = self.items.rowCount()
        self.items.insertRow(r)
        
        # Combo box z produktami
        combo = product_combo(self.db)
        combo.currentIndexChanged.connect(self.update_fifo_cost)
        self.items.setCellWidget(r, 0, combo)

        qty = QSpinBox()
        qty.setMinimum(1)
        qty.setMaximum(100000)
        qty.valueChanged.connect(self.update_fifo_cost)
        self.items.setCellWidget(r, 1, qty)
        
        # Opóźnione odświeżenie kosztu
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
        """Oblicza koszt zakupu w oparciu o FIFO dla wybranych pozycji"""
        try:
            total_cost = 0.0
            items = self.get_items()
            
            for pid, qty in items:
                # Pobierz dostępne partie FIFO dla tego produktu
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

    def save_sale(self):
        """Zapisuje sprzedaż z obliczonym kosztem FIFO"""
        items = self.get_items()
        if not items:
            QMessageBox.warning(self, "Brak pozycji", "Dodaj przynajmniej jedną pozycję do sprzedaży.")
            return
            
        # Sprawdź czy wszystkie produkty mają wystarczający stan
        for pid, qty in items:
            if not self.db.check_stock(pid, qty):
                product_info = self.db.get_product_info(pid)
                if product_info:
                    QMessageBox.warning(self, "Brak stanu", 
                        f"Brak wystarczającego stanu dla produktu:\n"
                        f"SKU: {product_info['sku']}\n"
                        f"Nazwa: {product_info['title']}\n"
                        f"Wymagane: {qty}, dostępne: {product_info['stock']}")
                else:
                    QMessageBox.warning(self, "Błąd", f"Produkt ID {pid} nie istnieje.")
                return
        
        # Oblicz koszt FIFO
        fifo_cost = self.update_fifo_cost()
        
        # Przelicz EUR
        date = self.date.date().toString("yyyy-MM-dd")
        try:
            eur_rate = get_eur_rate(date)
            eur = round(self.pln.value() / eur_rate, 2) if eur_rate else 0
        except:
            eur = 0
        
        # Dodaj sprzedaż
        try:
            self.db.add_sale_order_with_reset(
                self.platform.currentText(),
                self.pln.value(),
                eur,
                date,
                items,
                fifo_cost
            )
            
            QMessageBox.information(self, "Sukces", "Sprzedaż została dodana.")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie udało się dodać sprzedaży:\n{str(e)}")

# ================== MAIN ==================
class Main(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DB()
        self.setWindowTitle("Magazyn i sprzedaż")
        self.resize(1100, 600)

        v = QVBoxLayout(self)
        h = QHBoxLayout()

        buttons = [
            ("Dodaj produkt", self.add_product),
            ("Usuń produkt", self.delete_product),
            ("Dodaj zakup", self.add_purchase),
            ("Dodaj sprzedaż", self.add_sale),
            ("Historia zakupów", self.show_purchases),
            ("Historia sprzedaży", self.show_sales),
            ("Raport", self.report),
            ("Eksport raportu", self.export_report),
            ("Eksport CSV", self.export_csv),
            ("Debug", self.debug),
            ("Inwentaryzacja", self.inventory),
        ]

        for t, fn in buttons:
            b = QPushButton(t)
            b.clicked.connect(fn)
            h.addWidget(b)

        v.addLayout(h)

        # Użyj naszej sortowalnej tabeli
        self.table = SortableTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "SKU", "Nazwa", "Stan", ""])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Ustaw rozmiary kolumn
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        v.addWidget(self.table)

        self.refresh()

    def refresh(self):
        rows = self.db.list_products()
        data = []
        for r in rows:
            data.append([
                r["id"],
                r["sku"],
                r["title"],
                r["stock"],
                ""  # Miejsce na przycisk
            ])
        
        # Zapamiętaj aktualne sortowanie
        current_column = self.table.current_sorted_column
        current_order = self.table.current_sort_order
        
        self.table.setRowCount(len(data))
        for i, row in enumerate(data):
            for j, value in enumerate(row[:4]):  # Pierwsze 4 kolumny z danymi
                item = QTableWidgetItem(str(value))
                
                # Ustaw wyrównanie dla kolumn numerycznych
                if j in [0, 3]:  # ID i Stan
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    # Ustaw dane jako liczby dla poprawnego sortowania
                    try:
                        item.setData(Qt.EditRole, float(value))
                    except ValueError:
                        pass
                
                self.table.setItem(i, j, item)
            
            # Przycisk usuwania dla każdego wiersza
            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedWidth(30)
            delete_btn.setToolTip("Usuń produkt")
            delete_btn.clicked.connect(lambda checked, pid=row[0]: self.delete_single_product(pid))
            self.table.setCellWidget(i, 4, delete_btn)
        
        # Przywróć sortowanie jeśli było aktywne
        if current_column >= 0:
            self.table.sort_by_column(current_column, current_order)
            self.table.mark_sorted_column(current_column)

    def add_product(self):
        dialog = AddProductDialog(self.db, self)
        if dialog.exec():
            self.refresh()

    def delete_product(self):
        """Usuwa produkt przez wybór z listy"""
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
        """Usuwa konkretny produkt"""
        self.confirm_delete_product(pid)

    def confirm_delete_product(self, pid):
        """Potwierdza i usuwa produkt"""
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
        d = SaleDialog(self.db)
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

    def report(self):
        d1, ok = QInputDialog.getText(self, "Raport", "Od (YYYY-MM-DD)")
        if not ok:
            return
        d2, ok = QInputDialog.getText(self, "Raport", "Do (YYYY-MM-DD)")
        if not ok:
            return
        try:
            r = self.db.report(d1, d2)
            profit = (r['sales_pln'] or 0) - (r['all_costs'] or 0)
            profit_margin = profit / (r['sales_pln'] or 1) * 100 if r['sales_pln'] else 0
            
            QMessageBox.information(
                self, "Raport",
                f"Sprzedaż PLN: {r['sales_pln'] or 0:.2f}\n"
                f"Koszty zakupu: {r['purchase_costs'] or 0:.2f}\n"
                f"Wszystkie koszty: {r['all_costs'] or 0:.2f}\n"
                f"Zysk PLN: {profit:.2f}\n"
                f"Marża: {profit_margin:.1f}%"
            )
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie można wygenerować raportu:\n{str(e)}")

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Eksport CSV", "", "CSV (*.csv)")
        if path:
            self.db.export_sales_csv(path)

    def export_report(self):
        """Otwiera dialog do generowania szczegółowego raportu"""
        dialog = ReportDialog(self.db, self)
        dialog.exec()

    def debug(self):
        pid, ok = QInputDialog.getInt(self, "Debug", "ID produktu")
        if ok:
            info = self.db.debug_stock_changes(pid)
            QMessageBox.information(self, "Debug", str(info))

    def inventory(self):
        InventoryDialog(self.db, self).exec()
        self.refresh()

# ================== START ==================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(RED_WHITE_QSS)
    w = Main()
    w.show()
    sys.exit(app.exec())
