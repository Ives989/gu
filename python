import streamlit as st
import akshare as ak
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import time

# 页面配置
st.set_page_config(layout="wide", page_title="A股量化实战平台")

# --- 数据抓取工具（带重试机制） ---
def get_data_with_retry(func, *args, **kwargs):
    for i in range(3): # 最多尝试3次
        try:
            return func(*args, **kwargs)
        except:
            time.sleep(2)
    return pd.DataFrame()

# --- 核心逻辑：移动止损算法 ---
def apply_trailing_stop(df, trail_pct):
    df = df.copy()
    df['highest_price'] = df['收盘'].cummax()
    df['drawdown'] = (df['highest_price'] - df['收盘']) / df['highest_price']
    df['stop_signal'] = df['drawdown'] > (trail_pct / 100)
    return df

st.title("🛡️ A股量化分析与移动止损系统")

# 侧边栏
with st.sidebar:
    st.header("1. 选股与参数")
    industry = st.selectbox("选择行业", ["半导体", "白酒", "银行", "光伏设备"])
    trail_val = st.slider("移动止损触发线 (%)", 3, 15, 8)
    
# 选股模块
st.subheader(f"🔍 {industry} 行业多因子筛选")
if st.button("开始扫描全市场"):
    with st.spinner("正在获取实时行情..."):
        stocks = get_data_with_retry(ak.stock_board_industry_cons_em, symbol=industry)
        if not stocks.empty:
            # 简单因子过滤：PE < 40 且 成交额活跃
            filtered = stocks[(stocks['市盈率-动态'] > 0) & (stocks['市盈率-动态'] < 40)]
            st.dataframe(filtered[['代码', '名称', '最新价', '涨跌幅', '市盈率-动态']])
            
            # 回测演示（以行业第一名为例）
            target_code = filtered.iloc[0]['代码']
            st.info(f"对行业龙头 {target_code} 进行移动止损压力测试")
            
            hist = get_data_with_retry(ak.stock_zh_a_hist, symbol=target_code, period="daily", adjust="qfq")
            hist['日期'] = pd.to_datetime(hist['日期'])
            hist = apply_trailing_stop(hist, trail_val)
            
            # 绘图
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist['日期'], y=hist['收盘'], name="股价"))
            # 标注止损点
            stops = hist[hist['stop_signal']]
            fig.add_trace(go.Scatter(x=stops['日期'], y=stops['收盘'], mode='markers', marker=dict(color='red'), name="触发止损"))
            st.plotly_chart(fig, use_container_width=True)
