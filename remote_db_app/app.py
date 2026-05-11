# app.py - Streamlit web version (mirrors local Tkinter app behaviour)
import streamlit as st
import threading
import subprocess
import io
import os
import time
import paramiko
from datetime import datetime
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
import pandas as pd

# Page config
st.set_page_config(
    page_title="Remote DB Client - Oracle Automation",
    page_icon="🔧",
    layout="wide"
)

# ---------- Session state initialisation ----------
def init_session():
    if 'db1_connected' not in st.session_state:
        st.session_state.db1_connected = False
        st.session_state.engine = None
    if 'db2_connected' not in st.session_state:
        st.session_state.db2_connected = False
        st.session_state.engine2 = None
    if 'ssh_connected' not in st.session_state:
        st.session_state.ssh_connected = False
        st.session_state.ssh_client = None
    if 'dp_output' not in st.session_state:
        st.session_state.dp_output = []
    if 'transfer_logs' not in st.session_state:
        st.session_state.transfer_logs = []
    if 'compare_results' not in st.session_state:
        st.session_state.compare_results = None
    if 'dp_running' not in st.session_state:
        st.session_state.dp_running = False
    if 'dp_stop' not in st.session_state:
        st.session_state.dp_stop = False

init_session()

st.title("🔧 Remote DB Client - Oracle Automation")

# Sidebar – Connections
with st.sidebar:
    st.header("🔌 Connections")

    # Database 1
    st.subheader("Database 1 (Source)")
    host1_val = st.text_input("Host", value="localhost", key="host1")
    port1_val = st.text_input("Port", value="1521", key="port1")
    service1_val = st.text_input("Service Name", key="service1")
    user1_val = st.text_input("User", key="user1")
    pass1_val = st.text_input("Password", type="password", key="pass1")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Connect DB1", use_container_width=True):
            try:
                conn_str = f"oracle+oracledb://{user1_val}:{quote_plus(pass1_val)}@{host1_val}:{port1_val}/?service_name={service1_val}"
                eng = create_engine(conn_str)
                with eng.connect() as conn:
                    conn.execute(text("SELECT 1 FROM DUAL"))
                st.session_state.engine = eng
                st.session_state.db1_connected = True
                st.success("DB1 Connected!")
            except Exception as e:
                st.session_state.db1_connected = False
                st.session_state.engine = None
                st.error(f"Connection failed: {e}")

    with col2:
        if st.button("Disconnect DB1", use_container_width=True):
            if st.session_state.engine:
                st.session_state.engine.dispose()
            st.session_state.engine = None
            st.session_state.db1_connected = False

    st.markdown("✅ **DB1:** " + ("Connected" if st.session_state.db1_connected else "Not Connected"))

    st.divider()

    # Database 2
    st.subheader("Database 2 (Target)")
    host2_val = st.text_input("Host", key="host2")
    port2_val = st.text_input("Port", value="1521", key="port2")
    service2_val = st.text_input("Service Name", key="service2")
    user2_val = st.text_input("User", key="user2")
    pass2_val = st.text_input("Password", type="password", key="pass2")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Connect DB2", use_container_width=True):
            try:
                conn_str = f"oracle+oracledb://{user2_val}:{quote_plus(pass2_val)}@{host2_val}:{port2_val}/?service_name={service2_val}"
                eng = create_engine(conn_str)
                with eng.connect() as conn:
                    conn.execute(text("SELECT 1 FROM DUAL"))
                st.session_state.engine2 = eng
                st.session_state.db2_connected = True
                st.success("DB2 Connected!")
            except Exception as e:
                st.session_state.db2_connected = False
                st.session_state.engine2 = None
                st.error(f"Connection failed: {e}")

    with col2:
        if st.button("Disconnect DB2", use_container_width=True):
            if st.session_state.engine2:
                st.session_state.engine2.dispose()
            st.session_state.engine2 = None
            st.session_state.db2_connected = False

    st.markdown("✅ **DB2:** " + ("Connected" if st.session_state.db2_connected else "Not Connected"))

    st.divider()

    # SSH
    st.subheader("SSH Connection")
    ssh_host_val = st.text_input("SSH Host", value="192.168.1.100", key="ssh_host")
    ssh_port_val = st.text_input("SSH Port", value="22", key="ssh_port")
    ssh_user_val = st.text_input("SSH User", key="ssh_user")
    ssh_pass_val = st.text_input("SSH Password", type="password", key="ssh_pass")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Connect SSH", use_container_width=True):
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(ssh_host_val, port=int(ssh_port_val), username=ssh_user_val, password=ssh_pass_val)
                st.session_state.ssh_client = client
                st.session_state.ssh_connected = True
                st.success("SSH Connected!")
            except Exception as e:
                st.session_state.ssh_connected = False
                st.session_state.ssh_client = None
                st.error(f"SSH failed: {e}")

    with col2:
        if st.button("Disconnect SSH", use_container_width=True):
            if st.session_state.ssh_client:
                st.session_state.ssh_client.close()
            st.session_state.ssh_client = None
            st.session_state.ssh_connected = False

    st.markdown("✅ **SSH:** " + ("Connected" if st.session_state.ssh_connected else "Not Connected"))

