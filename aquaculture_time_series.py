import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

# 引入 statsmodels 時間序列庫
try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
except ImportError:
    print("Error: 缺少 statsmodels 庫，請先執行: pip install statsmodels")
    sys.exit(1)

# =====================================================================
# 1. 建立 24 小時池塘溶氧量監測數據 (Daytime to Early Morning)
# 數據特徵：下午光合作用強烈溶氧達最高點，日落後由於呼吸作用，溶氧持續衰退至清晨
# =====================================================================

# 建立 24 小時時間戳記
time_index = pd.date_range("2026-06-09 12:00:00", periods=24, freq="h")

# 24 小時的溶氧量變化 (mg/L)
do_data = [
    7.2, 7.8, 8.4, 8.9, 8.6, 8.1, 7.5, 6.9, 6.3, 5.8, 5.3, 4.9, # 12:00 - 23:00
    4.5, 4.1, 3.8, 3.5, 3.2, 2.9, 2.7, 2.5, 2.3, 2.2, 2.1, 2.0  # 00:00 - 11:00 (次日)
]

# 封裝成 Pandas Series
ts_do = pd.Series(do_data, index=time_index)

# 將前 18 個小時作為訓練數據 (12:00 - 次日 05:00)
# 預測接下來的 6 個小時 (次日 06:00 - 11:00)，這段期間是清晨溶氧最低的危急時刻
train_data = ts_do.iloc[:18]
test_data = ts_do.iloc[18:]

print("=== 歷史監測數據 (最後 6 筆訓練集) ===")
print(train_data.tail(6))
print("-" * 50)

# =====================================================================
# 2. 實作 ARIMA(1, 1, 1) 模型
# ARIMA 三個參數說明：
#   p=1 (自回歸項 AR)：利用前一個小時的數值來預測當前值。
#   d=1 (差分次數 I)：將序列差分 1 次以消除趨勢，使資料平穩（消除夜間持續衰退的趨勢）。
#   q=1 (移動平均項 MA)：利用前一個小時的預測誤差來修正當前預測。
# =====================================================================

print("\n[模型一：ARIMA(1, 1, 1) 自回歸整合移動平均模型]")
# 建立並擬合模型
arima_model = ARIMA(train_data, order=(1, 1, 1))
arima_result = arima_model.fit()

# 預測未來 6 步 (6 小時)，並獲取預測結果與信賴區間
arima_forecast = arima_result.get_forecast(steps=6)
arima_means = arima_forecast.predicted_mean
arima_ci = arima_forecast.conf_int(alpha=0.05)  # 95% 信賴區間

print("ARIMA 預測結果：")
for i in range(6):
    dt = test_data.index[i].strftime("%H:%M")
    pred_val = arima_means.iloc[i]
    actual_val = test_data.iloc[i]
    low_ci = arima_ci.iloc[i, 0]
    high_ci = arima_ci.iloc[i, 1]
    print(f"  - 時間: {dt} | 預測溶氧: {pred_val:.2f} mg/L (95% CI: {low_ci:.2f} ~ {high_ci:.2f}) | 實際值: {actual_val:.2f} mg/L")

# =====================================================================
# 3. 實作雙參數指數平滑模型 (Holt's Linear Exponential Smoothing)
# 參數說明：
#   trend='add'：加法趨勢。表示假設溶氧量隨時間呈線性下降趨勢。
#   seasonal=None：此處監測短期衰退，無須引入季節性週期。
# =====================================================================

print("\n[模型二：Holt 雙參數指數平滑模型 (Double Exponential Smoothing)]")
# 建立並擬合模型
holt_model = ExponentialSmoothing(train_data, trend='add', seasonal=None)
holt_result = holt_model.fit()

# 預測未來 6 小時
holt_forecast = holt_result.forecast(steps=6)

print("Holt 指數平滑預測結果：")
for i in range(6):
    dt = test_data.index[i].strftime("%H:%M")
    pred_val = holt_forecast.iloc[i]
    actual_val = test_data.iloc[i]
    print(f"  - 時間: {dt} | 預測溶氧: {pred_val:.2f} mg/L | 實際值: {actual_val:.2f} mg/L")

# =====================================================================
# 4. 決策預警邏輯集成
# =====================================================================

print("\n[智慧預警決策判定]")
danger_threshold = 3.0  # 溶氧低於 3.0 mg/L 判定為危急狀態，魚隻易窒息
alert_triggered = False
alert_time = None
alert_val = 0.0

# 檢查 ARIMA 預測是否會在未來 6 小時內跌破警戒線
for i in range(6):
    pred_val = arima_means.iloc[i]
    if pred_val < danger_threshold:
        alert_triggered = True
        alert_time = test_data.index[i].strftime("%H:%M")
        alert_val = pred_val
        break

if alert_triggered:
    print(f"\033[1;31m🚨 [水質警戒警告] ARIMA 模型預測在 {alert_time} 溶氧將跌至 {alert_val:.2f} mg/L，低於安全警戒值 (3.00 mg/L)！\033[0m")
    print("\033[1;32m💡 決策指令：向本地端 ESP32 發送中控信號，提前開啟水車與打氣設備，防止溶氧崩解。\033[0m")
else:
    print("✅ 預估未來 6 小時內溶氧指標安全。")
