/*
FIRMWARE FOR TEENSY 4.1
Configuration and implementation of GNSS MAX Click and RYLR99X transmission link
for real-time evaluation of Link Budget and integration with a dashboard for visualization.
@ Satvik Agrawal
 */

#include <SparkFun_u-blox_GNSS_v3.h>

#define RYLR        Serial2
#define WireGNSS    Wire // Connect using the Wire port. Change this if required
#define gnssAddress 0x42 // The default I2C address for u-blox modules is 0x42. Change this if required

typedef enum {
  LATITUDE,
  LONGITUDE,
  ALTITUDE
} Location;

SFE_UBLOX_GNSS myGNSS;

bool initGNSS() {
  WireGNSS.begin();

  if (!myGNSS.begin(WireGNSS, gnssAddress)) 
    return false;
  myGNSS.setI2COutput(COM_TYPE_UBX);
  return true;
}

void getLocation (int32_t location[3]) {
  if (myGNSS.getPVT(1) == true)
  {
    location[0] = myGNSS.getLatitude();
    location[1] = myGNSS.getLongitude();
    location[2] = myGNSS.getAltitudeMSL();
  } 
}

String parseRYLR(String input) {
  int start = input.indexOf(',') + 1;
  start = input.indexOf(',', start) + 1;
  int end = input.indexOf(',', start);
  String parsed = input.substring(start, end);
  parsed.trim();
  return parsed;  
}

void sendRYLR(String transmit) {
  String packet = "AT+SEND=0," + String(transmit.length()) + "," + transmit + "\r\n";
  RYLR.print(packet);
  delay(10);
}

String receiveRYLR() {
  if (RYLR.available()) {
    String receive = RYLR.readStringUntil('\n');
    receive = parseRYLR(receive.trim());
    return receive;
  }
  return "NO_DATA";
}


int main() {
  RYLR.begin(57600);

  if (initGNSS()) {
    Serial.println(F("u-blox GNSS detected."));
    status += "1";
  } else {
    Serial.println(F("u-blox GNSS not detected."));
    status += "0";
  }

  int32_t loc[3];

  while(1) {
    getLocation(loc);
    String data = String(millis()) + ";" +
              String(loc[LATITUDE]) + ";" +
              String(loc[LONGITUDE]) + ";" +
              String(loc[ALTITUDE]);

    sendRYLR(data);
    delay(2);
    
  }
}
