# config.py
import json
import os
from datetime import datetime

CONFIG_FILE = "config.json"

class Config:
    def __init__(self):
        self.data = self.load()
    
    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return self.default_config()
        return self.default_config()
    
    def default_config(self):
        return {
            "database": {
                "last_used_path": "data.db",  # Domyślna ścieżka bazy
                "last_opened": None
            },
            "business": {
                "name": "",
                "address": "",
                "postal_code": "",
                "city": "",
                "pesel": "",
                "nip": "",
                "regon": "",
                "company_name": "",
                "company_address": "",
                "phone": "",
                "email": ""
            },
            "invoice": {
                "next_number": 1,
                "prefix": "FS",
                "digits": 6,
                "footer_text": "Dziękujemy za zakupy!",
                "auto_open": True,
                "save_pdf": True,
                "include_logo": False
            },
            "limits": {
                "minimal_wage": 4242.00,
                "quarterly_limit_multiplier": 2.25,
                "use_quarterly_limits": True,
                "year_limits": {
                    "2024": {"minimal_wage": 4242.00, "monthly_limit": 3181.50, "quarterly_limit": 9544.50},
                    "2025": {"minimal_wage": 4242.00, "monthly_limit": 3181.50, "quarterly_limit": 9544.50},
                    "2026": {"minimal_wage": 4242.00, "monthly_limit": 3181.50, "quarterly_limit": 9544.50}
                }
            }
        }
    
    def save(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    # ========== METODY DLA BAZY DANYCH ==========
    
    def get_database_path(self):
        """Pobiera zapisaną ścieżkę do bazy danych"""
        if "database" not in self.data:
            self.data["database"] = {}
        
        path = self.data["database"].get("last_used_path", "data.db")
        
        # Jeśli plik nie istnieje, wróć do domyślnej
        if not os.path.exists(path):
            return "data.db"
        
        return path
    
    def set_database_path(self, path):
        """Ustawia ścieżkę do bazy danych"""
        if "database" not in self.data:
            self.data["database"] = {}
        
        # Normalizuj ścieżkę
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)
        
        self.data["database"]["last_used_path"] = path
        self.data["database"]["last_opened"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save()
    
    def get_database_info(self):
        """Pobiera informacje o bazie danych"""
        if "database" not in self.data:
            self.data["database"] = {}
        
        path = self.data["database"].get("last_used_path", "data.db")
        exists = os.path.exists(path)
        
        if exists:
            try:
                size = os.path.getsize(path)
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size/1024:.1f} KB"
                else:
                    size_str = f"{size/(1024*1024):.1f} MB"
            except:
                size_str = "nieznany"
        else:
            size_str = "brak pliku"
        
        return {
            "path": path,
            "filename": os.path.basename(path),
            "exists": exists,
            "size": size_str,
            "last_opened": self.data["database"].get("last_opened")
        }
    
    # ========== METODY DLA DANYCH OSOBOWYCH ==========
    
    def get_business_info(self):
        return self.data.get("business", {})
    
    def update_business_info(self, info):
        self.data["business"] = info
        self.save()
    
    # ========== METODY DLA RACHUNKÓW ==========
    
    def get_invoice_config(self):
        return self.data.get("invoice", {})
    
    def get_next_invoice_number(self):
        invoice_config = self.get_invoice_config()
        num = invoice_config.get("next_number", 1)
        prefix = invoice_config.get("prefix", "FS")
        digits = invoice_config.get("digits", 6)
        
        # Zwiększ numer dla następnej faktury
        self.data["invoice"]["next_number"] = num + 1
        self.save()
        
        # Formatuj numer z odpowiednią ilością zer
        return f"{prefix}/{num:0{digits}d}"
    
    def set_next_invoice_number(self, number):
        """Ustawia następny numer faktury"""
        if "invoice" not in self.data:
            self.data["invoice"] = {}
        self.data["invoice"]["next_number"] = number
        self.save()
    
    def get_invoice_footer(self):
        invoice_config = self.get_invoice_config()
        return invoice_config.get("footer_text", "Dziękujemy za zakupy!")
    
    def should_auto_open_invoice(self):
        invoice_config = self.get_invoice_config()
        return invoice_config.get("auto_open", True)
    
    def should_save_pdf(self):
        invoice_config = self.get_invoice_config()
        return invoice_config.get("save_pdf", True)
    
    def should_include_logo(self):
        invoice_config = self.get_invoice_config()
        return invoice_config.get("include_logo", False)
    
    # ========== METODY DLA LIMITÓW ==========
    
    def get_limits_config(self):
        """Pobiera konfigurację limitów"""
        return self.data.get("limits", {})
    
    def update_limits_config(self, limits_info):
        """Aktualizuje konfigurację limitów"""
        if "limits" not in self.data:
            self.data["limits"] = {}
        
        self.data["limits"].update(limits_info)
        self.save()
    
    def get_minimal_wage(self, year=None):
        """Pobiera minimalne wynagrodzenie dla danego roku"""
        limits = self.get_limits_config()
        
        if year:
            # Sprawdź czy mamy zapisany limit dla konkretnego roku
            year_limits = limits.get("year_limits", {})
            if str(year) in year_limits:
                return year_limits[str(year)].get("minimal_wage", limits.get("minimal_wage", 4242.00))
        
        return limits.get("minimal_wage", 4242.00)
    
    def get_quarterly_limit(self, year=None):
        """Oblicza limit kwartalny dla danego roku"""
        minimal_wage = self.get_minimal_wage(year)
        multiplier = self.get_limits_config().get("quarterly_limit_multiplier", 2.25)
        return minimal_wage * multiplier
    
    def get_monthly_limit(self, year=None):
        """Oblicza limit miesięczny dla danego roku"""
        minimal_wage = self.get_minimal_wage(year)
        return minimal_wage * 0.75  # 75% minimalnego wynagrodzenia
    
    def use_quarterly_limits(self):
        """Sprawdza czy używać limitów kwartalnych"""
        return self.get_limits_config().get("use_quarterly_limits", True)
    
    def set_use_quarterly_limits(self, use_quarterly):
        """Ustawia czy używać limitów kwartalnych"""
        if "limits" not in self.data:
            self.data["limits"] = {}
        
        self.data["limits"]["use_quarterly_limits"] = use_quarterly
        self.save()
    
    def get_year_limit_config(self, year):
        """Pobiera konfigurację limitów dla konkretnego roku"""
        limits = self.get_limits_config()
        year_limits = limits.get("year_limits", {})
        return year_limits.get(str(year), {})
    
    def update_year_limit_config(self, year, config):
        """Aktualizuje konfigurację limitów dla konkretnego roku"""
        if "limits" not in self.data:
            self.data["limits"] = {}
        
        if "year_limits" not in self.data["limits"]:
            self.data["limits"]["year_limits"] = {}
        
        self.data["limits"]["year_limits"][str(year)] = config
        self.save()
