# app.py - Streamlit web version
import streamlit as st
import threading
import subprocess
import io
import os
import paramiko
from datetime import datetime
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
import pandas as pd
import time

# Page config
st.set_page_config(
    page_title="Remote DB Client - Oracle Automation",
    page_icon="🔧",
    layout="wide"
)

# Initialize session state
if 'db1_connected' not in st.session_state:
    st.session_state.db1_connected = False
    st.session_state.engine = None
    
if 'db2_connected' not in st.session_state:
    st.session_state.db2_connected = False
    st.session_state.engine2 = None
    
if 'ssh_connected' not in st.session_state:
    st.session_state.ssh_connected = False
    st.session_state.ssh_client = None

if 'transfer_logs' not in st.session_state:
    st.session_state.transfer_logs = []

if 'dp_output' not in st.session_state:
    st.session_state.dp_output = []

# Title
st.title("🔧 Remote DB Client - Oracle Automation")

# Sidebar for connections
with st.sidebar:
    st.header("🔌 Connections")
    
    # Database 1
    st.subheader("Database 1 (Source)")
    host1 = st.text_input("Host", value="localhost", key="host1")
    port1 = st.text_input("Port", value="1521", key="port1")
    service1 = st.text_input("Service Name", key="service1")
    user1 = st.text_input("User", key="user1")
    pass1 = st.text_input("Password", type="password", key="pass1")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Connect DB1", use_container_width=True):
            try:
                conn_str = f"oracle+oracledb://{user1}:{quote_plus(pass1)}@{host1}:{port1}/?service_name={service1}"
                st.session_state.engine = create_engine(conn_str)
                with st.session_state.engine.connect() as conn:
                    conn.execute(text("SELECT 1 FROM DUAL"))
                st.session_state.db1_connected = True
                st.success("DB1 Connected!")
            except Exception as e:
                st.session_state.db1_connected = False
                st.error(f"Connection failed: {e}")
    
    with col2:
        if st.button("Disconnect DB1", use_container_width=True):
            if st.session_state.engine:
                st.session_state.engine.dispose()
            st.session_state.db1_connected = False
            st.session_state.engine = None
    
    if st.session_state.db1_connected:
        st.success("✅ DB1 Connected")
    else:
        st.error("❌ DB1 Not Connected")
    
    st.divider()
    
    # Database 2
    st.subheader("Database 2 (Target)")
    host2 = st.text_input("Host", key="host2")
    port2 = st.text_input("Port", value="1521", key="port2")
    service2 = st.text_input("Service Name", key="service2")
    user2 = st.text_input("User", key="user2")
    pass2 = st.text_input("Password", type="password", key="pass2")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Connect DB2", use_container_width=True):
            try:
                conn_str = f"oracle+oracledb://{user2}:{quote_plus(pass2)}@{host2}:{port2}/?service_name={service2}"
                st.session_state.engine2 = create_engine(conn_str)
                with st.session_state.engine2.connect() as conn:
                    conn.execute(text("SELECT 1 FROM DUAL"))
                st.session_state.db2_connected = True
                st.success("DB2 Connected!")
            except Exception as e:
                st.session_state.db2_connected = False
                st.error(f"Connection failed: {e}")
    
    with col2:
        if st.button("Disconnect DB2", use_container_width=True):
            if st.session_state.engine2:
                st.session_state.engine2.dispose()
            st.session_state.db2_connected = False
            st.session_state.engine2 = None
    
    if st.session_state.db2_connected:
        st.success("✅ DB2 Connected")
    else:
        st.error("❌ DB2 Not Connected")
    
    st.divider()
    
    # SSH Connection
    st.subheader("SSH Connection")
    ssh_host = st.text_input("SSH Host", value="192.168.1.100", key="ssh_host")
    ssh_port = st.text_input("SSH Port", value="22", key="ssh_port")
    ssh_user = st.text_input("SSH User", key="ssh_user")
    ssh_pass = st.text_input("SSH Password", type="password", key="ssh_pass")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Connect SSH", use_container_width=True):
            try:
                st.session_state.ssh_client = paramiko.SSHClient()
                st.session_state.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                st.session_state.ssh_client.connect(ssh_host, port=int(ssh_port), username=ssh_user, password=ssh_pass)
                st.session_state.ssh_connected = True
                st.success("SSH Connected!")
            except Exception as e:
                st.session_state.ssh_connected = False
                st.error(f"SSH failed: {e}")
    
    with col2:
        if st.button("Disconnect SSH", use_container_width=True):
            if st.session_state.ssh_client:
                st.session_state.ssh_client.close()
            st.session_state.ssh_connected = False
            st.session_state.ssh_client = None
    
    if st.session_state.ssh_connected:
        st.success("✅ SSH Connected")
    else:
        st.error("❌ SSH Not Connected")