# Main tabs
tab1, tab2, tab3 = st.tabs(["📦 DataPump", "📁 File Transfer", "📊 Compare Objects"])

# ---------------------- DataPump Tab (real-time streaming) ----------------------
with tab1:
    st.header("DataPump Export/Import")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        mode = st.radio("Mode", ["Export", "Import"], horizontal=True, key="dp_mode")
        dumpfile = st.text_input("Dump File", value="export.dmp", key="dp_dumpfile")
        logfile = st.text_input("Log File", value="export.log", key="dp_logfile")
        schemas = st.text_input("Schemas (comma separated)", key="dp_schemas")
        tables = st.text_input("Tables (schema.table format)", key="dp_tables")

        if mode == "Import":
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                remap_from = st.text_input("Remap From Schema", key="remap_from")
            with col_r2:
                remap_to = st.text_input("Remap To Schema", key="remap_to")
        else:
            remap_from = remap_to = ""

        content = st.selectbox("Content", ["ALL", "DATA_ONLY", "METADATA_ONLY"], key="dp_content")
        parallel = st.number_input("Parallel", min_value=1, max_value=32, value=1, key="dp_parallel")
        compression = st.selectbox("Compression", ["NONE", "METADATA_ONLY", "DATA_ONLY", "ALL"], key="dp_compression")
        extra_params = st.text_input("Extra Parameters", key="dp_extra")

        if not st.session_state.dp_running:
            if st.button("Generate & Run DataPump", type="primary", use_container_width=True):
                target_engine = st.session_state.engine if mode == "Export" else st.session_state.engine2
                if not target_engine:
                    st.error(f"Connect to {'DB1' if mode == 'Export' else 'DB2'} first!")
                else:
                    st.session_state.dp_output = []   # clear previous
                    st.session_state.dp_stop = False
                    # Build command
                    cmd_parts = [
                        "expdp" if mode == "Export" else "impdp",
                        f"{user1_val if mode == 'Export' else user2_val}/<password>"
                    ]
                    cmd_parts.append("directory=DATA_PUMP")
                    cmd_parts.append(f"dumpfile={dumpfile}")
                    cmd_parts.append(f"logfile={logfile}")
                    if schemas:
                        cmd_parts.append(f"schemas={schemas.replace(' ', '')}")
                    if tables:
                        cmd_parts.append(f"tables={tables.replace(' ', '')}")
                    if mode == "Import" and remap_from and remap_to:
                        cmd_parts.append(f"remap_schema={remap_from}:{remap_to}")
                    if content != "ALL":
                        cmd_parts.append(f"content={content}")
                    if parallel > 1:
                        cmd_parts.append(f"parallel={parallel}")
                    if compression != "NONE":
                        cmd_parts.append(f"compression={compression}")
                    if extra_params:
                        cmd_parts.append(extra_params)

                    full_cmd = subprocess.list2cmdline(cmd_parts)
                    st.session_state.dp_output.append(f"$ {full_cmd}\n")

                    if st.session_state.ssh_connected and st.session_state.ssh_client:
                        # Remote execution via SSH
                        service = service1_val if mode == "Export" else service2_val
                        env_cmd = f"export ORACLE_SID={service}; export ORAENV_ASK=NO; . /usr/local/bin/oraenv; {full_cmd}"

                        def ssh_exec_thread():
                            client = st.session_state.ssh_client
                            try:
                                stdin, stdout, stderr = client.exec_command(env_cmd, get_pty=True)
                                # Read stdout line by line in a non-blocking way
                                for line in iter(stdout.readline, ""):
                                    if st.session_state.dp_stop:
                                        stdin.write("\x03")   # send Ctrl+C
                                        break
                                    st.session_state.dp_output.append(line.rstrip())
                                # Check for errors
                                for line in iter(stderr.readline, ""):
                                    st.session_state.dp_output.append(f"[STDERR] {line.rstrip()}")
                                st.session_state.dp_output.append("✅ DataPump finished.")
                            except Exception as e:
                                st.session_state.dp_output.append(f"SSH error: {e}")
                            finally:
                                st.session_state.dp_running = False

                        st.session_state.dp_running = True
                        threading.Thread(target=ssh_exec_thread, daemon=True).start()
                        st.info("DataPump started. Output will appear below...")
                    else:
                        st.error("SSH not connected. For remote execution, connect to the Linux server first.")
        else:
            if st.button("Stop DataPump", type="secondary"):
                st.session_state.dp_stop = True

    with col_right:
        st.subheader("Output")
        # Real-time display of output
        output_placeholder = st.empty()
        if st.session_state.dp_output:
            output_placeholder.code("\n".join(st.session_state.dp_output), language="bash")
        if st.button("Clear Output"):
            st.session_state.dp_output = []

