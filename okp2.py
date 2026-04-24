import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import random

# --- ページ設定 ---
st.set_page_config(page_title="園芸施設 統合管理システム", layout="wide")

# --- Supabase接続設定 ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- データ操作関数 ---
def save_to_supabase(t, h):
    """データをSupabaseに挿入"""
    data = {"temperature": t, "humidity": h}
    supabase.table("environment").insert(data).execute()

def fetch_data_for_export(target_date):
    """指定日のデータを取得してDataFrameで返す"""
    start_time = f"{target_date}T00:00:00Z"
    end_time = f"{target_date}T23:59:59Z"
    
    response = supabase.table("environment") \
        .select("*") \
        .gte("created_at", start_time) \
        .lte("created_at", end_time) \
        .order("created_at") \
        .execute()
    
    return pd.DataFrame(response.data)

def fetch_recent_data(limit=30):
    """直近のデータを取得してグラフ用DFを返す"""
    response = supabase.table("environment") \
        .select("created_at, temperature, humidity") \
        .order("created_at", desc=True) \
        .limit(limit) \
        .execute()
    
    df = pd.DataFrame(response.data)
    if not df.empty:
        # 日本時間に変換（必要に応じて）
        df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_convert('Asia/Tokyo')
        df = df.sort_values('created_at')
    return df

# --- サイドバー：データエクスポート ---
st.sidebar.header("📁 データエクスポート")
export_date = st.sidebar.date_input("抽出する日付を選択", date.today())

if st.sidebar.button("CSVデータを生成"):
    export_df = fetch_data_for_export(export_date)
    
    if not export_df.empty:
        # 不要なID列などを除外して整理
        export_df = export_df[['created_at', 'temperature', 'humidity']]
        csv = export_df.to_csv(index=False).encode('utf-8-sig')
        st.sidebar.download_button(
            label=f"📥 {export_date} のCSVをダウンロード",
            data=csv, 
            file_name=f"env_data_{export_date}.csv", 
            mime='text/csv'
        )
    else:
        st.sidebar.warning("選択した日付のデータはありません。")

# --- メイン画面 ---
st.title("🌿 園芸施設 環境モニタリング (Cloud)")

col1, col2 = st.columns(2)
placeholder_temp = col1.empty()
placeholder_hum = col2.empty()
chart_placeholder = st.empty()

# --- 実行ループ ---
while True:
    # 1. データ取得（シミュレーション）と保存
    t = round(random.uniform(10.0, 35.0), 1)
    h = round(random.uniform(30.0, 90.0), 1)
    save_to_supabase(t, h)
    
    # 2. 表示用データの読み込み
    display_df = fetch_recent_data(30)

    if not display_df.empty:
        latest = display_df.iloc[-1]
        placeholder_temp.metric("🌡️ 温度", f"{latest['temperature']} °C")
        placeholder_hum.metric("💧 湿度", f"{latest['humidity']} %")

        # 3. グラフ更新
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=display_df['created_at'], y=display_df['temperature'], name="温度", line=dict(color='#FF4B4B', width=4)))
        fig.add_trace(go.Scatter(x=display_df['created_at'], y=display_df['humidity'], name="湿度", line=dict(color='#1C83E1', width=4)))
        fig.update_layout(hovermode="x unified", height=500)
        chart_placeholder.plotly_chart(fig, use_container_width=True)
    
    time.sleep(5) # クラウドDBへの負荷を考え、間隔を少し広げるのが一般的です
