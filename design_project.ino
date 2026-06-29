#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Adafruit_BMP085.h>
#include <DHT.h>

// ------------------ LCD ------------------
LiquidCrystal_I2C lcd(0x27, 16, 2);

// ------------------ DHT11 ------------------
#define DHTPIN 2
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// ------------------ BMP180 ------------------
Adafruit_BMP085 bmp;

// ------------------ LED PINS ------------------
#define GREEN 9
#define YELLOW 10
#define RED 11

int page = 0;
String aiMessage = "Waiting...";
String gasDetected = "Normal";

// ------------------ AQI FUNCTION ------------------
int calculateAQI(int mq135) {
  if (mq135 <= 200) return map(mq135, 0, 200, 0, 50);
  else if (mq135 <= 300) return map(mq135, 200, 300, 51, 100);
  else if (mq135 <= 400) return map(mq135, 300, 400, 101, 200);
  else if (mq135 <= 500) return map(mq135, 400, 500, 201, 300);
  else return map(mq135, 500, 1023, 301, 500);
}

// ------------------ GAS DETECTION ------------------
String detectGas(int mq2, int mq135){
  String gases = "";
  if(mq2>400) gases += "Smoke/LPG ";
  else if(mq2>250) gases += "Gas ";
  if(mq135>400) gases += "AirPoll ";
  else if(mq135>300) gases += "ModPoll ";
  if(gases=="") gases="Normal";
  return gases;
}

// ------------------ SETUP ------------------
void setup() {
  Serial.begin(9600);
  dht.begin();
  bmp.begin();
  lcd.init();
  lcd.backlight();

  pinMode(GREEN, OUTPUT);
  pinMode(YELLOW, OUTPUT);
  pinMode(RED, OUTPUT);

  lcd.setCursor(0,0);
  lcd.print("System Starting");
  delay(2000);
}

// ------------------ LOOP ------------------
void loop() {
  // --- SENSOR READINGS ---
  float temp = dht.readTemperature();
  float hum = dht.readHumidity();
  float pressure = bmp.readPressure()/100.0;
  int mq2 = analogRead(A0);
  int mq135 = analogRead(A1);

  // --- DETECT GAS ---
  gasDetected = detectGas(mq2, mq135);

  // --- AQI ---
  int aqi = calculateAQI(mq135);

  // --- LED CONTROL ---
  digitalWrite(GREEN, LOW);
  digitalWrite(YELLOW, LOW);
  digitalWrite(RED, LOW);

  if(aqi<=100) digitalWrite(GREEN,HIGH);
  else if(aqi<=200) digitalWrite(YELLOW,HIGH);
  else digitalWrite(RED,HIGH);

  // --- SEND TO PYTHON ---
  Serial.print(temp); Serial.print(",");
  Serial.print(hum); Serial.print(",");
  Serial.print(pressure); Serial.print(",");
  Serial.print(mq2); Serial.print(",");
  Serial.println(mq135);

  // --- RECEIVE AI PREDICTION ---
  if(Serial.available()){
    aiMessage = Serial.readStringUntil('\n');
  }

  // --- LCD DISPLAY PAGES ---
  lcd.clear();
  if(page==0){
    lcd.setCursor(0,0); lcd.print("Temp:"); lcd.print(temp,1); lcd.print("C");
    lcd.setCursor(0,1); lcd.print("Hum:"); lcd.print(hum,1); lcd.print("%");
  } else if(page==1){
    lcd.setCursor(0,0); lcd.print("Pressure:");
    lcd.setCursor(0,1); lcd.print(pressure,1); lcd.print(" hPa");
  } else if(page==2){
    lcd.setCursor(0,0); lcd.print("MQ2:"); lcd.print(mq2);
    lcd.setCursor(0,1); lcd.print("MQ135:"); lcd.print(mq135);
  } else if(page==3){
    lcd.setCursor(0,0); lcd.print("Gases:");
    lcd.setCursor(0,1); lcd.print(gasDetected);
  } else if(page==4){
    lcd.setCursor(0,0); lcd.print("AQI:"); lcd.print(aqi);
    lcd.setCursor(0,1); lcd.print("AI:"); lcd.print(aiMessage.substring(0, min(16, aiMessage.length())));
  }

  page = (page+1)%5;  // Rotate through 5 pages
  delay(2000);
}