# ---------------------- File Transfer Tab (like local app) ----------------------
with tab2:
    st.header("File Transfer")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Source (uses Linux SSH)")
        source_path = st.text_input("Source Directory Path", key="source_path")
        if st.button("Auto-fill from DB1", key="auto_source"):
            if st.session_state.engine:
                try:
                    with st.session_state.engine.connect() as conn:
                        result = conn.execute(text("SELECT directory_path FROM dba_directories WHERE directory_name = 'DATA_PUMP'"))
                        row = result.fetchone()
                        if row:
                            st.session_state.source_path = row[0]
                            st.success(f"Path: {row[0]}")
                        else:
                            st.warning("DATA_PUMP directory not found")
                except Exception as e:
                    st.error(f"Query error: {e}")
            else:
                st.error("Connect to DB1 first!")

    with col2:
        st.subheader("Destination")
        dest_host = st.text_input("Destination Host", key="dest_host")
        dest_ssh_port = st.text_input("SSH Port", value="22", key="dest_ssh_port")
        dest_user = st.text_input("User", key="dest_user")
        dest_pass = st.text_input("Password", type="password", key="dest_pass")
        dest_path = st.text_input("Destination Directory Path", key="dest_path")
        if st.button("Auto-fill from DB2", key="auto_dest"):
            if st.session_state.engine2:
                try:
                    with st.session_state.engine2.connect() as conn:
                        result = conn.execute(text("SELECT directory_path FROM dba_directories WHERE directory_name = 'DATA_PUMP'"))
                        row = result.fetchone()
                        if row:
                            st.session_state.dest_path = row[0]
                            st.success(f"Path: {row[0]}")
                        else:
                            st.warning("DATA_PUMP directory not found")
                except Exception as e:
                    st.error(f"Query error: {e}")
            else:
                st.error("Connect to DB2 first!")

    if st.button("🚀 Transfer Files", type="primary", use_container_width=True):
        # use session state values directly
        source_dir = st.session_state.get("source_path", "")
        dest_dir = st.session_state.get("dest_path", "")
        dumpfile = st.session_state.get("dp_dumpfile", "")
        logfile = st.session_state.get("dp_logfile", "")

        if not dumpfile and not logfile:
            st.error("No dump/log file names set in DataPump tab.")
        elif not source_dir or not dest_dir:
            st.error("Enter both source and destination paths.")
        elif not st.session_state.ssh_connected:
            st.error("Connect to SSH first.")
        else:
            st.session_state.transfer_logs = []
            def transfer():
                try:
                    src_sftp = st.session_state.ssh_client.open_sftp()
                    dst_ssh = paramiko.SSHClient()
                    dst_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    dst_ssh.connect(
                        st.session_state.dest_host,
                        port=int(st.session_state.dest_ssh_port),
                        username=st.session_state.dest_user,
                        password=st.session_state.dest_pass
                    )
                    dst_sftp = dst_ssh.open_sftp()
                    files = [f for f in (dumpfile, logfile) if f]
                    for f in files:
                        remote_src = os.path.join(source_dir, f).replace("\\", "/")
                        remote_dst = os.path.join(dest_dir, f).replace("\\", "/")
                        st.session_state.transfer_logs.append(f"Transferring {remote_src} -> {remote_dst}")
                        with io.BytesIO() as buf:
                            src_sftp.getfo(remote_src, buf)
                            buf.seek(0)
                            dst_sftp.putfo(buf, remote_dst)
                    src_sftp.close()
                    dst_sftp.close()
                    dst_ssh.close()
                    st.session_state.transfer_logs.append("✅ Transfer completed!")
                except Exception as e:
                    st.session_state.transfer_logs.append(f"❌ Transfer failed: {e}")

            threading.Thread(target=transfer, daemon=True).start()
            st.info("Transfer started. Check logs below.")

    st.subheader("Transfer Log")
    for log in st.session_state.transfer_logs:
        st.text(log)

