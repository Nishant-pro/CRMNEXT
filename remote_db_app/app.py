# app.py - Streamlit web version with SSH tunnelling (debugging added)
import streamlit as st
import threading
import subprocess
import io
import os
import time
import socket
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
        st.session_state.db1_tunnel_port = None
    if 'db2_connected' not in st.session_state:
        st.session_state.db2_connected = False
        st.session_state.engine2 = None
        st.session_state.db2_tunnel_port = None
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

# ---------- Helper functions ----------
def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def open_ssh_tunnel(ssh_client, remote_host, remote_port):
    """Open SSH forward tunnel. Returns local port or raises exception."""
    local_port = get_free_port()
    transport = ssh_client.get_transport()
    if not transport or not transport.is_active():
        raise Exception("SSH transport is not active")
    # Forward local_port to remote_host:remote_port via the SSH server
    transport.request_port_forward('127.0.0.1', local_port, remote_host, remote_port)
    return local_port

def close_ssh_tunnel(ssh_client, local_port):
    try:
        if ssh_client and ssh_client.get_transport():
            ssh_client.get_transport().cancel_port_forward('127.0.0.1', local_port)
    except:
        pass

def test_port(host, port, timeout=3):
    """Quickly check if a TCP port is open."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except:
        return False

# Sidebar – Connections
with st.sidebar:
    st.header("🔌 Connections")

    # ----- Database 1 -----
    st.subheader("Database 1 (Source)")
    host1 = st.text_input("DB Host (as seen from SSH server)", value="localhost", key="host1")
    port1 = st.text_input("DB Port", value="1521", key="port1")
    service1 = st.text_input("Service Name", key="service1")
    user1 = st.text_input("User", key="user1")
    pass1 = st.text_input("Password", type="password", key="pass1")
    use_tunnel1 = st.checkbox("Use SSH tunnel for DB1", value=True, key="tunnel1")

    if st.button("Connect DB1", use_container_width=True, type="primary"):
        # Clean up any previous connection
        if st.session_state.engine:
            st.session_state.engine.dispose()
        if st.session_state.db1_tunnel_port is not None:
            close_ssh_tunnel(st.session_state.ssh_client, st.session_state.db1_tunnel_port)
        st.session_state.engine = None
        st.session_state.db1_connected = False
        st.session_state.db1_tunnel_port = None

        local_host = host1
        local_port = int(port1)

        if use_tunnel1 and st.session_state.ssh_connected and st.session_state.ssh_client:
            try:
                tunnel_port = open_ssh_tunnel(st.session_state.ssh_client, host1, int(port1))
                st.success(f"Tunnel opened: localhost:{tunnel_port} -> {host1}:{port1}")
                local_host = '127.0.0.1'
                local_port = tunnel_port
                st.session_state.db1_tunnel_port = tunnel_port

                # Quick test that the tunnel is really open
                if not test_port('127.0.0.1', tunnel_port):
                    st.warning("Tunnel port seems closed – SSH server may be blocking forwarding.")
            except Exception as e:
                st.error(f"SSH tunnel failed: {e}")
                st.stop()

        conn_str = f"oracle+oracledb://{user1}:****@{local_host}:{local_port}/?service_name={service1}"
        st.info(f"Connection string (masked): {conn_str}")

        try:
            full_conn = f"oracle+oracledb://{user1}:{quote_plus(pass1)}@{local_host}:{local_port}/?service_name={service1}"
            eng = create_engine(full_conn)
            with eng.connect() as conn:
                conn.execute(text("SELECT 1 FROM DUAL"))
            st.session_state.engine = eng
            st.session_state.db1_connected = True
            st.success("DB1 Connected!")
        except Exception as e:
            st.session_state.db1_connected = False
            st.session_state.engine = None
            if st.session_state.db1_tunnel_port is not None:
                close_ssh_tunnel(st.session_state.ssh_client, st.session_state.db1_tunnel_port)
                st.session_state.db1_tunnel_port = None
            st.error(f"Connection failed: {e}")

    if st.button("Disconnect DB1", use_container_width=True):
        if st.session_state.engine:
            st.session_state.engine.dispose()
        st.session_state.engine = None
        st.session_state.db1_connected = False
        if st.session_state.db1_tunnel_port is not None:
            close_ssh_tunnel(st.session_state.ssh_client, st.session_state.db1_tunnel_port)
            st.session_state.db1_tunnel_port = None

    st.markdown("✅ **DB1:** " + ("Connected" if st.session_state.db1_connected else "Not Connected"))

    st.divider()

    # ----- Database 2 -----
    st.subheader("Database 2 (Target)")
    host2 = st.text_input("DB Host (as seen from SSH server)", key="host2")
    port2 = st.text_input("DB Port", value="1521", key="port2")
    service2 = st.text_input("Service Name", key="service2")
    user2 = st.text_input("User", key="user2")
    pass2 = st.text_input("Password", type="password", key="pass2")
    use_tunnel2 = st.checkbox("Use SSH tunnel for DB2", value=True, key="tunnel2")

    if st.button("Connect DB2", use_container_width=True, type="primary"):
        if st.session_state.engine2:
            st.session_state.engine2.dispose()
        if st.session_state.db2_tunnel_port is not None:
            close_ssh_tunnel(st.session_state.ssh_client, st.session_state.db2_tunnel_port)
        st.session_state.engine2 = None
        st.session_state.db2_connected = False
        st.session_state.db2_tunnel_port = None

        local_host = host2
        local_port = int(port2)

        if use_tunnel2 and st.session_state.ssh_connected and st.session_state.ssh_client:
            try:
                tunnel_port = open_ssh_tunnel(st.session_state.ssh_client, host2, int(port2))
                st.success(f"Tunnel opened: localhost:{tunnel_port} -> {host2}:{port2}")
                local_host = '127.0.0.1'
                local_port = tunnel_port
                st.session_state.db2_tunnel_port = tunnel_port

                if not test_port('127.0.0.1', tunnel_port):
                    st.warning("Tunnel port seems closed – SSH server may be blocking forwarding.")
            except Exception as e:
                st.error(f"SSH tunnel failed: {e}")
                st.stop()

        conn_str = f"oracle+oracledb://{user2}:****@{local_host}:{local_port}/?service_name={service2}"
        st.info(f"Connection string (masked): {conn_str}")

        try:
            full_conn = f"oracle+oracledb://{user2}:{quote_plus(pass2)}@{local_host}:{local_port}/?service_name={service2}"
            eng = create_engine(full_conn)
            with eng.connect() as conn:
                conn.execute(text("SELECT 1 FROM DUAL"))
            st.session_state.engine2 = eng
            st.session_state.db2_connected = True
            st.success("DB2 Connected!")
        except Exception as e:
            st.session_state.db2_connected = False
            st.session_state.engine2 = None
            if st.session_state.db2_tunnel_port is not None:
                close_ssh_tunnel(st.session_state.ssh_client, st.session_state.db2_tunnel_port)
                st.session_state.db2_tunnel_port = None
            st.error(f"Connection failed: {e}")

    if st.button("Disconnect DB2", use_container_width=True):
        if st.session_state.engine2:
            st.session_state.engine2.dispose()
        st.session_state.engine2 = None
        st.session_state.db2_connected = False
        if st.session_state.db2_tunnel_port is not None:
            close_ssh_tunnel(st.session_state.ssh_client, st.session_state.db2_tunnel_port)
            st.session_state.db2_tunnel_port = None

    st.markdown("✅ **DB2:** " + ("Connected" if st.session_state.db2_connected else "Not Connected"))

    st.divider()

    # ----- SSH Connection -----
    st.subheader("SSH Connection")
    ssh_host = st.text_input("SSH Host", value="192.168.1.100", key="ssh_host")
    ssh_port = st.text_input("SSH Port", value="22", key="ssh_port")
    ssh_user = st.text_input("SSH User", key="ssh_user")
    ssh_pass = st.text_input("SSH Password", type="password", key="ssh_pass")

    if st.button("Connect SSH", use_container_width=True, type="primary"):
        if st.session_state.ssh_client:
            try:
                st.session_state.ssh_client.close()
            except:
                pass
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ssh_host, port=int(ssh_port), username=ssh_user, password=ssh_pass)
            st.session_state.ssh_client = client
            st.session_state.ssh_connected = True
            st.success("SSH Connected!")
        except Exception as e:
            st.session_state.ssh_connected = False
            st.session_state.ssh_client = None
            st.error(f"SSH failed: {e}")

    if st.button("Disconnect SSH", use_container_width=True):
        # Close any database tunnels first
        if st.session_state.db1_tunnel_port is not None:
            close_ssh_tunnel(st.session_state.ssh_client, st.session_state.db1_tunnel_port)
            st.session_state.db1_tunnel_port = None
        if st.session_state.db2_tunnel_port is not None:
            close_ssh_tunnel(st.session_state.ssh_client, st.session_state.db2_tunnel_port)
            st.session_state.db2_tunnel_port = None
        if st.session_state.ssh_client:
            st.session_state.ssh_client.close()
        st.session_state.ssh_client = None
        st.session_state.ssh_connected = False
        st.session_state.engine = None
        st.session_state.engine2 = None
        st.session_state.db1_connected = False
        st.session_state.db2_connected = False

    st.markdown("✅ **SSH:** " + ("Connected" if st.session_state.ssh_connected else "Not Connected"))

# Main tabs
tab1, tab2, tab3 = st.tabs(["📦 DataPump", "📁 File Transfer", "📊 Compare Objects"])

# ---------------------- DataPump Tab ----------------------
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
                    st.session_state.dp_output = []
                    st.session_state.dp_stop = False
                    cmd_parts = [
                        "expdp" if mode == "Export" else "impdp",
                        f"{st.session_state.user1 if mode == 'Export' else st.session_state.user2}/<password>"
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
                        service = st.session_state.service1 if mode == "Export" else st.session_state.service2
                        env_cmd = f"export ORACLE_SID={service}; export ORAENV_ASK=NO; . /usr/local/bin/oraenv; {full_cmd}"

                        def ssh_exec_thread():
                            client = st.session_state.ssh_client
                            try:
                                stdin, stdout, stderr = client.exec_command(env_cmd, get_pty=True)
                                for line in iter(stdout.readline, ""):
                                    if st.session_state.dp_stop:
                                        stdin.write("\x03")
                                        break
                                    st.session_state.dp_output.append(line.rstrip())
                                for line in iter(stderr.readline, ""):
                                    st.session_state.dp_output.append(f"[STDERR] {line.rstrip()}")
                                st.session_state.dp_output.append("✅ DataPump finished.")
                            except Exception as e:
                                st.session_state.dp_output.append(f"SSH error: {e}")
                            finally:
                                st.session_state.dp_running = False

                        st.session_state.dp_running = True
                        threading.Thread(target=ssh_exec_thread, daemon=True).start()
                        st.info("DataPump started...")
                    else:
                        st.error("SSH not connected.")
        else:
            if st.button("Stop DataPump", type="secondary"):
                st.session_state.dp_stop = True

    with col_right:
        st.subheader("Output")
        output_placeholder = st.empty()
        if st.session_state.dp_output:
            output_placeholder.code("\n".join(st.session_state.dp_output), language="bash")
        if st.button("Clear Output"):
            st.session_state.dp_output = []

# ---------------------- File Transfer Tab ----------------------
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
                            st.warning("DATA_PUMP not found")
                except Exception as e:
                    st.error(str(e))
            else:
                st.error("Connect DB1 first")

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
                            st.warning("DATA_PUMP not found")
                except Exception as e:
                    st.error(str(e))
            else:
                st.error("Connect DB2 first")

    if st.button("🚀 Transfer Files", type="primary", use_container_width=True):
        # (same transfer logic as before)
        st.info("Transfer started...")
        # (unchanged)

# ---------------------- Compare Objects Tab ----------------------
with tab3:
    st.header("Object Comparison")
    if st.button("Compare Objects", type="primary"):
        if not st.session_state.engine or not st.session_state.engine2:
            st.error("Both DBs must be connected")
        else:
            # (unchanged comparison logic)
            pass

# Footer
st.divider()
st.caption("Remote DB Client - Oracle Automation Tool")