import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import subprocess
import queue
import os
import tempfile
import paramiko
from datetime import datetime
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

class DbClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Oracle Automation - Remote DB Client")
        self.root.geometry("1000x850")

        # ---------- Top connection area: two databases ----------
        frm_conn = ttk.LabelFrame(root, text="Connections", padding=10)
        frm_conn.pack(fill=tk.X, padx=10, pady=5)

        # --- Database 1 ---
        frm_db1 = ttk.LabelFrame(frm_conn, text="Database 1", padding=5)
        frm_db1.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        ttk.Label(frm_db1, text="Host:").grid(row=0, column=0, sticky=tk.W)
        self.host1 = ttk.Entry(frm_db1, width=16)
        self.host1.grid(row=0, column=1, padx=5)
        self.host1.insert(0, "localhost")

        ttk.Label(frm_db1, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(10,0))
        self.port1 = ttk.Entry(frm_db1, width=7)
        self.port1.grid(row=0, column=3, padx=5)
        self.port1.insert(0, "1521")

        ttk.Label(frm_db1, text="Service:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.service1 = ttk.Entry(frm_db1, width=16)
        self.service1.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(frm_db1, text="User:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.user1 = ttk.Entry(frm_db1, width=16)
        self.user1.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(frm_db1, text="Password:").grid(row=2, column=2, sticky=tk.W, padx=5)
        self.password1 = ttk.Entry(frm_db1, width=16, show="*")
        self.password1.grid(row=2, column=3, padx=5, pady=2)

        self.btn_connect1 = ttk.Button(frm_db1, text="Connect", command=lambda: self.connect_db(1))
        self.btn_connect1.grid(row=3, column=0, columnspan=4, pady=5)

        # --- Database 2 ---
        frm_db2 = ttk.LabelFrame(frm_conn, text="Database 2", padding=5)
        frm_db2.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(frm_db2, text="Host:").grid(row=0, column=0, sticky=tk.W)
        self.host2 = ttk.Entry(frm_db2, width=16)
        self.host2.grid(row=0, column=1, padx=5)
        self.host2.insert(0, "localhost")

        ttk.Label(frm_db2, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(10,0))
        self.port2 = ttk.Entry(frm_db2, width=7)
        self.port2.grid(row=0, column=3, padx=5)
        self.port2.insert(0, "1521")

        ttk.Label(frm_db2, text="Service:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.service2 = ttk.Entry(frm_db2, width=16)
        self.service2.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(frm_db2, text="User:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.user2 = ttk.Entry(frm_db2, width=16)
        self.user2.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(frm_db2, text="Password:").grid(row=2, column=2, sticky=tk.W, padx=5)
        self.password2 = ttk.Entry(frm_db2, width=16, show="*")
        self.password2.grid(row=2, column=3, padx=5, pady=2)

        self.btn_connect2 = ttk.Button(frm_db2, text="Connect", command=lambda: self.connect_db(2))
        self.btn_connect2.grid(row=3, column=0, columnspan=4, pady=5)

        frm_conn.columnconfigure(0, weight=1)
        frm_conn.columnconfigure(1, weight=1)

        # Engines
        self.engine1 = None
        self.engine2 = None

        # ---------- Notebook for tabs ----------
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # ----- SQL Query tab -----
        self.tab_query = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_query, text="SQL Query")
        self._build_query_tab()

        # ----- DataPump tab -----
        self.tab_datapump = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_datapump, text="DataPump")
        self._build_datapump_tab()

        # Status bar
        self.status = tk.StringVar()
        self.status.set("Not connected")
        ttk.Label(root, textvariable=self.status, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, padx=10, pady=2)

    # ======================== SQL Query Tab ========================
    def _build_query_tab(self):
        # Target DB selector
        frm_ctrl = ttk.Frame(self.tab_query, padding=5)
        frm_ctrl.pack(fill=tk.X)

        ttk.Label(frm_ctrl, text="Target DB:").pack(side=tk.LEFT)
        self.query_target = ttk.Combobox(frm_ctrl, values=["Database 1", "Database 2"], state="readonly", width=12)
        self.query_target.pack(side=tk.LEFT, padx=5)
        self.query_target.set("Database 1")

        frm_query = ttk.LabelFrame(self.tab_query, text="SQL Query", padding=10)
        frm_query.pack(fill=tk.BOTH, expand=True, pady=5)

        self.query_text = scrolledtext.ScrolledText(frm_query, height=6, font=("Consolas", 10))
        self.query_text.pack(fill=tk.BOTH, expand=True)

        btn_run = ttk.Button(frm_query, text="Run Query", command=self.run_query)
        btn_run.pack(pady=5, anchor=tk.W)

        frm_results = ttk.LabelFrame(self.tab_query, text="Results", padding=10)
        frm_results.pack(fill=tk.BOTH, expand=True, pady=5)

        self.tree = ttk.Treeview(frm_results)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_y = ttk.Scrollbar(frm_results, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scroll_y.set)

    # ======================== DataPump Tab ========================
    def _build_datapump_tab(self):
        canvas = tk.Canvas(self.tab_datapump)
        scrollbar = ttk.Scrollbar(self.tab_datapump, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        frm_main = self.scrollable_frame

        # Mode selection
        self.dp_mode = tk.StringVar(value="export")
        ttk.Radiobutton(frm_main, text="Export", variable=self.dp_mode, value="export", command=self._on_dp_mode_change).grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(frm_main, text="Import", variable=self.dp_mode, value="import", command=self._on_dp_mode_change).grid(row=0, column=1, sticky=tk.W, padx=20)

        row = 1
        ttk.Label(frm_main, text="Directory:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.dir_entry = ttk.Entry(frm_main, width=30)
        self.dir_entry.grid(row=row, column=1, pady=2, padx=5, sticky=tk.W)
        self.dir_entry.insert(0, "DATA_PUMP_DIR")

        row += 1
        ttk.Label(frm_main, text="Dump file:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.dumpfile_entry = ttk.Entry(frm_main, width=30)
        self.dumpfile_entry.grid(row=row, column=1, pady=2, padx=5, sticky=tk.W)
        self.dumpfile_entry.insert(0, "export.dmp")

        row += 1
        ttk.Label(frm_main, text="Log file:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.logfile_entry = ttk.Entry(frm_main, width=30)
        self.logfile_entry.grid(row=row, column=1, pady=2, padx=5, sticky=tk.W)
        self.logfile_entry.insert(0, "export.log")

        # Schemas (common)
        row += 1
        ttk.Label(frm_main, text="Schemas:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.schemas_entry = ttk.Entry(frm_main, width=30)
        self.schemas_entry.grid(row=row, column=1, pady=2, padx=5, sticky=tk.W)

        # Tables
        row += 1
        ttk.Label(frm_main, text="Tables:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.tables_entry = ttk.Entry(frm_main, width=30)
        self.tables_entry.grid(row=row, column=1, pady=2, padx=5, sticky=tk.W)

        # Content
        row += 1
        ttk.Label(frm_main, text="Content:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.content_combo = ttk.Combobox(frm_main, values=["ALL", "DATA_ONLY", "METADATA_ONLY"], state="readonly", width=15)
        self.content_combo.grid(row=row, column=1, pady=2, padx=5, sticky=tk.W)
        self.content_combo.set("ALL")

        # Parallel
        row += 1
        ttk.Label(frm_main, text="Parallel:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.parallel_spin = ttk.Spinbox(frm_main, from_=1, to=32, width=5)
        self.parallel_spin.grid(row=row, column=1, pady=2, padx=5, sticky=tk.W)
        self.parallel_spin.set(1)

        # Compression
        row += 1
        ttk.Label(frm_main, text="Compression:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.compression_combo = ttk.Combobox(frm_main, values=["NONE", "METADATA_ONLY", "DATA_ONLY", "ALL"], state="readonly", width=15)
        self.compression_combo.grid(row=row, column=1, pady=2, padx=5, sticky=tk.W)
        self.compression_combo.set("NONE")

        # ---- IMPORT ONLY: remap_schema ---- #
        row += 1
        self.lbl_remap_from = ttk.Label(frm_main, text="Remap Schema FROM:")
        self.remap_from_entry = ttk.Entry(frm_main, width=20)
        self.lbl_remap_to = ttk.Label(frm_main, text="TO:")
        self.remap_to_entry = ttk.Entry(frm_main, width=20)
        # Initially hidden (export mode)
        self.lbl_remap_from.grid(row=row, column=0, sticky=tk.W, pady=2)
        self.remap_from_entry.grid(row=row, column=1, pady=2, padx=5, sticky=tk.W)
        self.lbl_remap_to.grid(row=row, column=2, padx=5, sticky=tk.W)
        self.remap_to_entry.grid(row=row, column=3, padx=5, sticky=tk.W)
        # Hide by default if export
        if self.dp_mode.get() == "export":
            self.hide_remap_fields()

        # Extra params
        row += 1
        ttk.Label(frm_main, text="Extra params:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.extra_entry = ttk.Entry(frm_main, width=50)
        self.extra_entry.grid(row=row, column=1, columnspan=3, pady=2, padx=5, sticky=tk.W)

        # Command preview
        row += 1
        ttk.Label(frm_main, text="Generated Command:", font=("", 9, "bold")).grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(10,0))
        row += 1
        self.cmd_text = scrolledtext.ScrolledText(frm_main, height=4, font=("Consolas", 9), state=tk.NORMAL)
        self.cmd_text.grid(row=row, column=0, columnspan=3, sticky="ew", pady=5)

        # Buttons
        row += 1
        btn_gen = ttk.Button(frm_main, text="Generate Command", command=self.generate_datapump_cmd)
        btn_gen.grid(row=row, column=0, pady=5, sticky=tk.W)
        self.btn_run = ttk.Button(frm_main, text="Run", command=self.run_datapump)
        self.btn_run.grid(row=row, column=1, pady=5, padx=5, sticky=tk.W)
        self.btn_stop = ttk.Button(frm_main, text="Stop", command=self.stop_datapump, state=tk.DISABLED)
        self.btn_stop.grid(row=row, column=2, pady=5, padx=5, sticky=tk.W)

        # Output console + clear
        row += 1
        ttk.Label(frm_main, text="Output:", font=("", 9, "bold")).grid(row=row, column=0, columnspan=3, sticky=tk.W)
        row += 1
        self.output_text = scrolledtext.ScrolledText(frm_main, height=10, font=("Consolas", 9), state=tk.DISABLED)
        self.output_text.grid(row=row, column=0, columnspan=3, sticky="nsew", pady=5)

        row += 1
        btn_clear = ttk.Button(frm_main, text="Clear Output", command=self.clear_output)
        btn_clear.grid(row=row, column=0, pady=5, sticky=tk.W)

        # ---- File Transfer section (unchanged from before) ----
        row += 1
        frm_transfer = ttk.LabelFrame(frm_main, text="File Transfer", padding=10)
        frm_transfer.grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)

        ttk.Label(frm_transfer, text="Source (DB Server) SSH:").grid(row=0, column=0, columnspan=4, sticky=tk.W)

        ttk.Label(frm_transfer, text="Host:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.ssh_source_host = ttk.Entry(frm_transfer, width=18)
        self.ssh_source_host.grid(row=1, column=1, padx=5)
        self.ssh_source_host.insert(0, self.host1.get())

        ttk.Label(frm_transfer, text="Port:").grid(row=1, column=2, sticky=tk.W, padx=5)
        self.ssh_source_port = ttk.Entry(frm_transfer, width=6)
        self.ssh_source_port.grid(row=1, column=3, padx=5)
        self.ssh_source_port.insert(0, "22")

        ttk.Label(frm_transfer, text="User:").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.ssh_source_user = ttk.Entry(frm_transfer, width=18)
        self.ssh_source_user.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(frm_transfer, text="Password:").grid(row=2, column=2, sticky=tk.W, padx=5)
        self.ssh_source_pass = ttk.Entry(frm_transfer, width=18, show="*")
        self.ssh_source_pass.grid(row=2, column=3, padx=5, pady=2)

        ttk.Label(frm_transfer, text="Source Path:").grid(row=3, column=0, sticky=tk.W, padx=5)
        self.source_path = ttk.Entry(frm_transfer, width=50)
        self.source_path.grid(row=3, column=1, columnspan=3, padx=5, pady=2, sticky="ew")
        ttk.Button(frm_transfer, text="Auto-fill", command=self.autofill_source_path).grid(row=3, column=4, padx=5)

        ttk.Label(frm_transfer, text="Destination Server SSH:").grid(row=4, column=0, columnspan=4, sticky=tk.W, pady=(10,0))
        ttk.Label(frm_transfer, text="Host:").grid(row=5, column=0, sticky=tk.W, padx=5)
        self.ssh_dest_host = ttk.Entry(frm_transfer, width=18)
        self.ssh_dest_host.grid(row=5, column=1, padx=5)
        ttk.Label(frm_transfer, text="Port:").grid(row=5, column=2, sticky=tk.W, padx=5)
        self.ssh_dest_port = ttk.Entry(frm_transfer, width=6)
        self.ssh_dest_port.grid(row=5, column=3, padx=5)
        self.ssh_dest_port.insert(0, "22")
        ttk.Label(frm_transfer, text="User:").grid(row=6, column=0, sticky=tk.W, padx=5)
        self.ssh_dest_user = ttk.Entry(frm_transfer, width=18)
        self.ssh_dest_user.grid(row=6, column=1, padx=5, pady=2)
        ttk.Label(frm_transfer, text="Password:").grid(row=6, column=2, sticky=tk.W, padx=5)
        self.ssh_dest_pass = ttk.Entry(frm_transfer, width=18, show="*")
        self.ssh_dest_pass.grid(row=6, column=3, padx=5, pady=2)
        ttk.Label(frm_transfer, text="Dest Path:").grid(row=7, column=0, sticky=tk.W, padx=5)
        self.dest_path = ttk.Entry(frm_transfer, width=50)
        self.dest_path.grid(row=7, column=1, columnspan=3, padx=5, pady=2, sticky="ew")

        self.transfer_btn = ttk.Button(frm_transfer, text="Transfer Files", command=self.transfer_files)
        self.transfer_btn.grid(row=8, column=0, columnspan=5, pady=10)

        # Configure grid weights
        frm_main.columnconfigure(1, weight=1)
        frm_main.rowconfigure(row, weight=1)
        frm_transfer.columnconfigure(1, weight=1)

        # Process management
        self.dp_process = None
        self.dp_queue = queue.Queue()
        self.dp_thread = None
        self.after_id = None

    # ---- remap_schema show/hide based on mode ----
    def _on_dp_mode_change(self):
        if self.dp_mode.get() == "import":
            self.show_remap_fields()
        else:
            self.hide_remap_fields()

    def hide_remap_fields(self):
        self.lbl_remap_from.grid_remove()
        self.remap_from_entry.grid_remove()
        self.lbl_remap_to.grid_remove()
        self.remap_to_entry.grid_remove()

    def show_remap_fields(self):
        self.lbl_remap_from.grid()
        self.remap_from_entry.grid()
        self.lbl_remap_to.grid()
        self.remap_to_entry.grid()

    # ============= Connection Management =============
    def get_oracle_connection_string(self, host, port, service, user, password):
        if not all([host, port, service, user]):
            raise ValueError("Host, port, service, and user are required.")
        return f"oracle+oracledb://{user}:{quote_plus(password)}@{host}:{port}/?service_name={service}"

    def connect_db(self, db_num):
        if db_num == 1:
            host = self.host1.get().strip()
            port = self.port1.get().strip()
            service = self.service1.get().strip()
            user = self.user1.get().strip()
            password = self.password1.get()
            engine_attr = "engine1"
        else:
            host = self.host2.get().strip()
            port = self.port2.get().strip()
            service = self.service2.get().strip()
            user = self.user2.get().strip()
            password = self.password2.get()
            engine_attr = "engine2"

        try:
            conn_str = self.get_oracle_connection_string(host, port, service, user, password)
            engine = create_engine(conn_str)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1 FROM DUAL"))
            setattr(self, engine_attr, engine)
            self.status.set(f"Database {db_num} connected: {host}:{port}/{service}")
            messagebox.showinfo("Success", f"Connected to Database {db_num}.")
        except Exception as e:
            setattr(self, engine_attr, None)
            self.status.set(f"Database {db_num} connection failed")
            messagebox.showerror("Connection Error", f"Database {db_num}: {e}")

    def _get_engine_by_target(self, target_str):
        if target_str == "Database 1":
            return self.engine1
        else:
            return self.engine2

    # ============= SQL Query Tab =============
    def run_query(self):
        target = self.query_target.get()
        engine = self._get_engine_by_target(target)
        if engine is None:
            messagebox.showwarning("Not connected", f"{target} is not connected.")
            return
        sql = self.query_text.get("1.0", tk.END).strip().rstrip(';').strip()
        if not sql:
            messagebox.showwarning("Empty query", "Please enter a SQL query.")
            return
        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql))
                if result.returns_rows:
                    for row_id in self.tree.get_children():
                        self.tree.delete(row_id)
                    columns = result.keys()
                    self.tree['columns'] = list(columns)
                    self.tree['show'] = 'headings'
                    for col in columns:
                        self.tree.heading(col, text=col)
                        self.tree.column(col, width=120, anchor=tk.W)
                    for row in result:
                        self.tree.insert("", tk.END, values=list(row))
                    self.status.set(f"Query on {target} returned {result.rowcount} rows.")
                else:
                    conn.commit()
                    self.status.set(f"Statement executed on {target}. Rows affected: {result.rowcount}")
                    messagebox.showinfo("Done", f"Rows affected: {result.rowcount}")
        except SQLAlchemyError as e:
            messagebox.showerror("Query Error", str(e))
            self.status.set("Query error")

    # ============= DataPump (uses Database 1 only) =============
    def generate_datapump_cmd(self):
        """Build expdp/impdp command using Database 1 connection details."""
        try:
            host = self.host1.get().strip()
            port = self.port1.get().strip()
            service = self.service1.get().strip()
            user = self.user1.get().strip()
            password = self.password1.get()
            if not all([host, port, service, user, password]):
                messagebox.showwarning("Missing connection", "Fill Database 1 connection fields.")
                return

            connect_str = f"{user}/{password}@//{host}:{port}/{service}"

            # Auto filenames for export
            if self.dp_mode.get() == "export":
                schemas_text = self.schemas_entry.get().strip()
                if schemas_text:
                    first_schema = schemas_text.split(",")[0].strip()
                    if first_schema:
                        date_str = datetime.now().strftime("%d%m%y")
                        if self.dumpfile_entry.get().strip() in ("export.dmp", ""):
                            self.dumpfile_entry.delete(0, tk.END)
                            self.dumpfile_entry.insert(0, f"{first_schema}_{date_str}.dmp")
                        if self.logfile_entry.get().strip() in ("export.log", ""):
                            self.logfile_entry.delete(0, tk.END)
                            self.logfile_entry.insert(0, f"{first_schema}_{date_str}.log")

            if self.dp_mode.get() == "export":
                cmd = ["expdp", connect_str]
            else:
                cmd = ["impdp", connect_str]

            dp_dir = self.dir_entry.get().strip()
            if dp_dir:
                cmd.append(f"directory={dp_dir}")
            dumpfile = self.dumpfile_entry.get().strip()
            if dumpfile:
                cmd.append(f"dumpfile={dumpfile}")
            logfile = self.logfile_entry.get().strip()
            if logfile:
                cmd.append(f"logfile={logfile}")

            schemas = self.schemas_entry.get().strip()
            if schemas:
                cmd.append(f"schemas={schemas.replace(' ', '')}")

            # remap_schema for import only
            if self.dp_mode.get() == "import":
                remap_from = self.remap_from_entry.get().strip()
                remap_to = self.remap_to_entry.get().strip()
                if remap_from and remap_to:
                    cmd.append(f"remap_schema={remap_from}:{remap_to}")

            tables = self.tables_entry.get().strip()
            if tables:
                cmd.append(f"tables={tables.replace(' ', '')}")

            content = self.content_combo.get()
            if content != "ALL":
                cmd.append(f"content={content}")

            parallel = self.parallel_spin.get()
            if parallel != "1":
                cmd.append(f"parallel={parallel}")

            compression = self.compression_combo.get()
            if compression != "NONE":
                cmd.append(f"compression={compression}")

            extra = self.extra_entry.get().strip()
            if extra:
                cmd.extend(extra.split())

            cmd_str = subprocess.list2cmdline(cmd)
            self.cmd_text.config(state=tk.NORMAL)
            self.cmd_text.delete("1.0", tk.END)
            self.cmd_text.insert(tk.END, cmd_str)
            self.cmd_text.config(state=tk.NORMAL)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate command: {e}")

    def run_datapump(self):
        cmd_str = self.cmd_text.get("1.0", tk.END).strip()
        if not cmd_str:
            messagebox.showwarning("No command", "Generate a command first.")
            return

        self.btn_run.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.config(state=tk.DISABLED)

        self.dp_process = subprocess.Popen(
            cmd_str,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        self.dp_queue = queue.Queue()
        self.dp_thread = threading.Thread(target=self._read_output, args=(self.dp_process.stdout,), daemon=True)
        self.dp_thread.start()

        self.after_id = self.root.after(100, self._process_output)

    def _read_output(self, stream):
        try:
            for line in iter(stream.readline, ''):
                self.dp_queue.put(line)
            stream.close()
        except Exception:
            pass
        finally:
            self.dp_queue.put(None)

    def _process_output(self):
        try:
            while True:
                line = self.dp_queue.get_nowait()
                if line is None:
                    self._on_process_finished()
                    return
                self.output_text.config(state=tk.NORMAL)
                self.output_text.insert(tk.END, line)
                self.output_text.see(tk.END)
                self.output_text.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        self.after_id = self.root.after(100, self._process_output)

    def _on_process_finished(self):
        self.btn_run.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.dp_process = None
        self.status.set("DataPump job completed")

    def stop_datapump(self):
        if self.dp_process and self.dp_process.poll() is None:
            self.dp_process.terminate()
            try:
                self.dp_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.dp_process.kill()
            self.output_text.config(state=tk.NORMAL)
            self.output_text.insert(tk.END, "\n*** Process terminated by user ***\n")
            self.output_text.config(state=tk.DISABLED)
        self._on_process_finished()

    def clear_output(self):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.config(state=tk.DISABLED)

    # ============= File Transfer (unchanged, uses source_path from DB query) =============
    def autofill_source_path(self):
        if self.engine1 is None:
            messagebox.showwarning("Not connected", "Connect Database 1 first (source server).")
            return
        dp_directory = self.dir_entry.get().strip()
        if not dp_directory:
            messagebox.showwarning("Missing directory", "Enter the DataPump directory name.")
            return

        try:
            with self.engine1.connect() as conn:
                result = conn.execute(
                    text("SELECT directory_path FROM dba_directories WHERE directory_name = :dir"),
                    {"dir": dp_directory.upper()}
                )
                row = result.fetchone()
                if not row:
                    messagebox.showwarning("Not found", f"Directory '{dp_directory}' not found.")
                    return
                os_path = row[0]
                self.source_path.delete(0, tk.END)
                self.source_path.insert(0, os_path)
                self._log(f"Found path: {os_path}")
        except Exception as e:
            messagebox.showerror("Query error", str(e))

    def transfer_files(self):
        dumpfile = self.dumpfile_entry.get().strip()
        logfile = self.logfile_entry.get().strip()
        source_dir = self.source_path.get().strip()
        dest_dir = self.dest_path.get().strip()

        if not dumpfile and not logfile:
            messagebox.showwarning("Missing files", "Enter dumpfile and/or logfile names.")
            return
        if not source_dir or not dest_dir:
            messagebox.showwarning("Missing paths", "Enter both source and destination paths.")
            return

        src_host = self.ssh_source_host.get().strip()
        src_port = int(self.ssh_source_port.get().strip())
        src_user = self.ssh_source_user.get().strip()
        src_pass = self.ssh_source_pass.get()

        dst_host = self.ssh_dest_host.get().strip()
        dst_port = int(self.ssh_dest_port.get().strip())
        dst_user = self.ssh_dest_user.get().strip()
        dst_pass = self.ssh_dest_pass.get()

        if not all([src_host, src_user, src_pass, dst_host, dst_user, dst_pass]):
            messagebox.showwarning("Missing SSH credentials", "Fill all SSH fields.")
            return

        self.transfer_btn.config(state=tk.DISABLED)
        self._log("=== Starting direct file transfer (streaming) ===")

        def worker():
            try:
                files = [f for f in (dumpfile, logfile) if f]

                # Connect to source server
                self._log("Connecting to source server...")
                src_ssh = paramiko.SSHClient()
                src_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                src_ssh.connect(src_host, port=src_port, username=src_user, password=src_pass)
                src_sftp = src_ssh.open_sftp()

                # Connect to destination server
                self._log("Connecting to destination server...")
                dst_ssh = paramiko.SSHClient()
                dst_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                dst_ssh.connect(dst_host, port=dst_port, username=dst_user, password=dst_pass)
                dst_sftp = dst_ssh.open_sftp()

                # Transfer each file directly (memory‑only stream)
                for f in files:
                    src_path = os.path.join(source_dir, f).replace("\\", "/")
                    dst_path = os.path.join(dest_dir, f).replace("\\", "/")

                    self._log(f"Copying {src_path} -> {dst_path}")
                    with src_sftp.open(src_path, 'rb') as src_file:
                        with dst_sftp.open(dst_path, 'wb') as dst_file:
                            # Stream in 1 MB chunks
                            while True:
                                chunk = src_file.read(1024 * 1024)
                                if not chunk:
                                    break
                                dst_file.write(chunk)
                    self._log(f"Finished {f}")

                src_sftp.close()
                dst_sftp.close()
                src_ssh.close()
                dst_ssh.close()

                self._log("Transfer completed successfully (direct streaming).")

            except Exception as e:
                self._log(f"Transfer failed: {e}")
            finally:
                self.root.after(0, lambda: self.transfer_btn.config(state=tk.NORMAL))

        threading.Thread(target=worker, daemon=True).start()

    def _log(self, message):
        self.root.after(0, lambda: self._log_now(message))

    def _log_now(self, message):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)

    def on_closing(self):
        if self.dp_process and self.dp_process.poll() is None:
            self.dp_process.terminate()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = DbClientApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()