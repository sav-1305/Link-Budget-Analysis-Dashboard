# Real-time Link Budget Analysis System

A comprehensive RF link budget analysis system using Teensy 4.1 microcontrollers, GNSS positioning, and RYLR99X LoRa transceivers for real-time evaluation of 
wireless communication links. This system provides real-time analysis of RF link performance by:

- Transmitting GPS coordinates and telemetry via LoRa
- Receiving and analyzing signal strength metrics (RSSI/SNR)
- Calculating link budget parameters and path loss
- Visualizing data on an interactive dashboard with live mapping

## Components Required
**Hardware Used**
- 2x Teensy 4.1 microcontroller Development boards
- 2x RYLR993 (LoRa transceiver modules (915MHz)
- 1x GNSS MAX Click GPS module (u-blox based)
- Bi-directional Antennas for LoRa transceivers
- USB-B cables for programming and data connection

**Software Used**
- Arduino IDE 2.2.1
- Python 3.8.10
  - SparkFun u-blox GNSS Library

## Dashboard Features
**Real-time Monitoring**
- Live GPS coordinates from transmitter
- Signal strength metrics (RSSI/SNR)
- Link quality indicators with status alerts
- Distance calculation between stations

**Interactive Map**
- Dual-marker visualization (transmitter/receiver)
- Real-time path tracking with distance annotation
- Signal strength overlay on location markers
- Zoom and pan controls for detailed view

**Link Budget Analysis**
- Free Space Path Loss calculation
- Link margin computation with safety thresholds
- Theoretical vs actual power comparison
- User-configurable RF parameters
