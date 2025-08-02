/*
FIRMWARE FOR TEENSY 4.1 - RECEIVER
RYLR99X receiver for location data with RSSI/SNR parsing
Receives lat/long/alt data and extracts signal quality metrics
Outputs formatted data via Serial for dashboard integration
@ Satvik Agrawal
 */

#define RYLR        Serial2
#define DEBUG_SERIAL Serial

// Structure to hold received data
struct LocationData {
  unsigned long timestamp;
  int32_t latitude;
  int32_t longitude; 
  int32_t altitude;
  int16_t rssi;
  int16_t snr;
  bool validData;
};

LocationData currentData;

void setup() {
  // Initialize Serial for USB communication to laptop
  DEBUG_SERIAL.begin(115200);
  
  // Initialize Serial2 for RYLR99X communication
  RYLR.begin(57600);
  
  // Wait for Serial connection (optional - remove if running standalone)
  while (!DEBUG_SERIAL && millis() < 5000) {
    delay(10);
  }
  
  DEBUG_SERIAL.println("Teensy 4.1 RYLR99X Receiver Initialized");
  DEBUG_SERIAL.println("Waiting for transmissions...");
  
  // Initialize data structure
  currentData.validData = false;
}

// Parse the complete RYLR response including RSSI and SNR
bool parseRYLRResponse(String response, LocationData &data) {
  // RYLR response format: +RCV=<Address>,<Length>,<Data>,<RSSI>,<SNR>
  // Example: +RCV=0,25,12345;123456789;987654321;1000,-45,10
  
  response.trim();
  
  // Check if this is a receive command
  if (!response.startsWith("+RCV=")) {
    return false;
  }
  
  // Find comma positions for parsing
  int commaPos[4];
  int commaCount = 0;
  
  for (int i = 0; i < response.length() && commaCount < 4; i++) {
    if (response.charAt(i) == ',') {
      commaPos[commaCount] = i;
      commaCount++;
    }
  }
  
  if (commaCount < 4) {
    DEBUG_SERIAL.println("Error: Incomplete RYLR response");
    return false;
  }
  
  // Extract data payload (between 2nd and 3rd comma)
  String dataPayload = response.substring(commaPos[1] + 1, commaPos[2]);
  
  // Extract RSSI (between 3rd and 4th comma)
  String rssiStr = response.substring(commaPos[2] + 1, commaPos[3]);
  
  // Extract SNR (after 4th comma)
  String snrStr = response.substring(commaPos[3] + 1);
  
  // Parse the data payload: timestamp;latitude;longitude;altitude
  int semicolonPos[3];
  int semicolonCount = 0;
  
  for (int i = 0; i < dataPayload.length() && semicolonCount < 3; i++) {
    if (dataPayload.charAt(i) == ';') {
      semicolonPos[semicolonCount] = i;
      semicolonCount++;
    }
  }
  
  if (semicolonCount < 3) {
    DEBUG_SERIAL.println("Error: Invalid data payload format");
    return false;
  }
  
  // Extract individual data fields
  String timestampStr = dataPayload.substring(0, semicolonPos[0]);
  String latStr = dataPayload.substring(semicolonPos[0] + 1, semicolonPos[1]);
  String lonStr = dataPayload.substring(semicolonPos[1] + 1, semicolonPos[2]);
  String altStr = dataPayload.substring(semicolonPos[2] + 1);
  
  // Convert strings to numbers
  data.timestamp = timestampStr.toInt();
  data.latitude = latStr.toInt();
  data.longitude = lonStr.toInt();
  data.altitude = altStr.toInt();
  data.rssi = rssiStr.toInt();
  data.snr = snrStr.toInt();
  data.validData = true;
  
  return true;
}

// Format and send data to serial port for laptop/dashboard
void sendDataToSerial(const LocationData &data) {
  if (!data.validData) return;
  
  // Create CSV-style output for easy parsing by dashboard
  String output = String(data.timestamp) + "," +
                  String(data.latitude) + "," +
                  String(data.longitude) + "," +
                  String(data.altitude) + "," +
                  String(data.rssi) + "," +
                  String(data.snr);
  
  DEBUG_SERIAL.println(output);
}

// Print human-readable data for debugging
void printDebugInfo(const LocationData &data) {
  if (!data.validData) return;
  
  DEBUG_SERIAL.println("=== Received Data ===");
  DEBUG_SERIAL.println("Timestamp: " + String(data.timestamp) + " ms");
  DEBUG_SERIAL.println("Latitude: " + String(data.latitude / 10000000.0, 7) + "°");
  DEBUG_SERIAL.println("Longitude: " + String(data.longitude / 10000000.0, 7) + "°");
  DEBUG_SERIAL.println("Altitude: " + String(data.altitude / 1000.0, 3) + " m");
  DEBUG_SERIAL.println("RSSI: " + String(data.rssi) + " dBm");
  DEBUG_SERIAL.println("SNR: " + String(data.snr) + " dB");
  DEBUG_SERIAL.println("====================");
}

void loop() {
  // Check for incoming RYLR data
  if (RYLR.available()) {
    String receivedData = RYLR.readStringUntil('\n');
    
    if (parseRYLRResponse(receivedData, currentData)) {
      // Send formatted data to serial for dashboard
      sendDataToSerial(currentData);
      
      // Optional: Print debug information
      // Uncomment the line below for detailed debugging
      // printDebugInfo(currentData);
      
      // Reset valid flag after processing
      currentData.validData = false;
    } else {
      // Handle parsing errors or non-data messages
      if (receivedData.length() > 0) {
        DEBUG_SERIAL.println("Raw RYLR: " + receivedData);
      }
    }
  }
  
  // Small delay to prevent overwhelming the serial buffer
  delay(1);
}

// Optional: Function to send commands to RYLR module for configuration
void configureRYLR() {
  // Set network ID (should match transmitter)
  RYLR.println("AT+NETWORKID=5");
  delay(100);
  
  // Set address (different from transmitter)
  RYLR.println("AT+ADDRESS=1");
  delay(100);
  
  // Set RF parameters if needed
  // RYLR.println("AT+PARAMETER=12,7,1,7");
  // delay(100);
}

/*
DATA OUTPUT FORMAT:
The serial output will be in CSV format:
timestamp,latitude,longitude,altitude,rssi,snr

Example:
12345,123456789,987654321,1000,-45,10

Where:
- timestamp: milliseconds from transmitter
- latitude: degrees * 10^7 (divide by 10000000 for actual degrees)
- longitude: degrees * 10^7 (divide by 10000000 for actual degrees) 
- altitude: millimeters above mean sea level (divide by 1000 for meters)
- rssi: Received Signal Strength Indicator in dBm
- snr: Signal-to-Noise Ratio in dB
*/
