import sqlite3
import csv
import os
from datetime import datetime, timedelta
from collections import defaultdict

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    HAS_EXCEL = True
except ImportError:
    HAS_EXCEL = False

class DB:
    def __init__(self, path="data.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        c = self.conn.cursor()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE,
            title TEXT,
            stock INTEGER DEFAULT 0
        );

        /* ===== ZAKUPY ===== */

        CREATE TABLE IF NOT EXISTS purchase_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_pln REAL,
            date TEXT
        );

        CREATE TABLE IF NOT EXISTS purchase_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            qty INTEGER,
            unit_cost REAL,
            available_qty INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS purchase_stock_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_item_id INTEGER,
            product_id INTEGER,
            qty INTEGER,
            date TEXT,
            sale_order_id INTEGER DEFAULT NULL
        );

        /* ===== SPRZEDAŻ ===== */

        CREATE TABLE IF NOT EXISTS sales_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            total_pln REAL,
            total_eur REAL,
            purchase_cost REAL DEFAULT 0,
            date TEXT
        );

        CREATE TABLE IF NOT EXISTS sales_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            qty INTEGER
        );
        """)
        
        # Dodaj brakujące kolumny
        try:
            c.execute("SELECT purchase_cost FROM sales_orders LIMIT 1")
        except sqlite3.OperationalError:
            c.execute("ALTER TABLE sales_orders ADD COLUMN purchase_cost REAL DEFAULT 0")
            
        try:
            c.execute("SELECT available_qty FROM purchase_items LIMIT 1")
        except sqlite3.OperationalError:
            c.execute("ALTER TABLE purchase_items ADD COLUMN available_qty INTEGER DEFAULT 0")
            
        try:
            c.execute("SELECT unit_cost FROM purchase_items LIMIT 1")
        except sqlite3.OperationalError:
            c.execute("ALTER TABLE purchase_items ADD COLUMN unit_cost REAL DEFAULT 0")
            
        c.execute("""
            CREATE TABLE IF NOT EXISTS purchase_stock_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_item_id INTEGER,
                product_id INTEGER,
                qty INTEGER,
                date TEXT,
                sale_order_id INTEGER DEFAULT NULL
            )
        """)
        
        self.conn.commit()

    # ---------- PRODUCTS ----------
    def add_product(self, sku, title):
        self.conn.execute(
            "INSERT INTO products(sku,title,stock) VALUES(?,?,0)",
            (sku, title)
        )
        self.conn.commit()

    def check_sku_exists(self, sku):
        """Sprawdza czy SKU już istnieje"""
        r = self.conn.execute("SELECT id FROM products WHERE sku=?", (sku,)).fetchone()
        return r is not None

    def get_product_id_by_sku(self, sku):
        """Zwraca ID produktu po SKU"""
        r = self.conn.execute("SELECT id FROM products WHERE sku=?", (sku,)).fetchone()
        return r["id"] if r else None

    def delete_product(self, pid):
        """Usuwa produkt i powiązane rekordy"""
        c = self.conn.cursor()
        
        product = self.get_product_info(pid)
        if product and product["stock"] > 0:
            return False
            
        c.execute("DELETE FROM purchase_items WHERE product_id=?", (pid,))
        c.execute("DELETE FROM sales_items WHERE product_id=?", (pid,))
        c.execute("DELETE FROM purchase_stock_history WHERE product_id=?", (pid,))
        c.execute("DELETE FROM products WHERE id=?", (pid,))
        
        self.conn.commit()
        return True

    def list_products(self):
        return self.conn.execute("SELECT * FROM products").fetchall()

    def update_stock(self, pid, delta):
        self.conn.execute(
            "UPDATE products SET stock = stock + ? WHERE id=?",
            (delta, pid)
        )
        self.conn.commit()

    # ---------- CHECK STOCK ----------
    def check_stock(self, pid: int, required_qty: int) -> bool:
        r = self.conn.execute("SELECT stock FROM products WHERE id=?", (pid,)).fetchone()
        if not r:
            return False
        return r["stock"] >= required_qty

    def get_product_info(self, pid: int):
        return self.conn.execute("SELECT sku, title, stock FROM products WHERE id=?", (pid,)).fetchone()

    # ---------- PURCHASES ----------
    def add_purchase_order(self, total_pln, date, items):
        c = self.conn.cursor()
        
        # Znajdź największe istniejące ID i pierwsze wolne
        max_id_result = c.execute("SELECT MAX(id) as max_id FROM purchase_orders").fetchone()
        max_id = max_id_result["max_id"] or 0
        
        # Znajdź pierwsze wolne ID (lukę)
        all_ids = [row[0] for row in c.execute("SELECT id FROM purchase_orders ORDER BY id").fetchall()]
        new_id = 1
        for existing_id in all_ids:
            if existing_id == new_id:
                new_id += 1
            else:
                break
        
        # Jeśli nie ma luk, użyj max_id + 1
        if new_id > max_id:
            new_id = max_id + 1
        
        # Wstaw z określonym ID
        c.execute(
            "INSERT INTO purchase_orders(id,total_pln,date) VALUES(?,?,?)",
            (new_id, total_pln, date)
        )
        oid = new_id

        total_qty = sum(qty for _, qty in items)
        
        for pid, qty in items:
            unit_cost = (total_pln / total_qty) if total_qty > 0 else 0
            
            # Znajdź ID dla purchase_items
            max_pi_id = c.execute("SELECT MAX(id) as max_id FROM purchase_items").fetchone()
            max_pi_id_val = max_pi_id["max_id"] or 0
            
            # Znajdź luki w ID dla purchase_items
            pi_ids = [row[0] for row in c.execute("SELECT id FROM purchase_items ORDER BY id").fetchall()]
            new_pi_id = 1
            for existing_id in pi_ids:
                if existing_id == new_pi_id:
                    new_pi_id += 1
                else:
                    break
            
            if new_pi_id > max_pi_id_val:
                new_pi_id = max_pi_id_val + 1
            
            c.execute("""
                INSERT INTO purchase_items(id,order_id,product_id,qty,unit_cost,available_qty)
                VALUES(?,?,?,?,?,?)
            """, (new_pi_id, oid, pid, qty, unit_cost, qty))
            
            purchase_item_id = new_pi_id
            
            # Znajdź ID dla purchase_stock_history
            max_psh_id = c.execute("SELECT MAX(id) as max_id FROM purchase_stock_history").fetchone()
            max_psh_id_val = max_psh_id["max_id"] or 0
            
            for i in range(qty):
                psh_ids = [row[0] for row in c.execute("SELECT id FROM purchase_stock_history ORDER BY id").fetchall()]
                new_psh_id = 1
                for existing_id in psh_ids:
                    if existing_id == new_psh_id:
                        new_psh_id += 1
                    else:
                        break
                
                if new_psh_id > max_psh_id_val:
                    new_psh_id = max_psh_id_val + 1
                    max_psh_id_val = new_psh_id
                
                c.execute("""
                    INSERT INTO purchase_stock_history(id,purchase_item_id,product_id,qty,date)
                    VALUES(?,?,?,?,?)
                """, (new_psh_id, purchase_item_id, pid, 1, date))
            
            product = self.conn.execute("SELECT id FROM products WHERE id=?", (pid,)).fetchone()
            if product:
                self.update_stock(pid, qty)

        self.conn.commit()
        return oid

    # ---------- HISTORIA ZAKUPÓW ----------
    def list_purchases(self):
        """Zwraca listę krotek dla historii zakupów"""
        try:
            rows = self.conn.execute("""
                SELECT
                    o.id,
                    pr.sku,
                    pr.title,
                    i.qty,
                    ROUND(o.total_pln / (
                        SELECT SUM(qty) 
                        FROM purchase_items 
                        WHERE order_id = o.id
                    ) * i.qty, 2) as item_cost,
                    o.date
                FROM purchase_orders o
                JOIN purchase_items i ON i.order_id = o.id
                JOIN products pr ON pr.id = i.product_id
                ORDER BY o.date DESC, o.id DESC
            """).fetchall()
            
            # Konwertuj do listy krotek
            result = []
            for r in rows:
                result.append((
                    r["id"],
                    r["sku"],
                    r["title"],
                    r["qty"],
                    r["item_cost"],
                    r["date"]
                ))
            return result
        except Exception as e:
            print(f"Błąd w list_purchases: {e}")
            return []

    def get_detailed_purchases(self, date_from, date_to):
        """Zwraca szczegółowe dane zakupów w danym okresie"""
        try:
            rows = self.conn.execute("""
                SELECT
                    o.id as order_id,
                    o.date,
                    pr.sku,
                    pr.title,
                    i.qty,
                    ROUND(o.total_pln / (
                        SELECT SUM(qty) 
                        FROM purchase_items 
                        WHERE order_id = o.id
                    ) * i.qty, 2) as item_cost,
                    i.unit_cost,
                    o.total_pln as order_total
                FROM purchase_orders o
                JOIN purchase_items i ON i.order_id = o.id
                JOIN products pr ON pr.id = i.product_id
                WHERE o.date BETWEEN ? AND ?
                ORDER BY o.date, o.id
            """, (date_from, date_to)).fetchall()
            
            result = []
            for r in rows:
                result.append({
                    'order_id': r['order_id'],
                    'date': r['date'],
                    'sku': r['sku'],
                    'title': r['title'],
                    'qty': r['qty'],
                    'item_cost': r['item_cost'],
                    'unit_cost': r['unit_cost'],
                    'order_total': r['order_total']
                })
            return result
        except Exception as e:
            print(f"Błąd w get_detailed_purchases: {e}")
            return []

    def delete_purchase(self, oid):
        """Usuwa zamówienie zakupu i odpowiednie ilości z magazynu"""
        try:
            c = self.conn.cursor()
            
            # Pobierz wszystkie pozycje z tego zamówienia
            rows = c.execute("""
                SELECT product_id, qty 
                FROM purchase_items 
                WHERE order_id=?
            """, (oid,)).fetchall()

            # Zmniejsz stan magazynowy dla każdego produktu
            for r in rows:
                self.update_stock(r["product_id"], -r["qty"])

            # Usuń z historii stanów magazynowych
            c.execute("""
                DELETE FROM purchase_stock_history 
                WHERE purchase_item_id IN (
                    SELECT id FROM purchase_items WHERE order_id=?
                )
            """, (oid,))
            
            # Usuń pozycje zamówienia
            c.execute("DELETE FROM purchase_items WHERE order_id=?", (oid,))
            
            # Usuń zamówienie
            c.execute("DELETE FROM purchase_orders WHERE id=?", (oid,))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Błąd w delete_purchase: {e}")
            return False

    # ---------- FIFO FUNCTIONS ----------
    def get_fifo_batches(self, pid: int, required_qty: int):
        try:
            # Sprawdź czy tabela istnieje
            c = self.conn.cursor()
            c.execute("SELECT 1 FROM purchase_stock_history LIMIT 1")
        except sqlite3.OperationalError:
            return []
        
        batches = self.conn.execute("""
            SELECT 
                pi.id as purchase_item_id,
                pi.unit_cost,
                pi.available_qty,
                po.date,
                COUNT(psh.id) as available_units
            FROM purchase_items pi
            JOIN purchase_orders po ON po.id = pi.order_id
            LEFT JOIN purchase_stock_history psh ON psh.purchase_item_id = pi.id 
                AND psh.product_id = pi.product_id 
                AND psh.sale_order_id IS NULL
            WHERE pi.product_id = ? AND pi.available_qty > 0
            GROUP BY pi.id
            HAVING available_units > 0
            ORDER BY po.date ASC, pi.id ASC
        """, (pid,)).fetchall()
        
        result = []
        remaining_qty = required_qty
        
        for batch in batches:
            if remaining_qty <= 0:
                break
                
            available = batch["available_units"]
            take_qty = min(available, remaining_qty)
            
            result.append({
                "purchase_item_id": batch["purchase_item_id"],
                "unit_cost": batch["unit_cost"],
                "available_qty": take_qty,
                "date": batch["date"]
            })
            
            remaining_qty -= take_qty
        
        return result

    def allocate_fifo_stock(self, pid: int, qty: int, sale_order_id: int):
        batches = self.get_fifo_batches(pid, qty)
        total_cost = 0.0
        
        for batch in batches:
            batch_qty = batch["available_qty"]
            unit_cost = batch["unit_cost"]
            
            self.conn.execute("""
                UPDATE purchase_stock_history 
                SET sale_order_id = ?
                WHERE purchase_item_id = ? 
                AND product_id = ?
                AND sale_order_id IS NULL
                LIMIT ?
            """, (sale_order_id, batch["purchase_item_id"], pid, batch_qty))
            
            self.conn.execute("""
                UPDATE purchase_items 
                SET available_qty = available_qty - ?
                WHERE id = ?
            """, (batch_qty, batch["purchase_item_id"]))
            
            total_cost += unit_cost * batch_qty
        
        self.conn.commit()
        return total_cost

    # ---------- SALES ----------
    def add_sale_order_with_reset(self, platform, total_pln, total_eur, date, items, purchase_cost=0):
        """Dodaje zamówienie sprzedaży z resetowanym ID"""
        c = self.conn.cursor()
        
        # Znajdź największe istniejące ID i pierwsze wolne
        max_id_result = c.execute("SELECT MAX(id) as max_id FROM sales_orders").fetchone()
        max_id = max_id_result["max_id"] or 0
        
        # Znajdź wszystkie istniejące ID
        all_ids = [row[0] for row in c.execute("SELECT id FROM sales_orders ORDER BY id").fetchall()]
        
        # Znajdź pierwsze wolne ID (lukę)
        new_id = 1
        for existing_id in all_ids:
            if existing_id == new_id:
                new_id += 1
            else:
                break
        
        # Jeśli nie ma luk, użyj max_id + 1
        if new_id > max_id:
            new_id = max_id + 1
        
        # Wstaw z określonym ID
        c.execute("""
            INSERT INTO sales_orders(id,platform,total_pln,total_eur,purchase_cost,date)
            VALUES(?,?,?,?,?,?)
        """, (new_id, platform, total_pln, total_eur, purchase_cost, date))
        sale_order_id = new_id

        total_purchase_cost = 0
        
        for pid, qty in items:
            # Znajdź ID dla sales_items
            max_si_id = c.execute("SELECT MAX(id) as max_id FROM sales_items").fetchone()
            max_si_id_val = max_si_id["max_id"] or 0
            
            # Znajdź luki w ID dla sales_items
            si_ids = [row[0] for row in c.execute("SELECT id FROM sales_items ORDER BY id").fetchall()]
            new_si_id = 1
            for existing_id in si_ids:
                if existing_id == new_si_id:
                    new_si_id += 1
                else:
                    break
            
            if new_si_id > max_si_id_val:
                new_si_id = max_si_id_val + 1
            
            c.execute("""
                INSERT INTO sales_items(id,order_id,product_id,qty)
                VALUES(?,?,?,?)
            """, (new_si_id, sale_order_id, pid, qty))
            
            # Spróbuj alokować stan FIFO
            try:
                item_cost = self.allocate_fifo_stock(pid, qty, sale_order_id)
                total_purchase_cost += item_cost
            except Exception as e:
                print(f"Błąd alokacji FIFO: {e}")
                total_purchase_cost += 0
            
            self.update_stock(pid, -qty)

        # Aktualizuj całkowity koszt zakupu
        if total_purchase_cost > 0:
            c.execute("""
                UPDATE sales_orders 
                SET purchase_cost = ?
                WHERE id = ?
            """, (total_purchase_cost, sale_order_id))

        self.conn.commit()
        return sale_order_id

    def add_sale_order(self, platform, total_pln, total_eur, date, items, purchase_cost=0):
        """Dodaje zamówienie sprzedaży z autoincrement (dla kompatybilności)"""
        return self.add_sale_order_with_reset(platform, total_pln, total_eur, date, items, purchase_cost)

    # ---------- HISTORIA SPRZEDAŻY ----------
    def list_sales(self):
        """Zwraca listę krotek dla historii sprzedaży"""
        try:
            rows = self.conn.execute("""
                SELECT
                    o.id,
                    o.platform,
                    o.total_pln,
                    o.total_eur,
                    o.purchase_cost,
                    o.date,
                    GROUP_CONCAT(pr.sku || ' x' || si.qty, ', ') as items
                FROM sales_orders o
                LEFT JOIN sales_items si ON si.order_id = o.id
                LEFT JOIN products pr ON pr.id = si.product_id
                GROUP BY o.id, o.platform, o.total_pln, o.total_eur, o.purchase_cost, o.date
                ORDER BY o.date DESC, o.id DESC
            """).fetchall()
        except sqlite3.OperationalError as e:
            # Jeśli kolumna purchase_cost nie istnieje
            rows = self.conn.execute("""
                SELECT
                    o.id,
                    o.platform,
                    o.total_pln,
                    o.total_eur,
                    0 as purchase_cost,
                    o.date,
                    GROUP_CONCAT(pr.sku || ' x' || si.qty, ', ') as items
                FROM sales_orders o
                LEFT JOIN sales_items si ON si.order_id = o.id
                LEFT JOIN products pr ON pr.id = si.product_id
                GROUP BY o.id, o.platform, o.total_pln, o.total_eur, o.date
                ORDER BY o.date DESC, o.id DESC
            """).fetchall()
        
        # Konwertuj do listy krotek
        result = []
        for r in rows:
            profit = r["total_pln"] - (r["purchase_cost"] or 0)
            result.append((
                r["id"],
                r["platform"],
                round(r["total_pln"], 2),
                round(r["total_eur"], 2),
                round(r["purchase_cost"] or 0, 2),
                round(profit, 2),
                r["date"],
                r["items"] or ""
            ))
        return result

    def get_detailed_sales(self, date_from, date_to):
        """Zwraca szczegółowe dane sprzedaży w danym okresie"""
        try:
            rows = self.conn.execute("""
                SELECT
                    o.id as order_id,
                    o.platform,
                    o.date,
                    pr.sku,
                    pr.title,
                    si.qty,
                    ROUND(o.total_pln / (
                        SELECT SUM(qty) 
                        FROM sales_items 
                        WHERE order_id = o.id
                    ) * si.qty, 2) as item_revenue_pln,
                    ROUND(o.total_eur / (
                        SELECT SUM(qty) 
                        FROM sales_items 
                        WHERE order_id = o.id
                    ) * si.qty, 2) as item_revenue_eur,
                    ROUND(o.purchase_cost / (
                        SELECT SUM(qty) 
                        FROM sales_items 
                        WHERE order_id = o.id
                    ) * si.qty, 2) as item_cost,
                    o.total_pln as order_total_pln,
                    o.total_eur as order_total_eur,
                    o.purchase_cost as order_total_cost
                FROM sales_orders o
                JOIN sales_items si ON si.order_id = o.id
                JOIN products pr ON pr.id = si.product_id
                WHERE o.date BETWEEN ? AND ?
                ORDER BY o.date, o.id
            """, (date_from, date_to)).fetchall()
            
            result = []
            for r in rows:
                item_profit = r['item_revenue_pln'] - r['item_cost']
                result.append({
                    'order_id': r['order_id'],
                    'platform': r['platform'],
                    'date': r['date'],
                    'sku': r['sku'],
                    'title': r['title'],
                    'qty': r['qty'],
                    'item_revenue_pln': r['item_revenue_pln'],
                    'item_revenue_eur': r['item_revenue_eur'],
                    'item_cost': r['item_cost'],
                    'item_profit': item_profit,
                    'order_total_pln': r['order_total_pln'],
                    'order_total_eur': r['order_total_eur'],
                    'order_total_cost': r['order_total_cost']
                })
            return result
        except Exception as e:
            print(f"Błąd w get_detailed_sales: {e}")
            return []

    def delete_sale(self, oid):
        """Usuwa zamówienie sprzedaży i przywraca stan magazynowy"""
        try:
            c = self.conn.cursor()
            
            # Spróbuj przywrócić stan z historii FIFO
            try:
                purchase_items = c.execute("""
                    SELECT psh.purchase_item_id, psh.product_id
                    FROM purchase_stock_history psh
                    WHERE psh.sale_order_id = ?
                """, (oid,)).fetchall()
                
                for item in purchase_items:
                    c.execute("""
                        UPDATE purchase_items 
                        SET available_qty = available_qty + 1
                        WHERE id = ?
                    """, (item["purchase_item_id"],))
                
                c.execute("""
                    UPDATE purchase_stock_history 
                    SET sale_order_id = NULL 
                    WHERE sale_order_id = ?
                """, (oid,))
            except:
                pass
            
            # Przywróć stan produktów
            rows = c.execute("""
                SELECT product_id, qty FROM sales_items WHERE order_id=?
            """, (oid,)).fetchall()

            for r in rows:
                self.update_stock(r["product_id"], r["qty"])

            # Usuń pozycje sprzedaży
            c.execute("DELETE FROM sales_items WHERE order_id=?", (oid,))
            
            # Usuń zamówienie sprzedaży
            c.execute("DELETE FROM sales_orders WHERE id=?", (oid,))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Błąd w delete_sale: {e}")
            return False

    # ---------- REPORT ----------
    def report(self, d1, d2):
        try:
            return self.conn.execute("""
                SELECT
                    SUM(o.total_pln) AS sales_pln,
                    SUM(o.total_eur) AS sales_eur,
                    SUM(o.purchase_cost) AS purchase_costs,
                    (
                        SELECT SUM(po.total_pln)
                        FROM purchase_orders po
                        WHERE po.date BETWEEN ? AND ?
                    ) AS all_costs
                FROM sales_orders o
                WHERE o.date BETWEEN ? AND ?
            """, (d1, d2, d1, d2)).fetchone()
        except sqlite3.OperationalError:
            return self.conn.execute("""
                SELECT
                    SUM(o.total_pln) AS sales_pln,
                    SUM(o.total_eur) AS sales_eur,
                    0 AS purchase_costs,
                    (
                        SELECT SUM(po.total_pln)
                        FROM purchase_orders po
                        WHERE po.date BETWEEN ? AND ?
                    ) AS all_costs
                FROM sales_orders o
                WHERE o.date BETWEEN ? AND ?
            """, (d1, d2, d1, d2)).fetchone()

    # ---------- CSV ----------
    def export_sales_csv(self, path):
        rows = self.list_sales()
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["ID", "Platforma", "PLN", "EUR", "Koszt zakupu", "Zysk", "Data", "Pozycje"])
            for r in rows:
                w.writerow(r)

    # ---------- SZCZEGÓŁOWY RAPORT CSV ----------
    def export_detailed_report_csv(self, path, date_from, date_to, 
                                 include_purchases=True, include_sales=True,
                                 include_summary=True, include_products=False):
        """Eksportuje szczegółowy raport do CSV"""
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, delimiter=";")
                
                # Nagłówek raportu
                w.writerow([f"RAPORT OKRESOWY: {date_from} - {date_to}"])
                w.writerow([f"Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
                w.writerow([])
                
                # Podsumowanie finansowe
                if include_summary:
                    summary = self.report(date_from, date_to)
                    if summary:
                        w.writerow(["PODSUMOWANIE FINANSOWE"])
                        w.writerow(["Sprzedaż PLN:", f"{summary['sales_pln'] or 0:.2f}"])
                        w.writerow(["Sprzedaż EUR:", f"{summary['sales_eur'] or 0:.2f}"])
                        w.writerow(["Koszty zakupu:", f"{summary['purchase_costs'] or 0:.2f}"])
                        w.writerow(["Wszystkie koszty:", f"{summary['all_costs'] or 0:.2f}"])
                        profit = (summary['sales_pln'] or 0) - (summary['all_costs'] or 0)
                        w.writerow(["Zysk:", f"{profit:.2f}"])
                        w.writerow([])
                
                # Zakupy
                if include_purchases:
                    purchases = self.get_detailed_purchases(date_from, date_to)
                    if purchases:
                        w.writerow(["ZAKUPY"])
                        w.writerow(["ID zamówienia", "Data", "SKU", "Nazwa produktu", "Ilość", 
                                   "Koszt jednostkowy", "Wartość pozycji", "Wartość zamówienia"])
                        total_purchase_value = 0
                        current_order = None
                        order_total = 0
                        
                        for p in purchases:
                            if p['order_id'] != current_order:
                                if current_order is not None:
                                    w.writerow(["", "", "", "", "", "", f"SUMA ZAMÓWIENIA:", f"{order_total:.2f}"])
                                    w.writerow([])
                                current_order = p['order_id']
                                order_total = 0
                            
                            w.writerow([
                                p['order_id'], p['date'], p['sku'], p['title'], 
                                p['qty'], f"{p['unit_cost']:.2f}", 
                                f"{p['item_cost']:.2f}", f"{p['order_total']:.2f}"
                            ])
                            total_purchase_value += p['item_cost']
                            order_total += p['item_cost']
                        
                        if current_order is not None:
                            w.writerow(["", "", "", "", "", "", f"SUMA ZAMÓWIENIA:", f"{order_total:.2f}"])
                        
                        w.writerow(["", "", "", "", "", "", f"ŁĄCZNA WARTOŚĆ ZAKUPÓW:", f"{total_purchase_value:.2f}"])
                        w.writerow([])
                
                # Sprzedaż - POPRAWIONE: zysk = przychód - koszt
                if include_sales:
                    sales = self.get_detailed_sales(date_from, date_to)
                    if sales:
                        w.writerow(["SPRZEDAŻ"])
                        w.writerow(["ID zamówienia", "Platforma", "Data", "SKU", "Nazwa produktu", 
                                   "Ilość", "Przychód PLN", "Przychód EUR", "Koszt zakupu", 
                                   "Zysk", "Wartość zamówienia PLN", "Wartość zamówienia EUR"])
                        
                        total_revenue_pln = 0
                        total_revenue_eur = 0
                        total_cost = 0
                        total_profit = 0
                        current_order = None
                        order_total_pln = 0
                        order_total_eur = 0
                        
                        for s in sales:
                            if s['order_id'] != current_order:
                                if current_order is not None:
                                    w.writerow(["", "", "", "", "", "", "", "", "", 
                                               f"SUMA ZAMÓWIENIA:", f"{order_total_pln:.2f}", f"{order_total_eur:.2f}"])
                                    w.writerow([])
                                current_order = s['order_id']
                                order_total_pln = 0
                                order_total_eur = 0
                            
                            w.writerow([
                                s['order_id'], s['platform'], s['date'], s['sku'], s['title'], 
                                s['qty'], f"{s['item_revenue_pln']:.2f}", f"{s['item_revenue_eur']:.2f}", 
                                f"{s['item_cost']:.2f}", f"{s['item_profit']:.2f}",  # Zysk już obliczony w query
                                f"{s['order_total_pln']:.2f}", f"{s['order_total_eur']:.2f}"
                            ])
                            
                            total_revenue_pln += s['item_revenue_pln']
                            total_revenue_eur += s['item_revenue_eur']
                            total_cost += s['item_cost']
                            total_profit += s['item_profit']
                            order_total_pln += s['item_revenue_pln']
                            order_total_eur += s['item_revenue_eur']
                        
                        if current_order is not None:
                            w.writerow(["", "", "", "", "", "", "", "", "", 
                                       f"SUMA ZAMÓWIENIA:", f"{order_total_pln:.2f}", f"{order_total_eur:.2f}"])
                        
                        w.writerow(["", "", "", "", "", "", 
                                   f"ŁĄCZNY PRZYCHÓD PLN:", f"{total_revenue_pln:.2f}", 
                                   f"ŁĄCZNY KOSZT:", f"{total_cost:.2f}", 
                                   f"ŁĄCZNY ZYSK:", f"{total_profit:.2f}"])
                        w.writerow([])
                
                # Lista produktów
                if include_products:
                    products = self.list_products()
                    if products:
                        w.writerow(["STAN MAGAZYNOWY"])
                        w.writerow(["ID", "SKU", "Nazwa produktu", "Stan"])
                        for p in products:
                            w.writerow([p['id'], p['sku'], p['title'], p['stock']])
                
            return True
        except Exception as e:
            print(f"Błąd w export_detailed_report_csv: {e}")
            return False

    # ---------- SZCZEGÓŁOWY RAPORT EXCEL ----------
    def export_detailed_report_excel(self, path, date_from, date_to,
                                   include_purchases=True, include_sales=True,
                                   include_summary=True, include_products=False):
        """Eksportuje szczegółowy raport do Excel (XLSX)"""
        if not HAS_EXCEL:
            raise ImportError("Biblioteka openpyxl nie jest zainstalowana. Użyj: pip install openpyxl")
        
        try:
            wb = openpyxl.Workbook()
            
            # Stylowanie
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="2E7D32", end_color="2E7D32", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")
            
            money_format = '#,##0.00'
            date_format = 'YYYY-MM-DD'
            
            # Strona główna - informacje
            ws = wb.active
            ws.title = "Informacje"
            
            ws['A1'] = f"RAPORT OKRESOWY"
            ws['A1'].font = Font(bold=True, size=14)
            ws['A2'] = f"Okres: {date_from} - {date_to}"
            ws['A3'] = f"Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Podsumowanie finansowe
            if include_summary:
                ws['A5'] = "PODSUMOWANIE FINANSOWE"
                ws['A5'].font = Font(bold=True)
                
                summary = self.report(date_from, date_to)
                if summary:
                    data = [
                        ["Sprzedaż PLN:", f"{summary['sales_pln'] or 0:.2f}"],
                        ["Sprzedaż EUR:", f"{summary['sales_eur'] or 0:.2f}"],
                        ["Koszty zakupu:", f"{summary['purchase_costs'] or 0:.2f}"],
                        ["Wszystkie koszty:", f"{summary['all_costs'] or 0:.2f}"]
                    ]
                    
                    profit = (summary['sales_pln'] or 0) - (summary['all_costs'] or 0)
                    data.append(["Zysk:", f"{profit:.2f}"])
                    
                    for i, (label, value) in enumerate(data, start=6):
                        ws[f'A{i}'] = label
                        ws[f'B{i}'] = float(value.split()[0])
                        ws[f'B{i}'].number_format = money_format
                        ws[f'B{i}'].font = Font(bold=True) if "Zysk" in label else Font()
                
                ws.column_dimensions['A'].width = 25
                ws.column_dimensions['B'].width = 15
            
            # Zakupy
            if include_purchases:
                ws_purchases = wb.create_sheet("Zakupy")
                purchases = self.get_detailed_purchases(date_from, date_to)
                
                if purchases:
                    headers = ["ID zamówienia", "Data", "SKU", "Nazwa produktu", 
                              "Ilość", "Koszt jednostkowy", "Wartość pozycji", "Wartość zamówienia"]
                    
                    for col, header in enumerate(headers, start=1):
                        cell = ws_purchases.cell(row=1, column=col, value=header)
                        cell.font = header_font
                        cell.fill = header_fill
                        cell.alignment = header_alignment
                    
                    row = 2
                    total_purchase_value = 0
                    current_order = None
                    order_total = 0
                    
                    for p in purchases:
                        if p['order_id'] != current_order:
                            if current_order is not None:
                                # Dodaj sumę zamówienia
                                ws_purchases.cell(row=row, column=6, value="SUMA ZAMÓWIENIA:").font = Font(bold=True)
                                ws_purchases.cell(row=row, column=7, value=order_total).number_format = money_format
                                ws_purchases.cell(row=row, column=7).font = Font(bold=True)
                                row += 2
                            
                            current_order = p['order_id']
                            order_total = 0
                        
                        ws_purchases.cell(row=row, column=1, value=p['order_id'])
                        ws_purchases.cell(row=row, column=2, value=p['date'])
                        ws_purchases.cell(row=row, column=3, value=p['sku'])
                        ws_purchases.cell(row=row, column=4, value=p['title'])
                        ws_purchases.cell(row=row, column=5, value=p['qty'])
                        ws_purchases.cell(row=row, column=6, value=float(p['unit_cost'])).number_format = money_format
                        ws_purchases.cell(row=row, column=7, value=float(p['item_cost'])).number_format = money_format
                        ws_purchases.cell(row=row, column=8, value=float(p['order_total'])).number_format = money_format
                        
                        total_purchase_value += p['item_cost']
                        order_total += p['item_cost']
                        row += 1
                    
                    if current_order is not None:
                        ws_purchases.cell(row=row, column=6, value="SUMA ZAMÓWIENIA:").font = Font(bold=True)
                        ws_purchases.cell(row=row, column=7, value=order_total).number_format = money_format
                        ws_purchases.cell(row=row, column=7).font = Font(bold=True)
                        row += 2
                    
                    # Łączna wartość zakupów
                    ws_purchases.cell(row=row, column=6, value="ŁĄCZNA WARTOŚĆ ZAKUPÓW:").font = Font(bold=True)
                    ws_purchases.cell(row=row, column=7, value=total_purchase_value).number_format = money_format
                    ws_purchases.cell(row=row, column=7).font = Font(bold=True, color="FF0000")
                    
                    # Ustaw szerokości kolumn
                    for col in range(1, 9):
                        ws_purchases.column_dimensions[get_column_letter(col)].width = 15
            
            # Sprzedaż - POPRAWIONE: zysk = przychód - koszt
            if include_sales:
                ws_sales = wb.create_sheet("Sprzedaż")
                sales = self.get_detailed_sales(date_from, date_to)
                
                if sales:
                    headers = ["ID zamówienia", "Platforma", "Data", "SKU", "Nazwa produktu", 
                              "Ilość", "Przychód PLN", "Przychód EUR", "Koszt zakupu", "Zysk",
                              "Wartość zamówienia PLN", "Wartość zamówienia EUR"]
                    
                    for col, header in enumerate(headers, start=1):
                        cell = ws_sales.cell(row=1, column=col, value=header)
                        cell.font = header_font
                        cell.fill = PatternFill(start_color="1565C0", end_color="1565C0", fill_type="solid")
                        cell.alignment = header_alignment
                    
                    row = 2
                    total_revenue_pln = 0
                    total_revenue_eur = 0
                    total_cost = 0
                    total_profit = 0
                    current_order = None
                    order_total_pln = 0
                    order_total_eur = 0
                    
                    for s in sales:
                        if s['order_id'] != current_order:
                            if current_order is not None:
                                # Dodaj sumę zamówienia
                                ws_sales.cell(row=row, column=9, value="SUMA ZAMÓWIENIA:").font = Font(bold=True)
                                ws_sales.cell(row=row, column=10, value=order_total_pln).number_format = money_format
                                ws_sales.cell(row=row, column=10).font = Font(bold=True)
                                ws_sales.cell(row=row, column=11, value=order_total_eur).number_format = money_format
                                ws_sales.cell(row=row, column=11).font = Font(bold=True)
                                row += 2
                            
                            current_order = s['order_id']
                            order_total_pln = 0
                            order_total_eur = 0
                        
                        ws_sales.cell(row=row, column=1, value=s['order_id'])
                        ws_sales.cell(row=row, column=2, value=s['platform'])
                        ws_sales.cell(row=row, column=3, value=s['date'])
                        ws_sales.cell(row=row, column=4, value=s['sku'])
                        ws_sales.cell(row=row, column=5, value=s['title'])
                        ws_sales.cell(row=row, column=6, value=s['qty'])
                        ws_sales.cell(row=row, column=7, value=float(s['item_revenue_pln'])).number_format = money_format
                        ws_sales.cell(row=row, column=8, value=float(s['item_revenue_eur'])).number_format = money_format
                        ws_sales.cell(row=row, column=9, value=float(s['item_cost'])).number_format = money_format
                        ws_sales.cell(row=row, column=10, value=float(s['item_profit'])).number_format = money_format  # Zysk
                        ws_sales.cell(row=row, column=11, value=float(s['order_total_pln'])).number_format = money_format
                        ws_sales.cell(row=row, column=12, value=float(s['order_total_eur'])).number_format = money_format
                        
                        total_revenue_pln += s['item_revenue_pln']
                        total_revenue_eur += s['item_revenue_eur']
                        total_cost += s['item_cost']
                        total_profit += s['item_profit']
                        order_total_pln += s['item_revenue_pln']
                        order_total_eur += s['item_revenue_eur']
                        row += 1
                    
                    if current_order is not None:
                        ws_sales.cell(row=row, column=9, value="SUMA ZAMÓWIENIA:").font = Font(bold=True)
                        ws_sales.cell(row=row, column=10, value=order_total_pln).number_format = money_format
                        ws_sales.cell(row=row, column=10).font = Font(bold=True)
                        ws_sales.cell(row=row, column=11, value=order_total_eur).number_format = money_format
                        ws_sales.cell(row=row, column=11).font = Font(bold=True)
                        row += 2
                    
                    # Podsumowanie
                    ws_sales.cell(row=row, column=6, value="ŁĄCZNY PRZYCHÓD PLN:").font = Font(bold=True)
                    ws_sales.cell(row=row, column=7, value=total_revenue_pln).number_format = money_format
                    ws_sales.cell(row=row, column=7).font = Font(bold=True, color="2E7D32")
                    
                    ws_sales.cell(row=row, column=8, value="ŁĄCZNY PRZYCHÓD EUR:").font = Font(bold=True)
                    ws_sales.cell(row=row, column=9, value=total_revenue_eur).number_format = money_format
                    ws_sales.cell(row=row, column=9).font = Font(bold=True, color="2E7D32")
                    
                    ws_sales.cell(row=row+1, column=6, value="ŁĄCZNY KOSZT:").font = Font(bold=True)
                    ws_sales.cell(row=row+1, column=7, value=total_cost).number_format = money_format
                    ws_sales.cell(row=row+1, column=7).font = Font(bold=True, color="D32F2F")
                    
                    ws_sales.cell(row=row+1, column=8, value="ŁĄCZNY ZYSK:").font = Font(bold=True)
                    ws_sales.cell(row=row+1, column=9, value=total_profit).number_format = money_format
                    ws_sales.cell(row=row+1, column=9).font = Font(bold=True, color="2E7D32")
                    
                    # Ustaw szerokości kolumn
                    for col in range(1, 13):
                        ws_sales.column_dimensions[get_column_letter(col)].width = 15
            
            # Lista produktów
            if include_products:
                ws_products = wb.create_sheet("Magazyn")
                products = self.list_products()
                
                if products:
                    headers = ["ID", "SKU", "Nazwa produktu", "Stan"]
                    
                    for col, header in enumerate(headers, start=1):
                        cell = ws_products.cell(row=1, column=col, value=header)
                        cell.font = header_font
                        cell.fill = PatternFill(start_color="6A1B9A", end_color="6A1B9A", fill_type="solid")
                        cell.alignment = header_alignment
                    
                    row = 2
                    for p in products:
                        ws_products.cell(row=row, column=1, value=p['id'])
                        ws_products.cell(row=row, column=2, value=p['sku'])
                        ws_products.cell(row=row, column=3, value=p['title'])
                        ws_products.cell(row=row, column=4, value=p['stock'])
                        row += 1
                    
                    # Ustaw szerokości kolumn
                    ws_products.column_dimensions['A'].width = 10
                    ws_products.column_dimensions['B'].width = 15
                    ws_products.column_dimensions['C'].width = 30
                    ws_products.column_dimensions['D'].width = 10
            
            # Zapisz plik
            wb.save(path)
            return True
            
        except Exception as e:
            print(f"Błąd w export_detailed_report_excel: {e}")
            return False

    # ---------- DEBUG ----------
    def debug_stock_changes(self, pid: int):
        current = self.conn.execute("SELECT stock FROM products WHERE id=?", (pid,)).fetchone()
        
        purchases = self.conn.execute("""
            SELECT pi.qty, pi.unit_cost, po.date, pi.available_qty
            FROM purchase_items pi
            JOIN purchase_orders po ON po.id = pi.order_id
            WHERE pi.product_id=?
            ORDER BY po.date
        """, (pid,)).fetchall()
        
        return {
            "current_stock": current["stock"] if current else 0,
            "purchases": purchases,
        }
