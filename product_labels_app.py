import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import ImageTk, Image
import mysql.connector
from mysql.connector import Error
import base64
import os
import json
import csv
import re 

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "123456"
DB_NAME = "product_labels"

EXPORT_COLUMNS = [
    "id",
    "image_name",
    "product_name",
    "manufacturer_company",
    "manufacturer_phone",
    "importer_company",
    "importer_phone",
    "manufacturing_date",
    "expiry_date",
    "type",
]

def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

def init_db():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS labels (
                id INT AUTO_INCREMENT PRIMARY KEY,
                image_name VARCHAR(255) NOT NULL,
                image_path VARCHAR(255) NOT NULL,
                image_base64 LONGTEXT,
                product_name VARCHAR(255),
                manufacturer_company VARCHAR(255),
                manufacturer_address TEXT,
                manufacturer_phone VARCHAR(50),
                importer_company VARCHAR(255),
                importer_address TEXT,
                importer_phone VARCHAR(50),
                manufacturing_date VARCHAR(50),
                expiry_date VARCHAR(50),
                type VARCHAR(100)
            )
        ''')
        conn.commit()
    except Error as e:
        messagebox.showerror("Database Error", f"Failed to initialize database: {e}")
    finally:
        if conn:
            conn.close()

init_db()

def validate_date(date_str):
    if not date_str:
        return True
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    return re.match(pattern, date_str) is not None

def validate_phone(phone_str):
    if not phone_str:
        return True
    pattern = r'^[\d+\-\s]+$'
    return re.match(pattern, phone_str) is not None

def check_data_before_save(data):
    errors = []
    if not data['image_path']:
        errors.append("Image path is required.")
    if not validate_date(data['manufacturing_date']):
        errors.append("Manufacturing date format invalid (use YYYY-MM-DD).")
    if not validate_date(data['expiry_date']):
        errors.append("Expiry date format invalid (use YYYY-MM-DD).")
    if not validate_phone(data['manufacturer_phone']):
        errors.append("Manufacturer phone format invalid.")
    if not validate_phone(data['importer_phone']):
        errors.append("Importer phone format invalid.")
    return errors

class LabelingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Product Image Labeling Tool")
        self.geometry("1000x800")

        self.image_path = None
        self.image_name = None
        self.image_tk = None

        self.create_widgets()
        self.refresh_data_display()

    def create_widgets(self):
        self.image_frame = tk.Frame(self)
        self.image_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.image_label = tk.Label(self.image_frame)
        self.image_label.pack(fill=tk.BOTH, expand=True)

        buttons_frame = tk.Frame(self)
        buttons_frame.pack(side=tk.TOP, pady=10)

        tk.Button(buttons_frame, text="Load Image", command=self.load_image).pack(side=tk.LEFT, padx=5)
        tk.Button(buttons_frame, text="Save to DB", command=self.save_to_db).pack(side=tk.LEFT, padx=5)
        tk.Button(buttons_frame, text="Export CSV", command=self.export_csv).pack(side=tk.LEFT, padx=5)
        tk.Button(buttons_frame, text="Export JSON", command=self.export_json).pack(side=tk.LEFT, padx=5)

        inputs_frame = tk.Frame(self)
        inputs_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        tk.Label(inputs_frame, text="Product Name:").grid(row=0, column=0, sticky=tk.W)
        self.product_name_entry = tk.Entry(inputs_frame, width=50)
        self.product_name_entry.grid(row=0, column=1, pady=5)

        tk.Label(inputs_frame, text="Manufacturer Company:").grid(row=1, column=0, sticky=tk.W)
        self.manufacturer_company_entry = tk.Entry(inputs_frame, width=50)
        self.manufacturer_company_entry.grid(row=1, column=1, pady=5)

        tk.Label(inputs_frame, text="Manufacturer Address:").grid(row=2, column=0, sticky=tk.W)
        self.manufacturer_address_entry = tk.Entry(inputs_frame, width=50)
        self.manufacturer_address_entry.grid(row=2, column=1, pady=5)

        tk.Label(inputs_frame, text="Manufacturer Phone:").grid(row=3, column=0, sticky=tk.W)
        self.manufacturer_phone_entry = tk.Entry(inputs_frame, width=50)
        self.manufacturer_phone_entry.grid(row=3, column=1, pady=5)

        tk.Label(inputs_frame, text="Importer Company:").grid(row=4, column=0, sticky=tk.W)
        self.importer_company_entry = tk.Entry(inputs_frame, width=50)
        self.importer_company_entry.grid(row=4, column=1, pady=5)

        tk.Label(inputs_frame, text="Importer Address:").grid(row=5, column=0, sticky=tk.W)
        self.importer_address_entry = tk.Entry(inputs_frame, width=50)
        self.importer_address_entry.grid(row=5, column=1, pady=5)

        tk.Label(inputs_frame, text="Importer Phone:").grid(row=6, column=0, sticky=tk.W)
        self.importer_phone_entry = tk.Entry(inputs_frame, width=50)
        self.importer_phone_entry.grid(row=6, column=1, pady=5)

        tk.Label(inputs_frame, text="Manufacturing Date (YYYY-MM-DD):").grid(row=7, column=0, sticky=tk.W)
        self.manufacturing_date_entry = tk.Entry(inputs_frame, width=50)
        self.manufacturing_date_entry.grid(row=7, column=1, pady=5)

        tk.Label(inputs_frame, text="Expiry Date (YYYY-MM-DD):").grid(row=8, column=0, sticky=tk.W)
        self.expiry_date_entry = tk.Entry(inputs_frame, width=50)
        self.expiry_date_entry.grid(row=8, column=1, pady=5)

        tk.Label(inputs_frame, text="Type:").grid(row=9, column=0, sticky=tk.W)
        self.type_entry = tk.Entry(inputs_frame, width=50)
        self.type_entry.grid(row=9, column=1, pady=5)

        display_frame = tk.Frame(self)
        display_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(display_frame, text="Displayed Data (by Type):").pack(anchor=tk.W)

        self.type_filter = tk.StringVar()
        self.type_combo = ttk.Combobox(display_frame, textvariable=self.type_filter, state="readonly")
        self.type_combo.pack(anchor=tk.W)
        self.type_combo.bind("<<ComboboxSelected>>", self.refresh_data_display)

        self.data_tree = ttk.Treeview(
            display_frame,
            columns=("image_name", "product_name", "manufacturer_company", "manufacturing_date", "type"),
            show="headings"
        )
        for col, title in [
            ("image_name", "Image Name"),
            ("product_name", "Product Name"),
            ("manufacturer_company", "Manufacturer Company"),
            ("manufacturing_date", "Mfg Date"),
            ("type", "Type"),
        ]:
            self.data_tree.heading(col, text=title)
            self.data_tree.column(col, width=180, stretch=True)

        self.data_tree.pack(fill=tk.BOTH, expand=True)

        self.update_type_combo()

    def load_image(self):
        try:
            file_path = filedialog.askopenfilename(
                filetypes=[("Image files", "*.heic *.jpg *.jpeg *.png *.gif *.bmp")]
            )
            if not file_path:
                return
            img = Image.open(file_path)
            img.thumbnail((400, 400))
            self.image_tk = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.image_tk)
            self.image_path = file_path
            self.image_name = os.path.basename(file_path)
        except Exception as e:
            messagebox.showerror("File Error", f"Failed to load image: {e}. Ensure file format is supported.")

    def save_to_db(self):
        if not self.image_path:
            messagebox.showerror("Input Error", "Please load an image first.")
            return

        data = {
            "image_name": self.image_name,
            "image_path": self.image_path,
            "image_base64": "",
            "product_name": self.product_name_entry.get().strip(),
            "manufacturer_company": self.manufacturer_company_entry.get().strip(),
            "manufacturer_address": self.manufacturer_address_entry.get().strip(),
            "manufacturer_phone": self.manufacturer_phone_entry.get().strip(),
            "importer_company": self.importer_company_entry.get().strip(),
            "importer_address": self.importer_address_entry.get().strip(),
            "importer_phone": self.importer_phone_entry.get().strip(),
            "manufacturing_date": self.manufacturing_date_entry.get().strip(),
            "expiry_date": self.expiry_date_entry.get().strip(),
            "type": self.type_entry.get().strip(),
        }

        errors = check_data_before_save(data)
        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return

        try:
            with open(self.image_path, "rb") as f:
                data["image_base64"] = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            messagebox.showerror("File Error", f"Failed to encode image to base64: {e}")
            return

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO labels (
                    image_name, image_path, image_base64, product_name,
                    manufacturer_company, manufacturer_address, manufacturer_phone,
                    importer_company, importer_address, importer_phone,
                    manufacturing_date, expiry_date, type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                data["image_name"], data["image_path"], data["image_base64"], data["product_name"],
                data["manufacturer_company"], data["manufacturer_address"], data["manufacturer_phone"],
                data["importer_company"], data["importer_address"], data["importer_phone"],
                data["manufacturing_date"], data["expiry_date"], data["type"]
            ))
            conn.commit()
            messagebox.showinfo("Success", "Data saved to database.")
            self.clear_entries()
            self.refresh_data_display()
            self.update_type_combo()
        except Error as e:
            messagebox.showerror("Database Error", f"Failed to save to database: {e}")
        finally:
            if conn:
                conn.close()

    def clear_entries(self):
        for entry in [
            self.product_name_entry, self.manufacturer_company_entry, self.manufacturer_address_entry,
            self.manufacturer_phone_entry, self.importer_company_entry, self.importer_address_entry,
            self.importer_phone_entry, self.manufacturing_date_entry, self.expiry_date_entry, self.type_entry
        ]:
            entry.delete(0, tk.END)

    def refresh_data_display(self, event=None):
        for item in self.data_tree.get_children():
            self.data_tree.delete(item)

        type_filter = self.type_filter.get()

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "SELECT image_name, product_name, manufacturer_company, manufacturing_date, type FROM labels"
            params = ()
            if type_filter:
                query += " WHERE type = %s"
                params = (type_filter,)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            for row in rows:
                self.data_tree.insert("", tk.END, values=row)
        except Error as e:
            messagebox.showerror("Database Error", f"Failed to fetch data: {e}")
        finally:
            if conn:
                conn.close()

    def update_type_combo(self):
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT type FROM labels WHERE type IS NOT NULL AND type != ''")
            types = [row[0] for row in cursor.fetchall()]
            self.type_combo['values'] = [""] + types 
        except Error as e:
            messagebox.showerror("Database Error", f"Failed to update types: {e}")
        finally:
            if conn:
                conn.close()

    def export_json(self):
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM labels")
            rows = cursor.fetchall()
            data = []
            for row in rows:
                data.append({
                    "image_name": row[1],
                    "image_path": row[2],
                    "image_base64": row[3],  # JSON vẫn giữ đầy đủ, nếu muốn bỏ hãy xóa dòng này
                    "product_name": row[4],
                    "manufacturer": {
                        "company_name": row[5],
                        "address": row[6],
                        "phone": row[7]
                    },
                    "importer": {
                        "company_name": row[8],
                        "address": row[9],
                        "phone": row[10]
                    },
                    "manufacturing_date": row[11],
                    "expiry_date": row[12],
                    "type": row[13]
                })
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to read data: {e}")
            return
        finally:
            if conn:
                conn.close()

        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Success", "Data exported to JSON.")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export JSON: {e}")

    def export_csv(self):
        """
        Xuất CSV chỉ với các cột trong EXPORT_COLUMNS để tránh chuỗi base64 quá dài.
        """
        allowed_db_cols = {
            "id": "id",
            "image_name": "image_name",
            "product_name": "product_name",
            "manufacturer_company": "manufacturer_company",
            "manufacturer_phone": "manufacturer_phone",
            "importer_company": "importer_company",
            "importer_phone": "importer_phone",
            "manufacturing_date": "manufacturing_date",
            "expiry_date": "expiry_date",
            "type": "type",
        }

        selected_cols = [c for c in EXPORT_COLUMNS if c in allowed_db_cols]
        if not selected_cols:
            messagebox.showerror("Export Error", "No valid columns selected for CSV export.")
            return

        sql_cols = ", ".join(allowed_db_cols[c] for c in selected_cols)
        query = f"SELECT {sql_cols} FROM labels"

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to read data: {e}")
            return
        finally:
            if conn:
                conn.close()

        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(selected_cols)
                writer.writerows(rows)
            messagebox.showinfo("Success", "Data exported to CSV (gọn).")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export CSV: {e}")

if __name__ == "__main__":
    app = LabelingApp()
    app.mainloop()
