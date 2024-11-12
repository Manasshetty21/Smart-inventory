import streamlit as st
import firebase_admin
from firebase_admin import credentials, db, exceptions
import pandas as pd
from datetime import datetime
import time
import os

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["Time", "Distance"])
if 'last_update' not in st.session_state:
    st.session_state.last_update = None
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = True

# Set static credentials
VALID_USERNAME = "admin"
VALID_PASSWORD = "admin123"

def login():
    st.title("Smart Container Dashboard Login")
    
    # Create login form
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Invalid username or password")

def main_dashboard():
    # Firebase initialization
    try:
        default_app = firebase_admin.get_app()
    except ValueError:
        # Initialize Firebase only if it hasn't been initialized
        try:
            cred = credentials.Certificate("firebase-adminsdk.json")
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://smart-container-46c13-default-rtdb.firebaseio.com/'
            })
        except Exception as e:
            st.error(f"Firebase initialization error: {str(e)}")
            return

    # Page configuration
    st.set_page_config(
        page_title="Smart Container Dashboard",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Add logout button in sidebar
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # Title and description
    st.title("Smart Container Dashboard")
    st.markdown("Real-time monitoring of container level using ESP32 ToF sensor")

    # Create layout
    col1, col2 = st.columns(2)

    # Sidebar controls
    st.sidebar.title("Dashboard Controls")
    update_interval = st.sidebar.slider(
        "Update Interval (seconds)",
        min_value=1,
        max_value=60,
        value=3
    )
    
    # Add auto-refresh toggle
    st.session_state.auto_refresh = st.sidebar.checkbox(
        "Enable Auto Refresh",
        value=st.session_state.auto_refresh
    )

    clear_data = st.sidebar.button("Clear Historical Data")
    if clear_data:
        st.session_state.df = pd.DataFrame(columns=["Time", "Distance"])

    # Manual refresh button
    if not st.session_state.auto_refresh:
        if st.sidebar.button("Refresh Data"):
            st.rerun()

    # Containers for real-time updates
    with col1:
        st.subheader("Current Level")
        level_metric = st.empty()
        st.markdown("---")
        st.subheader("Last Update")
        last_update_text = st.empty()

    with col2:
        st.subheader("Level History")
        chart_container = st.empty()

    # Data table and download section
    st.markdown("---")
    table_container = st.empty()
    download_container = st.empty()

    try:
        # Real-time data update
        ref = db.reference('/sensor/distance')
        data = ref.get()
        
        if data is not None:
            # Calculate container level
            try:
                distance = float(data)
                container_level = max(0, min(100, (120 - distance) * (100 / 80)))
                
                # Update DataFrame
                current_time = pd.Timestamp.now()
                new_row = pd.DataFrame({
                    "Time": [current_time],
                    "Distance": [container_level]
                })
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                st.session_state.df = st.session_state.df.tail(100)  # Keep only last 100 records

                # Update metric
                delta = None
                if len(st.session_state.df) > 1:
                    delta = container_level - st.session_state.df['Distance'].iloc[-2]
                    
                level_metric.metric(
                    label="Container Level",
                    value=f"{container_level:.1f}%",
                    delta=f"{delta:.1f}%" if delta is not None else None
                )

                # Update last update time
                st.session_state.last_update = datetime.now()
                last_update_text.text(
                    f"Last updated: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}"
                )

                # Update chart
                chart_container.line_chart(
                    st.session_state.df.set_index("Time")["Distance"],
                    use_container_width=True
                )

                # Update table
                table_container.dataframe(
                    st.session_state.df.sort_values("Time", ascending=False),
                    use_container_width=True,
                    hide_index=True
                )

                # Update download button
                csv = st.session_state.df.to_csv(index=False).encode('utf-8')
                download_container.download_button(
                    label="📥 Download Data as CSV",
                    data=csv,
                    file_name=f"container_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

            except (TypeError, ValueError) as e:
                st.error(f"Error processing data: {str(e)}")
        else:
            st.warning("No data available from sensor")

    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")

    # Auto-refresh implementation
    if st.session_state.auto_refresh:
        time.sleep(update_interval)
        st.rerun()

def main():
    if not st.session_state.logged_in:
        login()
    else:
        main_dashboard()

if __name__ == "__main__":
    main()