# Main tabs
tab1, tab2, tab3 = st.tabs(["📦 DataPump", "📁 File Transfer", "📊 Compare Objects"])

# DataPump Tab
with tab1:
    st.header("DataPump Export/Import")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        mode = st.radio("Mode", ["Export", "Import"], horizontal=True)
        
        st.subheader("Required Parameters")
        dumpfile = st.text_input("Dump File", value="export.dmp")
        logfile = st.text_input("Log File", value="export.log")
        
        st.subheader("Optional Parameters")
        schemas = st.text_input("Schemas (comma separated)")
        tables = st.text_input("Tables (schema.table format)")
        
        if mode == "Import":
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                remap_from = st.text_input("Remap From Schema")
            with col_r2:
                remap_to = st.text_input("Remap To Schema")
        
        content = st.selectbox("Content", ["ALL", "DATA_ONLY", "METADATA_ONLY"])
        parallel = st.number_input("Parallel", min_value=1, max_value=32, value=1)
        compression = st.selectbox("Compression", ["NONE", "METADATA_ONLY", "DATA_ONLY", "ALL"])
        extra_params = st.text_input("Extra Parameters")
        
        if st.button("Generate & Run DataPump", type="primary", use_container_width=True):
            target_engine = st.session_state.engine if mode == "Export" else st.session_state.engine2
            target_user = user1 if mode == "Export" else user2
            
            if not target_engine:
                st.error(f"Connect to {'DB1' if mode == 'Export' else 'DB2'} first!")
            else:
                with st.spinner("Running DataPump..."):
                    cmd = f"{'expdp' if mode == 'Export' else 'impdp'} {target_user}/******** directory=DATA_PUMP dumpfile={dumpfile} logfile={logfile}"
                    if schemas:
                        cmd += f" schemas={schemas}"
                    if tables:
                        cmd += f" tables={tables}"
                    if mode == "Import" and remap_from and remap_to:
                        cmd += f" remap_schema={remap_from}:{remap_to}"
                    if content != "ALL":
                        cmd += f" content={content}"
                    if parallel > 1:
                        cmd += f" parallel={parallel}"
                    if compression != "NONE":
                        cmd += f" compression={compression}"
                    if extra_params:
                        cmd += f" {extra_params}"
                    
                    st.session_state.dp_output.append(f"$ {cmd}\n")
                    
                    if st.session_state.ssh_connected and st.session_state.ssh_client:
                        try:
                            service = service1 if mode == "Export" else service2
                            env_cmd = f"export ORACLE_SID={service}; export ORAENV_ASK=NO; . /usr/local/bin/oraenv; {cmd}"
                            _, stdout, stderr = st.session_state.ssh_client.exec_command(env_cmd)
                            output = stdout.read().decode()
                            error = stderr.read().decode()
                            st.session_state.dp_output.append(output)
                            if error:
                                st.session_state.dp_output.append(f"ERROR: {error}")
                        except Exception as e:
                            st.session_state.dp_output.append(f"Execution failed: {e}")
                    else:
                        try:
                            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
                            st.session_state.dp_output.append(result.stdout)
                            if result.stderr:
                                st.session_state.dp_output.append(f"ERROR: {result.stderr}")
                        except Exception as e:
                            st.session_state.dp_output.append(f"Local execution failed: {e}")
    
    with col2:
        st.subheader("Generated Command")
        cmd_display = st.empty()
        
        st.subheader("Output")
        output_placeholder = st.empty()
        
        if st.session_state.dp_output:
            output_placeholder.code('\n'.join(st.session_state.dp_output), language='bash')
        
        if st.button("Clear Output"):
            st.session_state.dp_output = []
            st.experimental_rerun()

