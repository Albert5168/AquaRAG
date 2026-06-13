import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
from statsmodels.tsa.arima.model import ARIMA

# =====================================================================
# 1. 初始化 SQLite 資料表 (sensor_logs)
# 應用場景：保存由 ESP32 上傳的即時感測數據與控制決策
# =====================================================================

def init_sensor_db(db_path="rag_database.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 建立感測器歷史日誌資料表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sensor_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        do_val REAL,         -- 溶氧量 (mg/L)
        temp_val REAL,       -- 溫度 (°C)
        ph_val REAL,         -- pH 值
        decision INTEGER     -- 本地端決策 (0: 關閉, 1: 打氣, 2: 水車+打氣)
    )
    """)
    conn.commit()
    return conn

# =====================================================================
# 2. 模擬歷史資料寫入 (模擬 ESP32 過去 3 天的連續數據上傳)
# =====================================================================

def insert_mock_data_to_sql(conn, num_records=200):
    cursor = conn.cursor()
    
    # 先確認目前是否已有資料，避免重複寫入
    cursor.execute("SELECT COUNT(*) FROM sensor_logs")
    if cursor.fetchone()[0] > 0:
        print("資料庫已存在歷史感測日誌，跳過模擬寫入。")
        return
        
    print(f"正在寫入 {num_records} 筆模擬 IoT 感測日誌至資料庫中...")
    
    base_time = datetime.now() - timedelta(days=3)
    
    for i in range(num_records):
        log_time = base_time + timedelta(minutes=20 * i)
        time_str = log_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 模擬溶氧在深夜下降，白天上升的規律
        hour = log_time.hour
        if 22 <= hour or hour <= 6:
            # 夜間到清晨：溶氧量偏低 (2.5 - 4.5)
            do_val = round(random_uniform(2.2, 4.5), 2)
        else:
            # 白天：溶氧量充足 (5.0 - 8.5)
            do_val = round(random_uniform(5.0, 8.5), 2)
            
        temp_val = round(random_uniform(24.0, 32.0), 2)
        ph_val = round(random_uniform(7.0, 8.2), 2)
        
        # 定義決策標籤
        if do_val < 3.2:
            decision = 2
        elif do_val < 4.8 or (temp_val > 30.0 and do_val < 5.2):
            decision = 1
        else:
            decision = 0
            
        cursor.execute("""
        INSERT INTO sensor_logs (timestamp, do_val, temp_val, ph_val, decision)
        VALUES (?, ?, ?, ?, ?)
        """, (time_str, do_val, temp_val, ph_val, decision))
        
    conn.commit()
    print("模擬歷史資料寫入 SQL 完成。")

def random_uniform(low, high):
    return low + (high - low) * np.random.rand()

# =====================================================================
# 3. 從 SQL 載入資料並訓練機器學習模型 (Random Forest)
# =====================================================================

def train_rf_from_sql(conn):
    print("\n--- 步驟 A: 自 SQL 載入特徵資料並訓練隨機森林分類器 ---")
    
    # 使用 Pandas 直接下 SQL 語句讀取資料集
    sql_query = "SELECT do_val, temp_val, ph_val, decision FROM sensor_logs"
    df = pd.read_sql_query(sql_query, conn)
    
    print(f"從 SQL 讀取到數據，形狀為: {df.shape}")
    print("數據前 5 筆樣貌:")
    print(df.head())
    
    # 提取特徵與標籤
    X = df[['do_val', 'temp_val', 'ph_val']].values
    y = df['decision'].values
    
    # 訓練隨機森林模型
    rf = RandomForestClassifier(n_estimators=50, max_depth=4, random_state=42)
    rf.fit(X, y)
    print("✓ 隨機森林模型基於 SQL 資料庫歷史日誌訓練完成！")
    return rf

# =====================================================================
# 4. 從 SQL 載入時間序列數據並進行 ARIMA 預測
# =====================================================================

def run_arima_from_sql(conn):
    print("\n--- 步驟 B: 自 SQL 載入時間序列資料進行 ARIMA 預估 ---")
    
    # 撈取最近 24 筆以小時為單位的溶氧量監測數據 (按時間升序)
    # 為了展示，這裡直接使用 SQL 的分群平均 (Group by) 或直接 LIMIT
    sql_query = """
    SELECT timestamp, do_val 
    FROM sensor_logs 
    ORDER BY timestamp DESC 
    LIMIT 24
    """
    df_ts = pd.read_sql_query(sql_query, conn)
    
    # 轉回升序排列以利時間序列訓練
    df_ts = df_ts.iloc[::-1].reset_index(drop=True)
    df_ts['timestamp'] = pd.to_datetime(df_ts['timestamp'])
    df_ts.set_index('timestamp', inplace=True)
    
    print("自 SQL 讀取到的最近 24 小時歷史時間序列數據：")
    print(df_ts.tail(5))
    
    # 擬合 ARIMA 模型 (p=1, d=1, q=1)
    # 取出單維度 Series
    series = df_ts['do_val']
    model = ARIMA(series, order=(1, 1, 1))
    result = model.fit()
    
    # 預測接下來 3 個時間點 (後續 1小時, 2小時, 3小時)
    forecast = result.forecast(steps=3)
    
    print("\nARIMA 預估未來 3 個時間點溶氧量:")
    for i, val in enumerate(forecast):
        print(f"  - 未來第 {i+1} 步預測: {val:.2f} mg/L")
        
    danger_limit = 3.0
    if any(val < danger_threshold for val in forecast):
        print("\033[1;31m🚨 [SQL 時間序列預警] 警告：預測溶氧即將跌破 3.0 mg/L！觸發防禦控制開啟水車。\033[0m")
    else:
        print("✅ 預估狀態安全。")

danger_threshold = 3.0

# =====================================================================
# 主執行流程
# =====================================================================

if __name__ == "__main__":
    db_file = "rag_database.db"
    
    # 連線資料庫並初始化表
    db_conn = init_sensor_db(db_file)
    
    # 模擬數據注入
    insert_mock_data_to_sql(db_conn, num_records=200)
    
    # 執行 SQL 訓練隨機森林
    rf_model = train_rf_from_sql(db_conn)
    
    # 執行 SQL ARIMA 預估
    run_arima_from_sql(db_conn)
    
    db_conn.close()
