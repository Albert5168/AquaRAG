import numpy as np
import pandas as pd
import sys

# =====================================================================
# 模型一：線性回歸 (Linear Regression) 用於感測器物理校正
# 應用場景：將 ESP32 傳回的類比電壓 (V) 精準對應到真實的溶氧量 (mg/L) 或 pH 值
# =====================================================================

class SensorCalibrator:
    def __init__(self):
        self.slope = 1.0  # 斜率 a
        self.intercept = 0.0  # 截距 b

    def train_calibration(self, voltages, actual_values):
        """
        利用最小平方法 (Ordinary Least Squares, OLS) 計算線性擬合 y = ax + b
        """
        X = np.array(voltages)
        y = np.array(actual_values)
        
        # 使用 NumPy 最小平方法公式計算
        n = len(X)
        sum_x = np.sum(X)
        sum_y = np.sum(y)
        sum_xx = np.sum(X * X)
        sum_xy = np.sum(X * y)
        
        # 計算斜率 a 與 截距 b
        self.slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x ** 2)
        self.intercept = (sum_y - self.slope * sum_x) / n
        
        print(f"[線性校正模型已建立] 擬合公式為: 物理值 = {self.slope:.4f} * 電壓(V) + ({self.intercept:.4f})")

    def calibrate(self, voltage):
        """
        輸入電壓值，回傳校正後的物理數值
        """
        return self.slope * voltage + self.intercept

# =====================================================================
# 模型二：隨機森林 (Random Forest) 用於多因子決策與特徵重要性評估
# 應用場景：綜合溶氧、水溫、pH，進行穩定的水車/打氣機聯合控制，防範單一決定樹的不穩定
# =====================================================================

def run_random_forest_demo():
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        
        print("\n=== 模型二：隨機森林 (Random Forest) 訓練與決策 ===")
        
        # 1. 建立模擬數據集
        np.random.seed(42)
        n_samples = 1000
        dos = np.random.uniform(2.0, 8.0, n_samples)
        temps = np.random.uniform(18.0, 34.0, n_samples)
        phs = np.random.uniform(6.5, 8.5, n_samples)
        
        X = np.column_stack((dos, temps, phs))
        y = []
        for i in range(n_samples):
            # 決定動作：0: 關閉, 1: 打氣, 2: 水車+打氣
            if X[i, 0] < 3.5:
                y.append(2)
            elif X[i, 0] < 5.0 or (X[i, 1] > 30.0 and X[i, 0] < 5.5):
                y.append(1)
            else:
                y.append(0)
        y = np.array(y)
        
        # 2. 分割訓練與測試集
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # 3. 建立並訓練隨機森林 (包含 100 棵決策樹)
        rf_model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        rf_model.fit(X_train, y_train)
        
        # 4. 評估準確度
        acc = rf_model.score(X_test, y_test)
        print(f"隨機森林分類準確度 (Accuracy): {acc * 100:.2f}%")
        
        # 5. 特徵重要性分析 (Feature Importance)
        # 用於了解哪一個感測因子對決定設備開關最關鍵
        importances = rf_model.feature_importances_
        feature_names = ["溶氧量 (DO)", "水溫 (Temp)", "酸鹼值 (pH)"]
        print("各感測特徵重要性 (Feature Importance):")
        for name, imp in zip(feature_names, importances):
            print(f"  - {name}: {imp * 100:.2f}%")
            
        # 6. 進行新樣本預測
        test_pond = np.array([[3.8, 31.0, 7.5]])  # 溶氧 3.8 (偏低), 溫度 31.0 (高溫)
        pred_action = rf_model.predict(test_pond)[0]
        actions = ["全部關閉", "開啟打氣機", "開啟水車與打氣機"]
        print(f"新資料點預測結果: {test_pond[0]} -> 設備執行: {actions[pred_action]}")
        
    except ImportError:
        print("\n[警告] 系統未安裝 scikit-learn。請執行: pip install scikit-learn 以啟用隨機森林模型。")