# File Transfer Tab
with tab2:
    st.header("File Transfer")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Source (Linux SSH)")
        source_path = st.text_input("Source Directory Path")
        
        if st.button("Auto-fill from DB1"):
            if st.session_state.engine:
                try:
                    with st.session_state.engine.connect() as conn:
                        result = conn.execute(text("SELECT directory_path FROM dba_directories WHERE directory_name = 'DATA_PUMP'"))
                        row = result.fetchone()
                        if row:
                            source_path = row[0]
                            st.success(f"Path: {row[0]}")
                        else:
                            st.warning("DATA_PUMP directory not found")
                except Exception as e:
                    st.error(f"Query error: {e}")
            else:
                st.error("Connect to DB1 first!")
    
    with col2:
        st.subheader("Destination")
        dest_host = st.text_input("Destination Host")
        dest_ssh_port = st.text_input("SSH Port", value="22")
        dest_user = st.text_input("User")
        dest_pass = st.text_input("Password", type="password")
        dest_path = st.text_input("Destination Directory Path")
        
        if st.button("Auto-fill from DB2"):
            if st.session_state.engine2:
                try:
                    with st.session_state.engine2.connect() as conn:
                        result = conn.execute(text("SELECT directory_path FROM dba_directories WHERE directory_name = 'DATA_PUMP'"))
                        row = result.fetchone()
                        if row:
                            dest_path = row[0]
                            st.success(f"Path: {row[0]}")
                        else:
                            st.warning("DATA_PUMP directory not found")
                except Exception as e:
                    st.error(f"Query error: {e}")
            else:
                st.error("Connect to DB2 first!")
    
    if st.button("🚀 Transfer Files", type="primary", use_container_width=True):
        if not source_path or not dest_path:
            st.error("Enter both source and destination paths!")
        elif not st.session_state.ssh_connected:
            st.error("Connect to SSH first!")
        else:
            with st.spinner("Transferring files..."):
                def transfer():
                    try:
                        src_sftp = st.session_state.ssh_client.open_sftp()
                        
                        dst_ssh = paramiko.SSHClient()
                        dst_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        dst_ssh.connect(dest_host, port=int(dest_ssh_port), username=dest_user, password=dest_pass)
                        dst_sftp = dst_ssh.open_sftp()
                        
                        files = [f for f in [dumpfile, logfile] if f]
                        for f in files:
                            remote_src = os.path.join(source_path, f).replace("\\", "/")
                            remote_dst = os.path.join(dest_path, f).replace("\\", "/")
                            st.session_state.transfer_logs.append(f"Transferring {remote_src} -> {remote_dst}")
                            
                            with io.BytesIO() as buffer:
                                src_sftp.getfo(remote_src, buffer)
                                buffer.seek(0)
                                dst_sftp.putfo(buffer, remote_dst)
                        
                        src_sftp.close()
                        dst_sftp.close()
                        dst_ssh.close()
                        st.session_state.transfer_logs.append("✅ Transfer completed!")
                    except Exception as e:
                        st.session_state.transfer_logs.append(f"❌ Transfer failed: {e}")
                
                threading.Thread(target=transfer, daemon=True).start()
                time.sleep(1)
    
    st.subheader("Transfer Log")
    log_placeholder = st.empty()
    if st.session_state.transfer_logs:
        for log in st.session_state.transfer_logs:
            st.text(log)

# Compare Objects Tab
with tab3:
    st.header("Object Comparison")
    
    if st.button("Compare Objects", type="primary"):
        if not st.session_state.engine or not st.session_state.engine2:
            st.error("Both databases must be connected!")
        else:
            with st.spinner("Comparing..."):
                object_types = ["FUNCTION", "INDEX", "LOB", "PACKAGE", "PACKAGE BODY", 
                              "PROCEDURE", "SEQUENCE", "SYNONYM", "TABLE", "TRIGGER"]
                
                results = []
                for obj_type in object_types:
                    try:
                        with st.session_state.engine.connect() as conn:
                            result = conn.execute(text("SELECT COUNT(*) FROM user_objects WHERE object_type = :t"), {"t": obj_type})
                            count1 = result.fetchone()[0]
                        
                        with st.session_state.engine2.connect() as conn:
                            result = conn.execute(text("SELECT COUNT(*) FROM user_objects WHERE object_type = :t"), {"t": obj_type})
                            count2 = result.fetchone()[0]
                        
                        results.append({"Type": obj_type, "DB1 Count": count1, "DB2 Count": count2})
                    except Exception as e:
                        st.error(f"Error in {obj_type}: {e}")
                
                if results:
                    df = pd.DataFrame(results)
                    st.dataframe(df, use_container_width=True)
                    st.success("Comparison completed!")

# Footer
st.divider()
st.caption("Remote DB Client - Oracle Automation Tool")