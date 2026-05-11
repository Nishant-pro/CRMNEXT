import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import subprocess
import queue
import sys
import os
import io
import paramiko
from datetime import datetime
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

class DbClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Remote DB Client - Oracle Automation")
        self.root.geometry("1050x900")

        # ---------- Top frame: two DB connections + SSH ----------
        frm_conn = ttk.Frame(root)
        frm_conn.pack(fill=tk.X, padx=10, pady=5)
        frm_conn.columnconfigure(0, weight=1)
        frm_conn.columnconfigure(1, weight=1)

        # ===== Database 1 =====
        frm_db1 = ttk.LabelFrame(frm_conn, text="Oracle Database 1", padding=10)
        frm_db1.grid(row=0, column=0, sticky="nsew", padx=(0,5))

        ttk.Label(frm_db1, text="Host:").grid(row=0, column=0, sticky=tk.W)
        self.host = ttk.Entry(frm_db1, width=16)
        self.host.grid(row=0, column=1, padx=5)
        self.host.insert(0, "localhost")

        ttk.Label(frm_db1, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(5,0))
        self.port = ttk.Entry(frm_db1, width=6)
        self.port.grid(row=0, column=3, padx=5)
        self.port.insert(0, "1521")

        ttk.Label(frm_db1, text="Service Name:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.db_name = ttk.Entry(frm_db1, width=16)
        self.db_name.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(frm_db1, text="User:").grid(row=1, column=2, sticky=tk.W, pady=2)
        self.user = ttk.Entry(frm_db1, width=16)
        self.user.grid(row=1, column=3, padx=5, pady=2)

        ttk.Label(frm_db1, text="Password:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.password = ttk.Entry(frm_db1, width=16, show="*")
        self.password.grid(row=2, column=1, padx=5, pady=2)

        btn_frame_db1 = ttk.Frame(frm_db1)
        btn_frame_db1.grid(row=3, column=0, columnspan=4, pady=8)
        self.btn_db_connect = ttk.Button(btn_frame_db1, text="Connect", command=self.connect_db)
        self.btn_db_connect.pack(side=tk.LEFT, padx=3)
        self.btn_db_disconnect = ttk.Button(btn_frame_db1, text="Disconnect", command=self.disconnect_db, state=tk.DISABLED)
        self.btn_db_disconnect.pack(side=tk.LEFT, padx=3)
        self.db_status_var = tk.StringVar(value="Not connected")
        self.db_status_label = ttk.Label(btn_frame_db1, textvariable=self.db_status_var, foreground="red")
        self.db_status_label.pack(side=tk.LEFT, padx=5)

        # ===== Database 2 =====
        frm_db2 = ttk.LabelFrame(frm_conn, text="Oracle Database 2", padding=10)
        frm_db2.grid(row=0, column=1, sticky="nsew", padx=(5,0))

        ttk.Label(frm_db2, text="Host:").grid(row=0, column=0, sticky=tk.W)
        self.host2 = ttk.Entry(frm_db2, width=16)
        self.host2.grid(row=0, column=1, padx=5)

        ttk.Label(frm_db2, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(5,0))
        self.port2 = ttk.Entry(frm_db2, width=6)
        self.port2.grid(row=0, column=3, padx=5)
        self.port2.insert(0, "1521")

        ttk.Label(frm_db2, text="Service Name:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.db_name2 = ttk.Entry(frm_db2, width=16)
        self.db_name2.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(frm_db2, text="User:").grid(row=1, column=2, sticky=tk.W, pady=2)
        self.user2 = ttk.Entry(frm_db2, width=16)
        self.user2.grid(row=1, column=3, padx=5, pady=2)

        ttk.Label(frm_db2, text="Password:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.password2 = ttk.Entry(frm_db2, width=16, show="*")
        self.password2.grid(row=2, column=1, padx=5, pady=2)

        btn_frame_db2 = ttk.Frame(frm_db2)
        btn_frame_db2.grid(row=3, column=0, columnspan=4, pady=8)
        self.btn_db2_connect = ttk.Button(btn_frame_db2, text="Connect", command=self.connect_db2)
        self.btn_db2_connect.pack(side=tk.LEFT, padx=3)
        self.btn_db2_disconnect = ttk.Button(btn_frame_db2, text="Disconnect", command=self.disconnect_db2, state=tk.DISABLED)
        self.btn_db2_disconnect.pack(side=tk.LEFT, padx=3)
        self.db2_status_var = tk.StringVar(value="Not connected")
        self.db2_status_label = ttk.Label(btn_frame_db2, textvariable=self.db2_status_var, foreground="red")
        self.db2_status_label.pack(side=tk.LEFT, padx=5)

        # ===== SSH connection =====
        frm_ssh = ttk.LabelFrame(frm_conn, text="Linux Server SSH Connection", padding=10)
        frm_ssh.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(5,0))

        ttk.Label(frm_ssh, text="Host:").grid(row=0, column=0, sticky=tk.W)
        self.ssh_host = ttk.Entry(frm_ssh, width=18)
        self.ssh_host.grid(row=0, column=1, padx=5)
        self.ssh_host.insert(0, "192.168.1.100")

        ttk.Label(frm_ssh, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(10,0))
        self.ssh_port = ttk.Entry(frm_ssh, width=7)
        self.ssh_port.grid(row=0, column=3, padx=5)
        self.ssh_port.insert(0, "22")

        ttk.Label(frm_ssh, text="User:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.ssh_user = ttk.Entry(frm_ssh, width=18)
        self.ssh_user.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(frm_ssh, text="Password:").grid(row=1, column=2, sticky=tk.W, pady=5)
        self.ssh_pass = ttk.Entry(frm_ssh, width=18, show="*")
        self.ssh_pass.grid(row=1, column=3, padx=5, pady=5)

        btn_frame_ssh = ttk.Frame(frm_ssh)
        btn_frame_ssh.grid(row=2, column=0, columnspan=4, pady=10)
        self.btn_ssh_connect = ttk.Button(btn_frame_ssh, text="Connect", command=self.ssh_connect)
        self.btn_ssh_connect.pack(side=tk.LEFT, padx=5)
        self.btn_ssh_disconnect = ttk.Button(btn_frame_ssh, text="Disconnect", command=self.ssh_disconnect, state=tk.DISABLED)
        self.btn_ssh_disconnect.pack(side=tk.LEFT, padx=5)
        self.btn_oraenv = ttk.Button(btn_frame_ssh, text="Run . oraenv", command=self.run_oraenv, state=tk.DISABLED)
        self.btn_oraenv.pack(side=tk.LEFT, padx=10)
        self.ssh_status_var = tk.StringVar(value="Not connected")
        self.ssh_status_label = ttk.Label(btn_frame_ssh, textvariable=self.ssh_status_var, foreground="red")
        self.ssh_status_label.pack(side=tk.LEFT, padx=10)

        # ---------- Engines ----------
        self.engine = None    # DB1
        self.engine2 = None   # DB2
        self.ssh_client = None

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

        # ----- DB Objects Comparison tab -----
        self.tab_compare = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_compare, text="DB Objects Comparison")
        self._build_compare_tab()

        # Status bar
        self.status = tk.StringVar()
        self.status.set("Ready")
        ttk.Label(root, textvariable=self.status, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, padx=10, pady=2)

    # ====================== SQL Query Tab ======================
    def _build_query_tab(self):
        # Database selection for query
        frm_select = ttk.Frame(self.tab_query)
        frm_select.pack(fill=tk.X, pady=5)
        ttk.Label(frm_select, text="Query on:").pack(side=tk.LEFT, padx=5)
        self.query_db_choice = tk.StringVar(value="DB1")
        ttk.Combobox(frm_select, textvariable=self.query_db_choice,
                     values=["DB1", "DB2"], state="readonly", width=6).pack(side=tk.LEFT)

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

    # ====================== DataPump Tab ======================
    def _build_datapump_tab(self):
        # Outer frame with scrollbar
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
        frm_main.columnconfigure(0, weight=1)
        frm_main.columnconfigure(1, weight=1)
        frm_main.columnconfigure(2, weight=0)
        frm_main.columnconfigure(3, weight=0)
        frm_main.columnconfigure(4, weight=0)

        # ---------- Mode selection + Target DB ----------
        self.dp_mode = tk.StringVar(value="export")          # <--- FIX: added this line
        row = 0
        ttk.Radiobutton(frm_main, text="Export", variable=self.dp_mode, value="export").grid(row=row, column=0, sticky=tk.W)
        ttk.Radiobutton(frm_main, text="Import", variable=self.dp_mode, value="import").grid(row=row, column=1, sticky=tk.W, padx=20)
        ttk.Label(frm_main, text="Target DB:").grid(row=row, column=2, sticky=tk.W, padx=(20,5))
        self.dp_target_db = tk.StringVar(value="DB1")
        ttk.Combobox(frm_main, textvariable=self.dp_target_db,
                     values=["DB1", "DB2"], state="readonly", width=6).grid(row=row, column=3, pady=2)

        # ---------- Required parameters ----------
        row = 1
        ttk.Label(frm_main, text="Directory:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.dir_entry = ttk.Entry(frm_main, width=30)
        self.dir_entry.grid(row=row, column=1, columnspan=3, pady=2, padx=5, sticky=tk.W)
        self.dir_entry.insert(0, "DATA_PUMP")

        row += 1
        ttk.Label(frm_main, text="Dump file:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.dumpfile_entry = ttk.Entry(frm_main, width=30)
        self.dumpfile_entry.grid(row=row, column=1, columnspan=3, pady=2, padx=5, sticky=tk.W)
        self.dumpfile_entry.insert(0, "export.dmp")

        row += 1
        ttk.Label(frm_main, text="Log file:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.logfile_entry = ttk.Entry(frm_main, width=30)
        self.logfile_entry.grid(row=row, column=1, columnspan=3, pady=2, padx=5, sticky=tk.W)
        self.logfile_entry.insert(0, "export.log")

        # ---------- Optional parameters ----------
        row += 1
        ttk.Label(frm_main, text="Schemas:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.schemas_entry = ttk.Entry(frm_main, width=30)
        self.schemas_entry.grid(row=row, column=1, columnspan=3, pady=2, padx=5, sticky=tk.W)
        ttk.Label(frm_main, text="(comma separated)").grid(row=row, column=4, padx=5, sticky=tk.W)

        row += 1
        ttk.Label(frm_main, text="Tables:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.tables_entry = ttk.Entry(frm_main, width=30)
        self.tables_entry.grid(row=row, column=1, columnspan=3, pady=2, padx=5, sticky=tk.W)
        ttk.Label(frm_main, text="(schema.table, ...)").grid(row=row, column=4, padx=5, sticky=tk.W)

        # --- Remap Schema (import mode) – fixed alignment ---
        row += 1
        ttk.Label(frm_main, text="Remap Schema:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.remap_from = ttk.Entry(frm_main, width=15)
        self.remap_from.grid(row=row, column=1, pady=2, padx=(0,2), sticky=tk.W)
        ttk.Label(frm_main, text="From").grid(row=row, column=2, sticky=tk.W, padx=(0,2))
        self.remap_to = ttk.Entry(frm_main, width=15)
        self.remap_to.grid(row=row, column=3, pady=2, padx=(0,2), sticky=tk.W)
        ttk.Label(frm_main, text="To").grid(row=row, column=4, sticky=tk.W, padx=(0,5))

        row += 1
        ttk.Label(frm_main, text="Content:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.content_combo = ttk.Combobox(frm_main, values=["ALL", "DATA_ONLY", "METADATA_ONLY"], state="readonly", width=15)
        self.content_combo.grid(row=row, column=1, pady=2, padx=5, sticky=tk.W)
        self.content_combo.set("ALL")

        row += 1
        ttk.Label(frm_main, text="Parallel:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.parallel_spin = ttk.Spinbox(frm_main, from_=1, to=32, width=5)
        self.parallel_spin.grid(row=row, column=1, pady=2, padx=5, sticky=tk.W)
        self.parallel_spin.set(1)

        row += 1
        ttk.Label(frm_main, text="Compression:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.compression_combo = ttk.Combobox(frm_main, values=["NONE", "METADATA_ONLY", "DATA_ONLY", "ALL"], state="readonly", width=15)
        self.compression_combo.grid(row=row, column=1, pady=2, padx=5, sticky=tk.W)
        self.compression_combo.set("NONE")

        row += 1
        ttk.Label(frm_main, text="Extra params:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.extra_entry = ttk.Entry(frm_main, width=50)
        self.extra_entry.grid(row=row, column=1, columnspan=3, pady=2, padx=5, sticky=tk.W)

        # ---------- Command preview ----------
        row += 1
        ttk.Label(frm_main, text="Generated Command:", font=("", 9, "bold")).grid(row=row, column=0, columnspan=5, sticky=tk.W, pady=(10,0))
        row += 1
        self.cmd_text = scrolledtext.ScrolledText(frm_main, height=4, font=("Consolas", 9), state=tk.NORMAL)
        self.cmd_text.grid(row=row, column=0, columnspan=5, sticky="ew", pady=5)

        # ---------- Buttons ----------
        row += 1
        btn_gen = ttk.Button(frm_main, text="Generate Command", command=self.generate_datapump_cmd)
        btn_gen.grid(row=row, column=0, pady=5, sticky=tk.W)
        self.btn_run = ttk.Button(frm_main, text="Run", command=self.run_datapump)
        self.btn_run.grid(row=row, column=1, pady=5, padx=5, sticky=tk.W)
        self.btn_stop = ttk.Button(frm_main, text="Stop", command=self.stop_datapump, state=tk.DISABLED)
        self.btn_stop.grid(row=row, column=2, pady=5, padx=5, sticky=tk.W)

        # ---------- Output console ----------
        row += 1
        ttk.Label(frm_main, text="Output:", font=("", 9, "bold")).grid(row=row, column=0, columnspan=5, sticky=tk.W)
        row += 1
        self.output_text = scrolledtext.ScrolledText(frm_main, height=10, font=("Consolas", 9), state=tk.DISABLED)
        self.output_text.grid(row=row, column=0, columnspan=5, sticky="nsew", pady=5)

        row += 1
        btn_clear = ttk.Button(frm_main, text="Clear Output", command=self.clear_output)
        btn_clear.grid(row=row, column=0, pady=5, sticky=tk.W)

        # ========== FILE TRANSFER SECTION ==========
        row += 1
        frm_transfer = ttk.LabelFrame(frm_main, text="File Transfer", padding=10)
        frm_transfer.grid(row=row, column=0, columnspan=5, sticky="ew", pady=10)

        # Source server details (links to DB1 by default)
        ttk.Label(frm_transfer, text="Source Server SSH:").grid(row=0, column=0, columnspan=5, sticky=tk.W)

        ttk.Label(frm_transfer, text="Host:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.ssh_source_host = ttk.Entry(frm_transfer, width=18)
        self.ssh_source_host.grid(row=1, column=1, padx=5)
        self.ssh_source_host.insert(0, self.host.get())

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
        ttk.Button(frm_transfer, text="Auto-fill from DB1", command=self.autofill_source_path).grid(row=3, column=4, padx=5)

        # Destination server details (links to DB2)
        ttk.Label(frm_transfer, text="Destination Server SSH:").grid(row=4, column=0, columnspan=5, sticky=tk.W, pady=(10,0))

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
        ttk.Button(frm_transfer, text="Auto-fill from DB2", command=self.autofill_dest_path).grid(row=7, column=4, padx=5)

        self.transfer_btn = ttk.Button(frm_transfer, text="Transfer Files", command=self.transfer_files)
        self.transfer_btn.grid(row=8, column=0, columnspan=5, pady=10)

        # Configure grid weights
        frm_main.columnconfigure(1, weight=1)
        frm_main.rowconfigure(row, weight=1)
        frm_transfer.columnconfigure(1, weight=1)

        # ---------- Process management ----------
        self.dp_process = None
        self.dp_channel = None
        self.dp_queue = queue.Queue()
        self.dp_thread = None
        self.after_id = None

    # ====================== DB Objects Comparison Tab ======================
    def _build_compare_tab(self):
        frm_compare = ttk.LabelFrame(self.tab_compare, text="Object Comparison", padding=10)
        frm_compare.pack(fill=tk.BOTH, expand=True, pady=5)

        btn_run_compare = ttk.Button(frm_compare, text="Compare Objects", command=self.compare_objects)
        btn_run_compare.pack(pady=5, anchor=tk.W)

        self.compare_tree = ttk.Treeview(frm_compare, columns=("Type", "DB1 Count", "DB2 Count", "Missing in DB2"), show="headings")
        self.compare_tree.heading("Type", text="Object Type")
        self.compare_tree.heading("DB1 Count", text="DB1 Count")
        self.compare_tree.heading("DB2 Count", text="DB2 Count")
        self.compare_tree.heading("Missing in DB2", text="Missing in DB2 (names)")
        self.compare_tree.column("Type", width=120)
        self.compare_tree.column("DB1 Count", width=80)
        self.compare_tree.column("DB2 Count", width=80)
        self.compare_tree.column("Missing in DB2", width=400)
        self.compare_tree.pack(fill=tk.BOTH, expand=True)

    # ====================== Database Connections (green status) ======================
    def get_connection_string(self, host, port, service, user, password):
        return f"oracle+oracledb://{user}:{quote_plus(password)}@{host}:{port}/?service_name={service}"

    def connect_db(self):
        try:
            conn_str = self.get_connection_string(
                self.host.get().strip(), self.port.get().strip(),
                self.db_name.get().strip(), self.user.get().strip(),
                self.password.get()
            )
            self.engine = create_engine(conn_str)
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1 FROM DUAL"))
            self.db_status_var.set("Connected")
            self.db_status_label.config(foreground="green")
            self.btn_db_connect.config(state=tk.DISABLED)
            self.btn_db_disconnect.config(state=tk.NORMAL)
            self.status.set(f"DB1 connected to {self.db_name.get()}")
        except Exception as e:
            self.engine = None
            self.db_status_var.set("Connection failed")
            self.db_status_label.config(foreground="red")
            messagebox.showerror("Connection Error", str(e))

    def disconnect_db(self):
        if self.engine:
            self.engine.dispose()
        self.engine = None
        self.db_status_var.set("Not connected")
        self.db_status_label.config(foreground="red")
        self.btn_db_connect.config(state=tk.NORMAL)
        self.btn_db_disconnect.config(state=tk.DISABLED)
        self.status.set("DB1 disconnected")

    def connect_db2(self):
        try:
            conn_str = self.get_connection_string(
                self.host2.get().strip(), self.port2.get().strip(),
                self.db_name2.get().strip(), self.user2.get().strip(),
                self.password2.get()
            )
            self.engine2 = create_engine(conn_str)
            with self.engine2.connect() as conn:
                conn.execute(text("SELECT 1 FROM DUAL"))
            self.db2_status_var.set("Connected")
            self.db2_status_label.config(foreground="green")
            self.btn_db2_connect.config(state=tk.DISABLED)
            self.btn_db2_disconnect.config(state=tk.NORMAL)
            self.status.set(f"DB2 connected to {self.db_name2.get()}")
        except Exception as e:
            self.engine2 = None
            self.db2_status_var.set("Connection failed")
            self.db2_status_label.config(foreground="red")
            messagebox.showerror("DB2 Connection Error", str(e))

    def disconnect_db2(self):
        if self.engine2:
            self.engine2.dispose()
        self.engine2 = None
        self.db2_status_var.set("Not connected")
        self.db2_status_label.config(foreground="red")
        self.btn_db2_connect.config(state=tk.NORMAL)
        self.btn_db2_disconnect.config(state=tk.DISABLED)
        self.status.set("DB2 disconnected")

    # ====================== SSH Connection ======================
    def ssh_connect(self):
        host = self.ssh_host.get().strip()
        port = int(self.ssh_port.get().strip())
        user = self.ssh_user.get().strip()
        pw = self.ssh_pass.get()
        if not all([host, user, pw]):
            messagebox.showwarning("Missing SSH credentials", "Fill all SSH fields.")
            return
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(host, port=port, username=user, password=pw)
            self.ssh_status_var.set("Connected")
            self.ssh_status_label.config(foreground="green")
            self.btn_ssh_connect.config(state=tk.DISABLED)
            self.btn_ssh_disconnect.config(state=tk.NORMAL)
            self.btn_oraenv.config(state=tk.NORMAL)
            self.status.set(f"SSH connected to {host}")
        except Exception as e:
            self.ssh_client = None
            self.ssh_status_var.set("Connection failed")
            self.ssh_status_label.config(foreground="red")
            messagebox.showerror("SSH Error", str(e))

    def ssh_disconnect(self):
        if self.ssh_client:
            self.ssh_client.close()
        self.ssh_client = None
        self.ssh_status_var.set("Not connected")
        self.ssh_status_label.config(foreground="red")
        self.btn_ssh_connect.config(state=tk.NORMAL)
        self.btn_ssh_disconnect.config(state=tk.DISABLED)
        self.btn_oraenv.config(state=tk.DISABLED)
        self.status.set("SSH disconnected")

    # ====================== oraenv ======================
    def run_oraenv(self):
        if not self.ssh_client:
            messagebox.showwarning("SSH not connected", "Connect to the Linux server first.")
            return
        service_name = self.db_name.get().strip()
        if not service_name:
            messagebox.showwarning("Missing service name", "Enter the service name (used as ORACLE_SID).")
            return

        cmd = (
            f"export ORACLE_SID={service_name}; "
            "export ORAENV_ASK=NO; "
            ". /usr/local/bin/oraenv; "
            "echo '--- Environment after . oraenv ---'; "
            "echo ORACLE_HOME=$ORACLE_HOME; "
            "echo ORACLE_SID=$ORACLE_SID; "
            "echo PATH=$PATH"
        )
        self._run_remote_cmd(cmd, on_finish=lambda: None, tag=". oraenv")

    # ====================== Remote command execution ======================
    def _run_remote_cmd(self, cmd, on_finish=None, tag="Remote command"):
        if not self.ssh_client:
            self._log_now(f"SSH not connected – cannot run: {tag}")
            return

        self._clear_output()
        self.btn_run.config(state=tk.DISABLED)
        self.btn_oraenv.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)

        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
            self.dp_channel = stdout.channel
            self.dp_process = None

            self.dp_queue = queue.Queue()
            self.dp_thread_stdout = threading.Thread(target=self._read_stream, args=(stdout,), daemon=True)
            self.dp_thread_stderr = threading.Thread(target=self._read_stream, args=(stderr,), daemon=True)
            self.dp_thread_stdout.start()
            self.dp_thread_stderr.start()

            self.after_id = self.root.after(100, self._check_ssh_status, on_finish)
        except Exception as e:
            self._log_now(f"Failed to execute remote command: {e}")
            self._on_remote_finished(on_finish)

    def _read_stream(self, stream):
        try:
            for line in iter(stream.readline, ''):
                if line:
                    self.dp_queue.put(line)
        except Exception:
            pass
        finally:
            stream.close()

    def _check_ssh_status(self, on_finish):
        try:
            while True:
                line = self.dp_queue.get_nowait()
                if line is not None:
                    self._log_now(line.rstrip())
        except queue.Empty:
            pass

        if self.dp_channel and not self.dp_channel.closed:
            self.after_id = self.root.after(100, self._check_ssh_status, on_finish)
        else:
            try:
                while True:
                    line = self.dp_queue.get_nowait()
                    if line:
                        self._log_now(line.rstrip())
            except queue.Empty:
                pass
            self._on_remote_finished(on_finish)

    def _on_remote_finished(self, on_finish):
        self.btn_run.config(state=tk.NORMAL)
        self.btn_oraenv.config(state=tk.NORMAL if self.ssh_client else tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)
        self.dp_channel = None
        if on_finish:
            on_finish()
        self.status.set("Remote command completed")

    def stop_datapump(self):
        if self.dp_process and self.dp_process.poll() is None:
            self.dp_process.terminate()
            try:
                self.dp_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.dp_process.kill()
            self._log_now("\n*** Process terminated by user ***\n")
            self._on_process_finished()
        elif self.dp_channel and not self.dp_channel.closed:
            self.dp_channel.close()
            self._log_now("\n*** Remote process terminated by user ***\n")
            self._on_remote_finished(on_finish=None)
        else:
            messagebox.showinfo("Nothing to stop", "No active process.")

    # ====================== DataPump Command with target DB ======================
    def _get_target_db_fields(self):
        """Return (user, password, host, port, service) for the selected DataPump target."""
        if self.dp_target_db.get() == "DB2":
            return (self.user2.get().strip(), self.password2.get(),
                    self.host2.get().strip(), self.port2.get().strip(),
                    self.db_name2.get().strip())
        else:
            return (self.user.get().strip(), self.password.get(),
                    self.host.get().strip(), self.port.get().strip(),
                    self.db_name.get().strip())

    def generate_datapump_cmd(self):
        try:
            conn_user, conn_pw, conn_host, conn_port, conn_service = self._get_target_db_fields()
            if not all([conn_user, conn_pw, conn_host, conn_port, conn_service]):
                messagebox.showwarning("Missing connection", "Fill in all fields for the selected target DB.")
                return

            date_str = datetime.now().strftime("%d%m%y")

            if self.dp_mode.get() == "export":
                schemas_text = self.schemas_entry.get().strip()
                if schemas_text:
                    first_schema = schemas_text.split(",")[0].strip()
                    if first_schema:
                        if self.dumpfile_entry.get().strip() in ("export.dmp", ""):
                            self.dumpfile_entry.delete(0, tk.END)
                            self.dumpfile_entry.insert(0, f"{first_schema}_{date_str}.dmp")
                        if self.logfile_entry.get().strip() in ("export.log", ""):
                            self.logfile_entry.delete(0, tk.END)
                            self.logfile_entry.insert(0, f"{first_schema}_{date_str}.log")
            else:
                self.logfile_entry.delete(0, tk.END)
                self.logfile_entry.insert(0, f"{conn_user}_{date_str}.log")

            connect_str = f"{conn_user}/{conn_pw}"

            if self.dp_mode.get() == "export":
                cmd_parts = ["expdp", connect_str]
            else:
                cmd_parts = ["impdp", connect_str]

            dp_dir = self.dir_entry.get().strip()
            if dp_dir:
                cmd_parts.append(f"directory={dp_dir}")
            dumpfile = self.dumpfile_entry.get().strip()
            if dumpfile:
                cmd_parts.append(f"dumpfile={dumpfile}")
            logfile = self.logfile_entry.get().strip()
            if logfile:
                cmd_parts.append(f"logfile={logfile}")
            schemas = self.schemas_entry.get().strip()
            if schemas:
                cmd_parts.append(f"schemas={schemas.replace(' ', '')}")
            tables = self.tables_entry.get().strip()
            if tables:
                cmd_parts.append(f"tables={tables.replace(' ', '')}")

            if self.dp_mode.get() == "import":
                remap_from = self.remap_from.get().strip()
                remap_to = self.remap_to.get().strip()
                if remap_from and remap_to:
                    cmd_parts.append(f"remap_schema={remap_from}:{remap_to}")

            content = self.content_combo.get()
            if content != "ALL":
                cmd_parts.append(f"content={content}")
            parallel = self.parallel_spin.get()
            if parallel != "1":
                cmd_parts.append(f"parallel={parallel}")
            compression = self.compression_combo.get()
            if compression != "NONE":
                cmd_parts.append(f"compression={compression}")
            extra = self.extra_entry.get().strip()
            if extra:
                cmd_parts.extend(extra.split())

            cmd_str = subprocess.list2cmdline(cmd_parts)
            self.cmd_text.config(state=tk.NORMAL)
            self.cmd_text.delete("1.0", tk.END)
            self.cmd_text.insert(tk.END, cmd_str)
            self.cmd_text.config(state=tk.NORMAL)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate command: {e}")

    # ====================== Run DataPump ======================
    def run_datapump(self):
        cmd_str = self.cmd_text.get("1.0", tk.END).strip()
        if not cmd_str:
            messagebox.showwarning("No command", "Generate a command first.")
            return

        self.btn_run.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        if self.ssh_client:
            # Use the target DB's service name for the environment
            _, _, _, _, conn_service = self._get_target_db_fields()
            env_prefix = f"export ORACLE_SID={conn_service}; export ORAENV_ASK=NO; . /usr/local/bin/oraenv; "
            full_remote_cmd = env_prefix + cmd_str

            self._run_remote_cmd(full_remote_cmd,
                                 on_finish=self._on_datapump_finish,
                                 tag="DataPump")
        else:
            self._clear_output()
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
            self.dp_thread = threading.Thread(target=self._read_local_output, args=(self.dp_process.stdout,), daemon=True)
            self.dp_thread.start()
            self.after_id = self.root.after(100, self._process_local_output)

    def _read_local_output(self, stream):
        try:
            for line in iter(stream.readline, ''):
                self.dp_queue.put(line)
            stream.close()
        except Exception:
            pass
        finally:
            self.dp_queue.put(None)

    def _process_local_output(self):
        try:
            while True:
                line = self.dp_queue.get_nowait()
                if line is None:
                    self._on_process_finished()
                    return
                self._log_now(line.rstrip())
        except queue.Empty:
            pass
        self.after_id = self.root.after(100, self._process_local_output)

    def _on_process_finished(self):
        self.btn_run.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.dp_process = None
        self.status.set("DataPump job completed")

    def _on_datapump_finish(self):
        self.btn_run.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.status.set("DataPump job completed")

    # ====================== Output Utilities ======================
    def _clear_output(self):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.config(state=tk.DISABLED)

    def clear_output(self):
        self._clear_output()

    def _log_now(self, message):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)

    # ====================== SQL Query (select DB1/DB2) ======================
    def run_query(self):
        if self.query_db_choice.get() == "DB2":
            engine = self.engine2
        else:
            engine = self.engine

        if engine is None:
            db_label = self.query_db_choice.get()
            messagebox.showwarning("Not connected", f"Please connect to {db_label} first.")
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
                    self.status.set(f"Query returned {result.rowcount} rows.")
                else:
                    conn.commit()
                    self.status.set(f"Query executed. Rows affected: {result.rowcount}")
                    messagebox.showinfo("Done", f"Rows affected: {result.rowcount}")
        except SQLAlchemyError as e:
            messagebox.showerror("Query Error", str(e))
            self.status.set("Query error")

    # ====================== File Transfer (direct) ======================
    def autofill_source_path(self):
        if self.engine is None:
            messagebox.showwarning("Not connected", "Connect to DB1 first.")
            return
        dp_directory = self.dir_entry.get().strip()
        if not dp_directory:
            messagebox.showwarning("Missing directory", "Enter the DataPump directory name.")
            return

        query = "SELECT directory_path FROM dba_directories WHERE directory_name = :dir"
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), {"dir": dp_directory.upper()})
                row = result.fetchone()
                if row is None:
                    messagebox.showwarning("Not found", f"Directory '{dp_directory}' not found in DB1.")
                    return
                os_path = row[0]
                self.source_path.delete(0, tk.END)
                self.source_path.insert(0, os_path)
                self._log_now(f"Found source path for directory {dp_directory}: {os_path}")
        except Exception as e:
            messagebox.showerror("Query error", str(e))

    def autofill_dest_path(self):
        if self.engine2 is None:
            messagebox.showwarning("Not connected", "Connect to DB2 first.")
            return
        dp_directory = self.dir_entry.get().strip()
        if not dp_directory:
            messagebox.showwarning("Missing directory", "Enter the DataPump directory name.")
            return

        query = "SELECT directory_path FROM dba_directories WHERE directory_name = :dir"
        try:
            with self.engine2.connect() as conn:
                result = conn.execute(text(query), {"dir": dp_directory.upper()})
                row = result.fetchone()
                if row is None:
                    messagebox.showwarning("Not found", f"Directory '{dp_directory}' not found in DB2.")
                    return
                os_path = row[0]
                self.dest_path.delete(0, tk.END)
                self.dest_path.insert(0, os_path)
                self._log_now(f"Found dest path for directory {dp_directory}: {os_path}")
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
        self._log_now("=== Starting direct server‑to‑server file transfer ===")

        def worker():
            src_ssh = None
            dst_ssh = None
            try:
                files = [f for f in (dumpfile, logfile) if f]

                self._log_now("Connecting to source server...")
                src_ssh = paramiko.SSHClient()
                src_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                src_ssh.connect(src_host, port=src_port, username=src_user, password=src_pass)
                src_sftp = src_ssh.open_sftp()

                self._log_now("Connecting to destination server...")
                dst_ssh = paramiko.SSHClient()
                dst_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                dst_ssh.connect(dst_host, port=dst_port, username=dst_user, password=dst_pass)
                dst_sftp = dst_ssh.open_sftp()

                for f in files:
                    remote_src = os.path.join(source_dir, f).replace("\\", "/")
                    remote_dst = os.path.join(dest_dir, f).replace("\\", "/")
                    self._log_now(f"Transferring {remote_src} -> {remote_dst} (direct stream)")

                    with io.BytesIO() as buffer:
                        src_sftp.getfo(remote_src, buffer)
                        buffer.seek(0)
                        dst_sftp.putfo(buffer, remote_dst)

                src_sftp.close()
                dst_sftp.close()
                self._log_now("Direct transfer completed successfully.")

            except Exception as e:
                self._log_now(f"Transfer failed: {e}")
            finally:
                if src_ssh: src_ssh.close()
                if dst_ssh: dst_ssh.close()
                self.root.after(0, lambda: self.transfer_btn.config(state=tk.NORMAL))

        threading.Thread(target=worker, daemon=True).start()

    # ====================== Database Objects Comparison ======================
    def compare_objects(self):
        if self.engine is None or self.engine2 is None:
            messagebox.showwarning("Not connected", "Both DB1 and DB2 must be connected.")
            return

        for row in self.compare_tree.get_children():
            self.compare_tree.delete(row)

        object_types = [
            "FUNCTION", "INDEX", "LOB", "PACKAGE", "PACKAGE BODY",
            "PROCEDURE", "SEQUENCE", "SYNONYM", "TABLE", "TRIGGER"
        ]

        def get_objects(engine, obj_type):
            try:
                with engine.connect() as conn:
                    result = conn.execute(
                        text("SELECT object_name FROM user_objects WHERE object_type = :t"),
                        {"t": obj_type}
                    )
                    names = {row[0] for row in result}
                    return names, len(names)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Query Error", f"Error querying {obj_type}: {e}"))
                return None, 0

        self.status.set("Comparing objects...")

        def compare_thread():
            for obj_type in object_types:
                names1, count1 = get_objects(self.engine, obj_type)
                if names1 is None:
                    continue
                names2, count2 = get_objects(self.engine2, obj_type)
                if names2 is None:
                    continue
                missing_in_db2 = sorted(names1 - names2)
                missing_str = ", ".join(missing_in_db2) if missing_in_db2 else "None"

                self.root.after(0, lambda t=obj_type, c1=count1, c2=count2, m=missing_str:
                    self.compare_tree.insert("", tk.END, values=(t, c1, c2, m))
                )
            self.root.after(0, lambda: self.status.set("Comparison completed."))

        threading.Thread(target=compare_thread, daemon=True).start()

    def on_closing(self):
        if self.dp_process and self.dp_process.poll() is None:
            self.dp_process.terminate()
        if self.dp_channel and not self.dp_channel.closed:
            self.dp_channel.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = DbClientApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()