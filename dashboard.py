"""
Real-time Link Budget Analysis Dashboard
Displays GNSS location data, calculates link budget parameters,
and visualizes transmitter-receiver communication link on map.
@ Satvik Agrawal
"""

import streamlit as st
import serial
import serial.tools.list_ports
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import time
import math
import requests
import json
from datetime import datetime
import threading
import queue

# Page configuration
st.set_page_config(
    page_title="Link Budget Analysis Dashboard",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables
if 'data_buffer' not in st.session_state:
    st.session_state.data_buffer = []
if 'serial_connection' not in st.session_state:
    st.session_state.serial_connection = None
if 'data_queue' not in st.session_state:
    st.session_state.data_queue = queue.Queue()
if 'receiver_location' not in st.session_state:
    st.session_state.receiver_location = None

def get_current_location():
    """
    Try to get current GPS location using IP geolocation as fallback
    """
    try:
        # Try using ipinfo.io for approximate location
        response = requests.get('https://ipinfo.io', timeout=5)
        data = response.json()
        if 'loc' in data:
            lat, lon = map(float, data['loc'].split(','))
            return lat, lon, data.get('city', 'Unknown')
    except:
        pass
    
    # Default location (example: somewhere in India)
    return 18.5204, 73.8567, "Default Location"

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two GPS coordinates using Haversine formula
    Returns distance in kilometers
    """
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def calculate_free_space_path_loss(distance_km, frequency_mhz=915):
    """
    Calculate Free Space Path Loss (FSPL) in dB
    FSPL = 20*log10(d) + 20*log10(f) + 32.44
    where d is distance in km and f is frequency in MHz
    """
    if distance_km <= 0:
        return 0
    
    fspl = 20 * math.log10(distance_km) + 20 * math.log10(frequency_mhz) + 32.44
    return fspl

def calculate_link_margin(tx_power, tx_gain, rx_gain, fspl, rx_sensitivity, filter_loss, rssi):
    """
    Calculate Link Margin
    Link Margin = RSSI - Receiver Sensitivity
    Also calculate theoretical received power for comparison
    """
    # Theoretical received power = Tx Power + Tx Gain + Rx Gain - FSPL - Filter Loss
    theoretical_rx_power = tx_power + tx_gain + rx_gain - fspl - filter_loss
    
    # Link margin based on actual RSSI
    link_margin = rssi - rx_sensitivity
    
    return link_margin, theoretical_rx_power

def read_serial_data():
    """
    Background thread function to read serial data
    """
    while st.session_state.serial_connection and st.session_state.serial_connection.is_open:
        try:
            if st.session_state.serial_connection.in_waiting > 0:
                line = st.session_state.serial_connection.readline().decode('utf-8').strip()
                if line and ',' in line:
                    st.session_state.data_queue.put(line)
        except Exception as e:
            st.session_state.data_queue.put(f"ERROR: {str(e)}")
            break
        time.sleep(0.1)

def parse_serial_data(line):
    """
    Parse CSV data from Teensy receiver
    Format: timestamp,latitude,longitude,altitude,rssi,snr
    """
    try:
        parts = line.split(',')
        if len(parts) >= 6:
            return {
                'timestamp': int(parts[0]),
                'latitude': float(parts[1]) / 10000000.0,  # Convert from degrees * 10^7
                'longitude': float(parts[2]) / 10000000.0,
                'altitude': float(parts[3]) / 1000.0,  # Convert from mm to meters
                'rssi': float(parts[4]),
                'snr': float(parts[5]),
                'datetime': datetime.now()
            }
    except Exception as e:
        st.sidebar.error(f"Data parsing error: {str(e)}")
    return None

def main():
    st.title("📡 Real-time Link Budget Analysis Dashboard")
    st.markdown("---")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("🔧 Configuration")
        
        # Serial port selection
        st.subheader("Serial Connection")
        ports = [port.device for port in serial.tools.list_ports.comports()]
        selected_port = st.selectbox("Select COM Port", ["None"] + ports)
        baud_rate = st.selectbox("Baud Rate", [9600, 57600, 115200], index=2)
        
        # Connection controls
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Connect"):
                if selected_port != "None":
                    try:
                        if st.session_state.serial_connection:
                            st.session_state.serial_connection.close()
                        
                        st.session_state.serial_connection = serial.Serial(selected_port, baud_rate, timeout=1)
                        
                        # Start background thread for reading data
                        thread = threading.Thread(target=read_serial_data, daemon=True)
                        thread.start()
                        
                        st.success(f"Connected to {selected_port}")
                    except Exception as e:
                        st.error(f"Connection failed: {str(e)}")
        
        with col2:
            if st.button("Disconnect"):
                if st.session_state.serial_connection:
                    st.session_state.serial_connection.close()
                    st.session_state.serial_connection = None
                    st.success("Disconnected")
        
        # Connection status
        if st.session_state.serial_connection and st.session_state.serial_connection.is_open:
            st.success("🟢 Connected")
        else:
            st.error("🔴 Disconnected")
        
        st.markdown("---")
        
        # Receiver location configuration
        st.subheader("📍 Receiver Location")
        if st.button("Get Current Location"):
            lat, lon, city = get_current_location()
            st.session_state.receiver_location = (lat, lon)
            st.success(f"Location set to: {city}")
        
        if st.session_state.receiver_location:
            rx_lat = st.number_input("Receiver Latitude", value=st.session_state.receiver_location[0], format="%.6f")
            rx_lon = st.number_input("Receiver Longitude", value=st.session_state.receiver_location[1], format="%.6f")
        else:
            rx_lat = st.number_input("Receiver Latitude", value=18.520400, format="%.6f")
            rx_lon = st.number_input("Receiver Longitude", value=73.856700, format="%.6f")
        
        st.session_state.receiver_location = (rx_lat, rx_lon)
        
        st.markdown("---")
        
        # Link budget parameters
        st.subheader("📊 Link Budget Parameters")
        tx_power = st.number_input("Transmitter Power (dBm)", value=20.0, min_value=-30.0, max_value=30.0)
        tx_gain = st.number_input("Transmitter Antenna Gain (dBi)", value=2.0, min_value=-10.0, max_value=20.0)
        rx_gain = st.number_input("Receiver Antenna Gain (dBi)", value=2.0, min_value=-10.0, max_value=20.0)
        rx_sensitivity = st.number_input("Receiver Sensitivity (dBm)", value=-110.0, min_value=-150.0, max_value=-50.0)
        filter_loss = st.number_input("Receiver Filter Loss (dB)", value=2.0, min_value=0.0, max_value=10.0)
        frequency = st.number_input("Frequency (MHz)", value=915.0, min_value=100.0, max_value=3000.0)
    
    # Main dashboard
    col1, col2 = st.columns([1, 1])
    
    # Process queued data
    while not st.session_state.data_queue.empty():
        try:
            line = st.session_state.data_queue.get_nowait()
            if not line.startswith("ERROR"):
                data = parse_serial_data(line)
                if data:
                    st.session_state.data_buffer.append(data)
                    # Keep only last 100 readings
                    if len(st.session_state.data_buffer) > 100:
                        st.session_state.data_buffer.pop(0)
        except queue.Empty:
            break
    
    # Current readings display
    with col1:
        st.subheader("📊 Current Readings")
        
        if st.session_state.data_buffer:
            latest_data = st.session_state.data_buffer[-1]
            
            # Display current values
            col1a, col1b, col1c = st.columns(3)
            with col1a:
                st.metric("Latitude", f"{latest_data['latitude']:.6f}°")
                st.metric("RSSI", f"{latest_data['rssi']:.1f} dBm")
            with col1b:
                st.metric("Longitude", f"{latest_data['longitude']:.6f}°")
                st.metric("SNR", f"{latest_data['snr']:.1f} dB")
            with col1c:
                st.metric("Altitude", f"{latest_data['altitude']:.1f} m")
                st.metric("Timestamp", f"{latest_data['timestamp']} ms")
            
            # Calculate link budget
            distance = calculate_distance(
                rx_lat, rx_lon,
                latest_data['latitude'], latest_data['longitude']
            )
            
            fspl = calculate_free_space_path_loss(distance, frequency)
            link_margin, theoretical_rx_power = calculate_link_margin(
                tx_power, tx_gain, rx_gain, fspl, rx_sensitivity, filter_loss, latest_data['rssi']
            )
            
            st.markdown("---")
            st.subheader("🔗 Link Budget Analysis")
            
            col2a, col2b = st.columns(2)
            with col2a:
                st.metric("Distance", f"{distance:.3f} km")
                st.metric("Free Space Path Loss", f"{fspl:.1f} dB")
                st.metric("Link Margin", f"{link_margin:.1f} dB", 
                         delta=f"{'Good' if link_margin > 10 else 'Poor' if link_margin < 0 else 'Fair'}")
            with col2b:
                st.metric("Theoretical Rx Power", f"{theoretical_rx_power:.1f} dBm")
                st.metric("Actual RSSI", f"{latest_data['rssi']:.1f} dBm")
                st.metric("Power Difference", f"{latest_data['rssi'] - theoretical_rx_power:.1f} dB")
        
        else:
            st.info("No data received yet. Check serial connection.")
    
    # Map display
    with col2:
        st.subheader("🗺️ Real-time Location Map")
        
        if st.session_state.data_buffer and st.session_state.receiver_location:
            latest_data = st.session_state.data_buffer[-1]
            
            # Create map centered between transmitter and receiver
            center_lat = (rx_lat + latest_data['latitude']) / 2
            center_lon = (rx_lon + latest_data['longitude']) / 2
            
            m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
            
            # Add receiver marker (blue)
            folium.Marker(
                [rx_lat, rx_lon],
                popup=f"Receiver Station<br>Lat: {rx_lat:.6f}<br>Lon: {rx_lon:.6f}",
                tooltip="Receiver",
                icon=folium.Icon(color='blue', icon='home')
            ).add_to(m)
            
            # Add transmitter marker (red)
            folium.Marker(
                [latest_data['latitude'], latest_data['longitude']],
                popup=f"Transmitter<br>Lat: {latest_data['latitude']:.6f}<br>Lon: {latest_data['longitude']:.6f}<br>Alt: {latest_data['altitude']:.1f}m<br>RSSI: {latest_data['rssi']:.1f}dBm",
                tooltip="Transmitter",
                icon=folium.Icon(color='red', icon='broadcast-tower')
            ).add_to(m)
            
            # Draw line between transmitter and receiver
            distance = calculate_distance(
                rx_lat, rx_lon,
                latest_data['latitude'], latest_data['longitude']
            )
            
            folium.PolyLine(
                locations=[[rx_lat, rx_lon], [latest_data['latitude'], latest_data['longitude']]],
                color='green',
                weight=2,
                opacity=0.8,
                popup=f"Distance: {distance:.3f} km"
            ).add_to(m)
            
            # Add distance annotation at midpoint
            mid_lat = (rx_lat + latest_data['latitude']) / 2
            mid_lon = (rx_lon + latest_data['longitude']) / 2
            
            folium.Marker(
                [mid_lat, mid_lon],
                popup=f"Distance: {distance:.3f} km<br>FSPL: {calculate_free_space_path_loss(distance, frequency):.1f} dB",
                icon=folium.DivIcon(html=f'<div style="font-size: 12px; color: green; font-weight: bold;">{distance:.3f} km</div>')
            ).add_to(m)
            
            st_folium(m, width=700, height=400)
        
        else:
            st.info("Map will appear when data is available and receiver location is set.")
    
    # Data history table
    if st.session_state.data_buffer:
        st.subheader("📈 Recent Data History")
        
        # Convert to DataFrame for display
        df = pd.DataFrame(st.session_state.data_buffer[-10:])  # Show last 10 readings
        df = df[['datetime', 'latitude', 'longitude', 'altitude', 'rssi', 'snr', 'timestamp']]
        df['datetime'] = df['datetime'].dt.strftime('%H:%M:%S')
        
        st.dataframe(df, use_container_width=True)
    
    # Auto-refresh
    time.sleep(1)
    st.rerun()

if __name__ == "__main__":
    main()
