import os
import random
import numpy as np

# Define Features: 0: DO (mg/L), 1: Temp (°C), 2: pH
# Define Actions: 
#   0: 正常運作 (水車與打氣均關閉)
#   1: 啟動打氣設備 (DO偏低或高溫)
#   2: 啟動水車與打氣設備 (DO極低，危急狀態)

class DecisionTreeNode:
    def __init__(self, feature=None, threshold=None, left=None, right=None, value=None):
        self.feature = feature
        self.threshold = threshold
        self.left = left
        self.right = right
        self.value = value

    def is_leaf(self):
        return self.value is not None

def calculate_gini(y):
    if len(y) == 0:
        return 0
    counts = np.bincount(y)
    probabilities = counts / len(y)
    return 1.0 - np.sum(probabilities ** 2)

def split_dataset(X, y, feature, threshold):
    left_mask = X[:, feature] < threshold
    right_mask = ~left_mask
    return X[left_mask], y[left_mask], X[right_mask], y[right_mask]

def find_best_split(X, y):
    best_gini_gain = -1
    best_split = {}
    n_samples, n_features = X.shape
    current_gini = calculate_gini(y)
    
    for feature in range(n_features):
        thresholds = np.unique(X[:, feature])
        for threshold in thresholds:
            X_left, y_left, X_right, y_right = split_dataset(X, y, feature, threshold)
            if len(y_left) == 0 or len(y_right) == 0:
                continue
                
            gini_left = calculate_gini(y_left)
            gini_right = calculate_gini(y_right)
            
            # Weighted average Gini impurity
            p_left = len(y_left) / n_samples
            p_right = len(y_right) / n_samples
            new_gini = p_left * gini_left + p_right * gini_right
            gini_gain = current_gini - new_gini
            
            if gini_gain > best_gini_gain:
                best_gini_gain = gini_gain
                best_split = {
                    "feature": feature,
                    "threshold": threshold,
                    "X_left": X_left,
                    "y_left": y_left,
                    "X_right": X_right,
                    "y_right": y_right
                }
    return best_split

def build_tree(X, y, depth=0, max_depth=3):
    n_samples, n_features = X.shape
    
    # Base cases: pure node, no samples, or max depth reached
    if len(np.unique(y)) == 1 or n_samples < 5 or depth >= max_depth:
        leaf_value = np.argmax(np.bincount(y)) if len(y) > 0 else 0
        return DecisionTreeNode(value=int(leaf_value))
        
    split = find_best_split(X, y)
    if not split:
        leaf_value = np.argmax(np.bincount(y)) if len(y) > 0 else 0
        return DecisionTreeNode(value=int(leaf_value))
        
    left_child = build_tree(split["X_left"], split["y_left"], depth + 1, max_depth)
    right_child = build_tree(split["X_right"], split["y_right"], depth + 1, max_depth)
    
    return DecisionTreeNode(
        feature=split["feature"],
        threshold=split["threshold"],
        left=left_child,
        right=right_child
    )

def generate_aquaculture_data(n_samples=500):
    np.random.seed(42)
    # DO range: 2.0 to 8.0 mg/L
    dos = np.random.uniform(2.0, 8.0, n_samples)
    # Temp range: 18.0 to 34.0 °C
    temps = np.random.uniform(18.0, 34.0, n_samples)
    # pH range: 6.5 to 8.5
    phs = np.random.uniform(6.5, 8.5, n_samples)
    
    X = np.column_stack((dos, temps, phs))
    y = []
    
    for i in range(n_samples):
        do = X[i, 0]
        temp = X[i, 1]
        ph = X[i, 2]
        
        # Expert logic rules for training label assignment
        if do < 3.2:
            action = 2  # 危急：水車與打氣全部開啟
        elif do < 4.8 or (temp > 30.0 and do < 5.2):
            action = 1  # 警告：開啟打氣設備
        else:
            action = 0  # 正常：全部關閉
        y.append(action)
        
    return X, np.array(y, dtype=np.intp)

def generate_python_rules(node, feature_names):
    if node.is_leaf():
        actions = ["關閉水車與打氣機 (正常)", "開啟打氣機 (警告)", "開啟水車與打氣機 (危急)"]
        return f"    return {node.value}  # 決策結果: {actions[node.value]}\n"
        
    f_name = feature_names[node.feature]
    code = f"    if {f_name} < {node.threshold:.2f}:\n"
    # Indent left child
    left_code = generate_python_rules(node.left, feature_names)
    code += "\n".join("    " + line if line else "" for line in left_code.split("\n")[:-1]) + "\n"
    code += f"    else:\n"
    # Indent right child
    right_code = generate_python_rules(node.right, feature_names)
    code += "\n".join("    " + line if line else "" for line in right_code.split("\n")[:-1]) + "\n"
    return code