# =====================================================================
# 模型三：時間序列趨勢預測 (Holt Linear Trend) 用於清晨缺氧防範
# 應用場景：分析過去數小時的溶氧趨勢，預警未來 3 小時內是否會缺氧，提前開啟設備
# =====================================================================

class OxygenTrendForecaster:
    def __init__(self):
        pass

    def forecast_linear_trend(self, time_series_do, forecast_steps=3):
        """
        使用霍爾特線性趨勢 (Holt's Linear Trend) 概念，進行輕量級時間序列擬合與預測。
        此算法完全由簡單的遞歸平滑公式組成，極適合在一般電腦或邊緣端快速運算。
        """
        y = np.array(time_series_do)
        alpha = 0.3  # 水平平滑係數
        beta = 0.1   # 趨勢平滑係數
        
        # 初始化
        level = y[0]
        trend = y[1] - y[0]
        
        # 疊代平滑
        for i in range(1, len(y)):
            last_level = level
            level = alpha * y[i] + (1 - alpha) * (level + trend)
            trend = beta * (level - last_level) + (1 - beta) * trend
            
        # 進行未來預測
        forecasts = []
        for m in range(1, forecast_steps + 1):
            forecast_val = level + m * trend
            # 溶氧最低為 0
            forecasts.append(max(0.0, forecast_val))
            
        return forecasts

def run_time_series_demo():
    print("\n=== 模型三：時間序列溶氧衰退預估 (Holt Linear Trend) ===")
    
    # 模擬過去 8 個小時的整點溶氧監測數據 (呈現夜間持續下降趨勢)
    # 20:00 -> 03:00 的溶氧數據
    historical_do = [6.5, 6.1, 5.7, 5.2, 4.8, 4.4, 3.9, 3.5]
    
    forecaster = OxygenTrendForecaster()
    # 預測未來 3 個小時 (04:00, 05:00, 06:00) 的溶氧量
    predictions = forecaster.forecast_linear_trend(historical_do, forecast_steps=3)
    
    print("過去 8 小時溶氧監測記錄 (每小時):", historical_do)
    times = ["第 1 小時後 (04:00)", "第 2 小時後 (05:00)", "第 3 小時後 (06:00)"]
    
    danger_limit = 3.0  # 缺氧警戒線
    alert_triggered = False
    
    print("未來 3 小時預估趨勢:")
    for t, val in zip(times, predictions):
        status = "安全"
        if val < danger_limit:
            status = "⚠️ 警告：預估將低於警戒值 (3.0 mg/L)！"
            alert_triggered = True
        print(f"  - {t}: {val:.2f} mg/L [{status}]")
        
    if alert_triggered:
        print(f"{BOLD_RED}預警系統動作：偵測到未來 3 小時內有缺氧風險！提前啟動水車與打氣系統以防範未然。{RESET}")
    else:
        print("預警系統動作：水質指標安全，維持自動模式。")

# =====================================================================
# 主測試測試區
# =====================================================================

BOLD_RED='\033[1;31m'
RESET='\033[0m'

if __name__ == "__main__":
    # 1. 執行線性校正測試
    print("=== 模型一：線性回歸 (Linear Regression) 電壓-溶氧校正 ===")
    # 實驗室/現場合對數據：[電壓值 (V), 對應的標準溶氧液實測值 (mg/L)]
    mock_voltages = [1.2, 1.8, 2.4, 3.0, 3.6]
    mock_actuals = [2.1, 3.8, 5.3, 7.0, 8.6]
    
    calibrator = SensorCalibrator()
    calibrator.train_calibration(mock_voltages, mock_actuals)
    
    # 測試校正：當 ESP32 傳回電壓為 2.15V 時，轉換成物理值
    test_v = 2.15
    calibrated_val = calibrator.calibrate(test_v)
    print(f"輸入感測器電壓 {test_v}V -> 校正轉換後物理溶氧量: {calibrated_val:.2f} mg/L\n")
    
    # 2. 執行隨機森林測試
    run_random_forest_demo()
    
    # 3. 執行時間序列預估測試
    run_time_series_demo()
