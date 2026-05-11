import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

class DbClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Remote DB Client")
        self.root.geometry("900x650")

        # Connection details
        frm_conn = ttk.LabelFrame(root, text="Connection", padding=10)
        frm_conn.pack(fill=tk.X, padx=10, pady=5)

        # DB type selector
        ttk.Label(frm_conn, text="DB Type:").grid(row=0, column=0, sticky=tk.W)
        self.db_type = ttk.Combobox(frm_conn, values=["postgresql", "mysql","oracle"], state="readonly", width=12)
        self.db_type.grid(row=0, column=1, padx=5)
        self.db_type.set("postgresql")

        # Host & Port
        ttk.Label(frm_conn, text="Host:").grid(row=0, column=2, sticky=tk.W, padx=(20,0))
        self.host = ttk.Entry(frm_conn, width=18)
        self.host.grid(row=0, column=3, padx=5)
        self.host.insert(0, "localhost")

        ttk.Label(frm_conn, text="Port:").grid(row=0, column=4, sticky=tk.W, padx=(10,0))
        self.port = ttk.Entry(frm_conn, width=7)
        self.port.grid(row=0, column=5, padx=5)
        self.port.insert(0, "5432")

        # Database, User, Password
        ttk.Label(frm_conn, text="Database:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.db_name = ttk.Entry(frm_conn, width=18)
        self.db_name.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(frm_conn, text="User:").grid(row=1, column=2, sticky=tk.W, pady=5)
        self.user = ttk.Entry(frm_conn, width=18)
        self.user.grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(frm_conn, text="Password:").grid(row=1, column=4, sticky=tk.W, pady=5)
        self.password = ttk.Entry(frm_conn, width=18, show="*")
        self.password.grid(row=1, column=5, padx=5, pady=5)

        # Connect button
        self.btn_connect = ttk.Button(frm_conn, text="Connect", command=self.connect_db)
        self.btn_connect.grid(row=2, column=0, columnspan=6, pady=10)

        self.engine = None                          # SQLAlchemy engine

        # Query area
        frm_query = ttk.LabelFrame(root, text="SQL Query", padding=10)
        frm_query.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.query_text = scrolledtext.ScrolledText(frm_query, height=6, font=("Consolas", 10))
        self.query_text.pack(fill=tk.BOTH, expand=True)

        btn_run = ttk.Button(frm_query, text="Run Query", command=self.run_query)
        btn_run.pack(pady=5, anchor=tk.W)

        # Results table
        frm_results = ttk.LabelFrame(root, text="Results", padding=10)
        frm_results.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Treeview for results
        self.tree = ttk.Treeview(frm_results)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_y = ttk.Scrollbar(frm_results, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scroll_y.set)

        # Status bar
        self.status = tk.StringVar()
        self.status.set("Not connected")
        ttk.Label(root, textvariable=self.status, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, padx=10, pady=2)

    def get_connection_string(self):
        db_type = self.db_type.get().strip()
        host = self.host.get().strip()
        port = self.port.get().strip()
        db = self.db_name.get().strip()
        user = self.user.get().strip()
        pw = self.password.get()
        if not all([host, port, db, user]):
            raise ValueError("Host, port, database (service name), and user are required.")
        
        from urllib.parse import quote_plus

        # Oracle branch (case‑insensitive)
        if db_type.lower() == "oracle":
            # Using the oracledb driver; service_name can be changed to ?sid=... if needed
            return f"oracle+oracledb://{user}:{quote_plus(pw)}@{host}:{port}/?service_name={db}"
        elif db_type.lower() == "postgresql":
            return f"postgresql+psycopg2://{user}:{quote_plus(pw)}@{host}:{port}/{db}"
        elif db_type.lower() == "mysql":
            return f"mysql+pymysql://{user}:{quote_plus(pw)}@{host}:{port}/{db}"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    def connect_db(self):
        try:
            conn_str = self.get_connection_string()
            self.engine = create_engine(conn_str)
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT NAME,OPEN_MODE FROM V$DATABASE"))
            self.status.set(f"Connected to {self.db_name.get()} on {self.host.get()}")
            messagebox.showinfo("Success", "Connected successfully.")
        except Exception as e:
            self.engine = None
            self.status.set("Connection failed")
            messagebox.showerror("Connection Error", str(e))

    def run_query(self):
        if self.engine is None:
            messagebox.showwarning("Not connected", "Please connect to a database first.")
            return
        sql = self.query_text.get("1.0", tk.END).strip()
        if not sql:
            messagebox.showwarning("Empty query", "Please enter a SQL query.")
            return

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql))
                if result.returns_rows:
                    # Clear old results
                    for row_id in self.tree.get_children():
                        self.tree.delete(row_id)
                    # Set columns
                    columns = result.keys()
                    self.tree['columns'] = list(columns)
                    self.tree['show'] = 'headings'
                    for col in columns:
                        self.tree.heading(col, text=col)
                        self.tree.column(col, width=120, anchor=tk.W)
                    # Insert rows
                    for row in result:
                        self.tree.insert("", tk.END, values=list(row))
                    self.status.set(f"Query returned {result.rowcount} rows.")
                else:
                    # For non‑SELECT queries
                    conn.commit()   # auto‑commit may be off, force it
                    self.status.set(f"Query executed. Rows affected: {result.rowcount}")
                    messagebox.showinfo("Done", f"Rows affected: {result.rowcount}")
        except SQLAlchemyError as e:
            messagebox.showerror("Query Error", str(e))
            self.status.set("Query error")

if __name__ == "__main__":
    root = tk.Tk()
    app = DbClientApp(root)
    root.mainloop()