def generate_cpp_rules(node, indent="  "):
    if node.is_leaf():
        return f"{indent}return {node.value}; // {node.value}\n"
        
    feature_map = ["do_val", "temp_val", "ph_val"]
    f_name = feature_map[node.feature]
    
    code = f"{indent}if ({f_name} < {node.threshold:.2f}) {{\n"
    code += generate_cpp_rules(node.left, indent + "  ")
    code += f"{indent}}} else {{\n"
    code += generate_cpp_rules(node.right, indent + "  ")
    code += f"{indent}}}\n"
    return code

def main():
    print("Generating training data...")
    X, y = generate_aquaculture_data(500)
    
    print("Training Balanced Decision Tree Model (max_depth=3)...")
    tree = build_tree(X, y, max_depth=3)
    
    feature_names = ["do_val", "temp_val", "ph_val"]
    
    # 1. Generate Python Code
    py_rules_code = (
        "def predict_action(do_val, temp_val, ph_val):\n"
        "    \"\"\"\n"
        "    根據決定樹預測控制動作\n"
        "    0: 全部關閉, 1: 開啟打氣機, 2: 開啟水車+打氣機\n"
        "    \"\"\"\n"
    )
    py_rules_code += generate_python_rules(tree, feature_names)
    
    py_output = "aquaculture_rules.py"
    with open(py_output, "w", encoding="utf-8") as f:
        f.write(py_rules_code)
    print(f"Python 決策程式碼已輸出至: {py_output}")
    
    # 2. Generate ESP32 Arduino Code
    cpp_rules = generate_cpp_rules(tree)
    arduino_code = f"""/*
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

void setup() {{
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
  while (WiFi.status() != WL_CONNECTED) {{
    delay(500);
    Serial.print(".");
  }}
  Serial.println("\\nConnected to Wi-Fi successfully!");
}}

// 本地平衡決定樹預測演算法 (自動生成)
int predictAction(float do_val, float temp_val, float ph_val) {{
{cpp_rules}}}

void executeAction(int action) {{
  if (action == 0) {{
    // 正常：關閉水車與打氣機
    digitalWrite(RELAY_PADDLE_WHEEL, LOW);
    digitalWrite(RELAY_AERATOR_PUMP, LOW);
    Serial.println("設備狀態: 全部關閉 (正常)");
  }} else if (action == 1) {{
    // 警告：開啟打氣機，關閉水車
    digitalWrite(RELAY_PADDLE_WHEEL, LOW);
    digitalWrite(RELAY_AERATOR_PUMP, HIGH);
    Serial.println("設備狀態: 開啟打氣設備 (警告)");
  }} else if (action == 2) {{
    // 危急：水車與打氣機全部開啟
    digitalWrite(RELAY_PADDLE_WHEEL, HIGH);
    digitalWrite(RELAY_AERATOR_PUMP, HIGH);
    Serial.println("設備狀態: 水車與打氣機全開 (危急)");
  }}
}}

void loop() {{
  // 1. 讀取感測器數值 (此處以類比讀取並映射做為範例)
  float do_val = (analogRead(PIN_DO_SENSOR) / 4095.0) * 10.0;     // 模擬溶氧量 0-10 mg/L
  float temp_val = 15.0 + (analogRead(PIN_TEMP_SENSOR) / 4095.0) * 25.0; // 模擬溫度 15-40 度
  float ph_val = 5.0 + (analogRead(PIN_PH_SENSOR) / 4095.0) * 5.0;       // 模擬 pH 5-10
  
  Serial.printf("讀取數據 - 溶氧量: %.2f mg/L | 溫度: %.2f C | pH: %.2f\\n", do_val, temp_val, ph_val);
  
  // 2. 執行本地端樹狀決策模型
  int decision = predictAction(do_val, temp_val, ph_val);
  
  // 3. 執行硬體控制
  executeAction(decision);
  
  // 4. 上傳數據到 FastAPI 伺服器
  if (WiFi.status() == WL_CONNECTED) {{
    HTTPClient http;
    http.begin(serverName);
    http.addHeader("Content-Type", "application/json");
    
    String httpRequestData = "{{\\"do_val\\":" + String(do_val, 2) + 
                             ",\\"temp_val\\":" + String(temp_val, 2) + 
                             ",\\"ph_val\\":" + String(ph_val, 2) + 
                             ",\\"decision\\":" + String(decision) + "}}";
                             
    int httpResponseCode = http.POST(httpRequestData);
    Serial.print("HTTP POST 回傳碼: ");
    Serial.println(httpResponseCode);
    http.end();
  }}
  
  delay(5000); // 每 5 秒循環一次
}}
"""
    
    cpp_output = "esp32_controller.ino"
    with open(cpp_output, "w", encoding="utf-8") as f:
        f.write(arduino_code)
    print(f"ESP32 Arduino 專案檔已輸出至: {cpp_output}")
    print("模型訓練與建置完全成功！")

if __name__ == "__main__":
    main()
