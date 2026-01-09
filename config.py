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
            }
        }
    
    def save(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def get_business_info(self):
        return self.data.get("business", {})
    
    def update_business_info(self, info):
        self.data["business"] = info
        self.save()
    
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
