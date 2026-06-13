def predict_action(do_val, temp_val, ph_val):
    """
    根據決定樹預測控制動作
    0: 全部關閉, 1: 開啟打氣機, 2: 開啟水車+打氣機
    """
    if do_val < 4.81:
        if do_val < 3.27:
            return 2  # 決策結果: 開啟水車與打氣機 (危急)
        else:
            return 1  # 決策結果: 開啟打氣機 (警告)
    else:
        if do_val < 5.19:
            if temp_val < 30.31:
                return 0  # 決策結果: 關閉水車與打氣機 (正常)
            else:
                return 1  # 決策結果: 開啟打氣機 (警告)
        else:
            return 0  # 決策結果: 關閉水車與打氣機 (正常)