# ---------------------- Compare Objects Tab (with Missing column) ----------------------
with tab3:
    st.header("Object Comparison")
    if st.button("Compare Objects", type="primary"):
        if not st.session_state.engine or not st.session_state.engine2:
            st.error("Both databases must be connected!")
        else:
            object_types = ["FUNCTION", "INDEX", "LOB", "PACKAGE", "PACKAGE BODY",
                            "PROCEDURE", "SEQUENCE", "SYNONYM", "TABLE", "TRIGGER"]
            results = []
            with st.spinner("Comparing..."):
                for obj_type in object_types:
                    try:
                        with st.session_state.engine.connect() as conn:
                            res = conn.execute(text("SELECT object_name FROM user_objects WHERE object_type = :t"), {"t": obj_type})
                            names1 = {row[0] for row in res}
                            count1 = len(names1)
                        with st.session_state.engine2.connect() as conn:
                            res = conn.execute(text("SELECT object_name FROM user_objects WHERE object_type = :t"), {"t": obj_type})
                            names2 = {row[0] for row in res}
                            count2 = len(names2)
                        missing = sorted(names1 - names2)
                        missing_str = ", ".join(missing) if missing else "None"
                        results.append({
                            "Type": obj_type,
                            "DB1 Count": count1,
                            "DB2 Count": count2,
                            "Missing in DB2": missing_str
                        })
                    except Exception as e:
                        st.error(f"Error in {obj_type}: {e}")
            if results:
                st.session_state.compare_results = pd.DataFrame(results)
            else:
                st.warning("No results obtained.")

    if st.session_state.compare_results is not None:
        st.dataframe(st.session_state.compare_results, use_container_width=True)

# Footer
st.divider()
st.caption("Remote DB Client - Oracle Automation Tool")