/*
 * ESP32 智慧養殖設備控制器
 * 自動讀取感測器，執行本地端平衡決定樹模型控制繼電器，並上傳數據
 */

#include <WiFi.h>
#include <HTTPClient.h>

// Wi-Fi 設定
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// FastAPI 伺服器網址
const char* serverName = "http://localhost:8000/api/sensor-data";

// 繼電器 GPIO 引腳定義
#define RELAY_PADDLE_WHEEL 18  // 水車繼電器引腳
#define RELAY_AERATOR_PUMP 19  // 打氣機繼電器引腳

// 類比感測器引腳模擬
#define PIN_DO_SENSOR 34
#define PIN_TEMP_SENSOR 35
#define PIN_PH_SENSOR 36

void setup() {
  Serial.begin(115200);
  
  // 設定繼電器引腳為輸出
  pinMode(RELAY_PADDLE_WHEEL, OUTPUT);
  pinMode(RELAY_AERATOR_PUMP, OUTPUT);
  
  // 預設關閉設備 (低電平觸發或高電平觸發依硬體決定)
  digitalWrite(RELAY_PADDLE_WHEEL, LOW);
  digitalWrite(RELAY_AERATOR_PUMP, LOW);
  
  // 連線 Wi-Fi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to Wi-Fi successfully!");
}

// 本地平衡決定樹預測演算法 (自動生成)
int predictAction(float do_val, float temp_val, float ph_val) {
  if (do_val < 4.81) {
    if (do_val < 3.27) {
      return 2; // 2
    } else {
      return 1; // 1
    }
  } else {
    if (do_val < 5.19) {
      if (temp_val < 30.31) {
        return 0; // 0
      } else {
        return 1; // 1
      }
    } else {
      return 0; // 0
    }
  }
}

void executeAction(int action) {
  if (action == 0) {
    // 正常：關閉水車與打氣機
    digitalWrite(RELAY_PADDLE_WHEEL, LOW);
    digitalWrite(RELAY_AERATOR_PUMP, LOW);
    Serial.println("設備狀態: 全部關閉 (正常)");
  } else if (action == 1) {
    // 警告：開啟打氣機，關閉水車
    digitalWrite(RELAY_PADDLE_WHEEL, LOW);
    digitalWrite(RELAY_AERATOR_PUMP, HIGH);
    Serial.println("設備狀態: 開啟打氣設備 (警告)");
  } else if (action == 2) {
    // 危急：水車與打氣機全部開啟
    digitalWrite(RELAY_PADDLE_WHEEL, HIGH);
    digitalWrite(RELAY_AERATOR_PUMP, HIGH);
    Serial.println("設備狀態: 水車與打氣機全開 (危急)");
  }
}

void loop() {
  // 1. 讀取感測器數值 (此處以類比讀取並映射做為範例)
  float do_val = (analogRead(PIN_DO_SENSOR) / 4095.0) * 10.0;     // 模擬溶氧量 0-10 mg/L
  float temp_val = 15.0 + (analogRead(PIN_TEMP_SENSOR) / 4095.0) * 25.0; // 模擬溫度 15-40 度
  float ph_val = 5.0 + (analogRead(PIN_PH_SENSOR) / 4095.0) * 5.0;       // 模擬 pH 5-10
  
  Serial.printf("讀取數據 - 溶氧量: %.2f mg/L | 溫度: %.2f C | pH: %.2f\n", do_val, temp_val, ph_val);
  
  // 2. 執行本地端樹狀決策模型
  int decision = predictAction(do_val, temp_val, ph_val);
  
  // 3. 執行硬體控制
  executeAction(decision);
  
  // 4. 上傳數據到 FastAPI 伺服器
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverName);
    http.addHeader("Content-Type", "application/json");
    
    String httpRequestData = "{\"do_val\":" + String(do_val, 2) + 
                             ",\"temp_val\":" + String(temp_val, 2) + 
                             ",\"ph_val\":" + String(ph_val, 2) + 
                             ",\"decision\":" + String(decision) + "}";
                             
    int httpResponseCode = http.POST(httpRequestData);
    Serial.print("HTTP POST 回傳碼: ");
    Serial.println(httpResponseCode);
    http.end();
  }
  
  delay(5000); // 每 5 秒循環一次
}
