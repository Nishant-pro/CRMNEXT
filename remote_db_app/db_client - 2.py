import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import subprocess
import queue
import sys
import os
import tempfile
import paramiko
from datetime import datetime                     # NEW: for date stamp
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

class DbClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Remote DB Client - Oracle Automation")
        self.root.geometry("950x850")

        # ---------- Top frame: Connection (shared) ----------
        frm_conn = ttk.LabelFrame(root, text="Connection", padding=10)
        frm_conn.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frm_conn, text="DB Type:").grid(row=0, column=0, sticky=tk.W)
        self.db_type = ttk.Combobox(frm_conn, values=["postgresql", "mysql", "oracle"], state="readonly", width=12)
        self.db_type.grid(row=0, column=1, padx=5)
        self.db_type.set("oracle")

        ttk.Label(frm_conn, text="Host:").grid(row=0, column=2, sticky=tk.W, padx=(20,0))
        self.host = ttk.Entry(frm_conn, width=18)
        self.host.grid(row=0, column=3, padx=5)
        self.host.insert(0, "localhost")

        ttk.Label(frm_conn, text="Port:").grid(row=0, column=4, sticky=tk.W, padx=(10,0))
        self.port = ttk.Entry(frm_conn, width=7)
        self.port.grid(row=0, column=5, padx=5)
        self.port.insert(0, "1521")

        ttk.Label(frm_conn, text="Service Name:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.db_name = ttk.Entry(frm_conn, width=18)
        self.db_name.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(frm_conn, text="User:").grid(row=1, column=2, sticky=tk.W, pady=5)
        self.user = ttk.Entry(frm_conn, width=18)
        self.user.grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(frm_conn, text="Password:").grid(row=1, column=4, sticky=tk.W, pady=5)
        self.password = ttk.Entry(frm_conn, width=18, show="*")
        self.password.grid(row=1, column=5, padx=5, pady=5)

        self.btn_connect = ttk.Button(frm_conn, text="Connect", command=self.connect_db)
        self.btn_connect.grid(row=2, column=0, columnspan=6, pady=10)

        self.engine = None

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

        # ---------- Mode selection ----------
        self.dp_mode = tk.StringVar(value="export")
        ttk.Radiobutton(frm_main, text="Export", variable=self.dp_mode, value="export").grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(frm_main, text="Import", variable=self.dp_mode, value="import").grid(row=0, column=1, sticky=tk.W, padx=20)

        # ---------- Required parameters ----------
        row = 1
        ttk.Label(frm_main, text="Directory:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.dir_entry = ttk.Entry(frm_main, width=30)
        self.dir_entry.grid(row=row, column=1, pady=2, padx=5, sticky=tk.W)
        self.dir_entry.insert(0, "DATA_PUMP")

        row += 1
        ttk.Label(frm_main, text="Dump file:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.dumpfile_entry = ttk.Entry(frm_main, width=30)
        self.dumpfile_entry.grid(row=row, column=1, pady=2, padx=5, sticky=tk.W)
        self.dumpfile_entry.insert(0, "export.dmp")          # placeholder, will be overwritten

        row += 1
        ttk.Label(frm_main, text="Log file:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.logfile_entry = ttk.Entry(frm_main, width=30)
        self.logfile_entry.grid(row=row, column=1, pady=2, padx=5, sticky=tk.W)
        self.logfile_entry.insert(0, "export.log")            # placeholder

        # ---------- Optional parameters ----------
        row += 1
        ttk.Label(frm_main, text="Schemas:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.schemas_entry = ttk.Entry(frm_main, width=30)
        self.schemas_entry.grid(row=row, column=1, pady=2, padx=5, sticky=tk.W)
        ttk.Label(frm_main, text="(comma separated)").grid(row=row, column=2, padx=5, sticky=tk.W)

        row += 1
        ttk.Label(frm_main, text="Tables:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.tables_entry = ttk.Entry(frm_main, width=30)
        self.tables_entry.grid(row=row, column=1, pady=2, padx=5, sticky=tk.W)
        ttk.Label(frm_main, text="(schema.table, ...)").grid(row=row, column=2, padx=5, sticky=tk.W)

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
        self.extra_entry.grid(row=row, column=1, columnspan=2, pady=2, padx=5, sticky=tk.W)

        # ---------- Command preview ----------
        row += 1
        ttk.Label(frm_main, text="Generated Command:", font=("", 9, "bold")).grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(10,0))
        row += 1
        self.cmd_text = scrolledtext.ScrolledText(frm_main, height=4, font=("Consolas", 9), state=tk.NORMAL)
        self.cmd_text.grid(row=row, column=0, columnspan=3, sticky="ew", pady=5)

        # ---------- Buttons ----------
        row += 1
        btn_gen = ttk.Button(frm_main, text="Generate Command", command=self.generate_datapump_cmd)
        btn_gen.grid(row=row, column=0, pady=5, sticky=tk.W)
        self.btn_run = ttk.Button(frm_main, text="Run", command=self.run_datapump)
        self.btn_run.grid(row=row, column=1, pady=5, padx=5, sticky=tk.W)
        self.btn_stop = ttk.Button(frm_main, text="Stop", command=self.stop_datapump, state=tk.DISABLED)
        self.btn_stop.grid(row=row, column=2, pady=5, padx=5, sticky=tk.W)

        # ---------- Output console (with clear button) ----------
        row += 1
        ttk.Label(frm_main, text="Output:", font=("", 9, "bold")).grid(row=row, column=0, columnspan=3, sticky=tk.W)
        row += 1
        self.output_text = scrolledtext.ScrolledText(frm_main, height=10, font=("Consolas", 9), state=tk.DISABLED)
        self.output_text.grid(row=row, column=0, columnspan=3, sticky="nsew", pady=5)

        row += 1
        btn_clear = ttk.Button(frm_main, text="Clear Output", command=self.clear_output)
        btn_clear.grid(row=row, column=0, pady=5, sticky=tk.W)

        # ========== FILE TRANSFER SECTION ==========
        row += 1
        frm_transfer = ttk.LabelFrame(frm_main, text="File Transfer", padding=10)
        frm_transfer.grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)

        # Source server details
        ttk.Label(frm_transfer, text="Source (DB Server) SSH:").grid(row=0, column=0, columnspan=4, sticky=tk.W)

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
        ttk.Button(frm_transfer, text="Auto-fill", command=self.autofill_source_path).grid(row=3, column=4, padx=5)

        # Destination server details
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

        # ---------- Process management (DataPump) ----------
        self.dp_process = None
        self.dp_queue = queue.Queue()
        self.dp_thread = None
        self.after_id = None

    # ============= Connection & Query (unchanged / adapted) =============
    def get_connection_string(self):
        db_type = self.db_type.get().strip()
        host = self.host.get().strip()
        port = self.port.get().strip()
        db = self.db_name.get().strip()
        user = self.user.get().strip()
        pw = self.password.get()
        if not all([host, port, db, user]):
            raise ValueError("Host, port, service name, and user are required.")

        if db_type.lower() == "oracle":
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
            with self.engine.connect() as conn:
                if self.db_type.get().strip().lower() == "oracle":
                    conn.execute(text("SELECT 1 FROM DUAL"))
                else:
                    conn.execute(text("SELECT 1"))
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
        sql = self.query_text.get("1.0", tk.END).strip().rstrip(';').strip()
        if not sql:
            messagebox.showwarning("Empty query", "Please enter a SQL query.")
            return
        try:
            with self.engine.connect() as conn:
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

    # ======================== DataPump Logic ========================
    def generate_datapump_cmd(self):
        """Build the expdp/impdp command, auto‑setting dump/log filenames if exporting with a schema."""
        try:
            conn_user = self.user.get().strip()
            conn_pw = self.password.get()
            conn_host = self.host.get().strip()
            conn_port = self.port.get().strip()
            conn_service = self.db_name.get().strip()
            if not all([conn_user, conn_pw, conn_host, conn_port, conn_service]):
                messagebox.showwarning("Missing connection", "Fill in all connection fields first.")
                return

            # ---- AUTO‑SET FILENAMES FOR EXPORT ----
            if self.dp_mode.get() == "export":
                schemas_text = self.schemas_entry.get().strip()
                if schemas_text:
                    # use first schema name (split comma)
                    first_schema = schemas_text.split(",")[0].strip()
                    if first_schema:
                        date_str = datetime.now().strftime("%d%m%y")   # DDMMYY
                        # Only overwrite if the fields still show the original placeholder
                        if self.dumpfile_entry.get().strip() in ("export.dmp", ""):
                            self.dumpfile_entry.delete(0, tk.END)
                            self.dumpfile_entry.insert(0, f"{first_schema}_{date_str}.dmp")
                        if self.logfile_entry.get().strip() in ("export.log", ""):
                            self.logfile_entry.delete(0, tk.END)
                            self.logfile_entry.insert(0, f"{first_schema}_{date_str}.log")

            connect_str = f"{conn_user}/{conn_pw}@//{conn_host}:{conn_port}/{conn_service}"

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
        """Clear the output text widget."""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.config(state=tk.DISABLED)

    # ======================== File Transfer Logic ========================
    def autofill_source_path(self):
        """
        Query the database to get the physical path of the DataPump directory
        specified in the 'Directory' field and fill the Source Path entry.
        """
        if self.engine is None:
            messagebox.showwarning("Not connected", "Connect to the database first.")
            return

        dp_directory = self.dir_entry.get().strip()
        if not dp_directory:
            messagebox.showwarning("Missing directory", "Enter the DataPump directory name first.")
            return

        # Query must be compatible with Oracle / PostgreSQL / MySQL.
        # Since we're focused on Oracle, we assume Oracle. For others, fallback.
        db_type = self.db_type.get().strip().lower()
        query = ""
        if db_type == "oracle":
            query = "SELECT directory_path FROM dba_directories WHERE directory_name = :dir"
        elif db_type == "postgresql":
            # PostgreSQL doesn't have directory objects; show error
            messagebox.showwarning("Not supported", "Auto‑fill works only for Oracle databases.")
            return
        elif db_type == "mysql":
            messagebox.showwarning("Not supported", "Auto‑fill works only for Oracle databases.")
            return
        else:
            messagebox.showwarning("Unknown DB type", "Unsupported database type.")
            return

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), {"dir": dp_directory.upper()})
                row = result.fetchone()
                if row is None:
                    messagebox.showwarning("Not found", f"Directory '{dp_directory}' not found in dba_directories.")
                    return
                os_path = row[0]
                self.source_path.delete(0, tk.END)
                self.source_path.insert(0, os_path)
                self._log(f"Found path for directory {dp_directory}: {os_path}")
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
            messagebox.showwarning("Missing SSH credentials", "Fill all SSH fields (both source and destination).")
            return

        self.transfer_btn.config(state=tk.DISABLED)
        self._log("=== Starting file transfer ===")

        def worker():
            try:
                files = [f for f in (dumpfile, logfile) if f]
                temp_dir = tempfile.mkdtemp()
                local_files = []

                self._log("Connecting to source server...")
                src_ssh = paramiko.SSHClient()
                src_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                src_ssh.connect(src_host, port=src_port, username=src_user, password=src_pass)

                for f in files:
                    remote_path = os.path.join(source_dir, f).replace("\\", "/")
                    local_path = os.path.join(temp_dir, f)
                    self._log(f"Downloading {remote_path} -> {local_path}")
                    sftp = src_ssh.open_sftp()
                    sftp.get(remote_path, local_path)
                    sftp.close()
                    local_files.append(local_path)
                src_ssh.close()

                self._log("Connecting to destination server...")
                dst_ssh = paramiko.SSHClient()
                dst_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                dst_ssh.connect(dst_host, port=dst_port, username=dst_user, password=dst_pass)

                for f, local in zip(files, local_files):
                    remote_path = os.path.join(dest_dir, f).replace("\\", "/")
                    self._log(f"Uploading {local} -> {remote_path}")
                    sftp = dst_ssh.open_sftp()
                    sftp.put(local, remote_path)
                    sftp.close()
                dst_ssh.close()

                for local in local_files:
                    os.remove(local)
                os.rmdir(temp_dir)

                self._log("Transfer completed successfully.")

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