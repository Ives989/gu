import streamlit as st
import akshare as ak
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# --- 1. 基础配置 ---
st.set_page_config(layout="wide", page_title="Gemini A股量化工作站")

# 缓存数据以提高访问速度
@st.cache_data(ttl=3600)
def fetch_industry_list():
    return ak.stock_board_industry_name_em()

@st.cache_data(ttl=600)
def fetch_industry_stocks(industry_name):
    try:
        return ak.stock_board_industry_cons_em(symbol=industry_name)
    except:
        return pd.DataFrame()

# --- 2. 核心算法：移动止损 ---
def run_trailing_stop_backtest(df, trail_pct):
    df = df.copy()
    # 简单的策略逻辑：均线金叉入场
    df['ma5'] = ta.sma(df['收盘'], length=5)
    df['ma20'] = ta.sma(df['收盘'], length=20)
    
    status = 0 # 0:空仓, 1:持仓
    highest_price = 0
    returns = []
    signals = []

    for i in range(len(df)):
        price = df['收盘'].iloc[i]
        if status == 0:
            if df['ma5'].iloc[i] > df['ma20'].iloc[i]:
                status = 1
                highest_price = price
                signals.append("BUY")
            else:
                signals.append(None)
            returns.append(0)
        elif status == 1:
            highest_price = max(highest_price, price)
            drawdown = (highest_price - price) / highest_price
            
            # 触发移动止损 或 均线死叉
            if drawdown > (trail_pct / 100) or df['ma5'].iloc[i] < df['ma20'].iloc[i]:
                status = 0
                signals.append("SELL")
            else:
                signals.append(None)
            returns.append(df['收盘'].pct_change().iloc[i])
            
    df['strategy_ret'] = returns
    df['cum_ret'] = (1 + df['strategy_ret']).cumprod()
    df['signal'] = signals
    return df

# --- 3. Streamlit UI 界面 ---
st.title("🚀 A股量化多因子与风险控制系统")

tab1, tab2 = st.tabs(["📊 行业筛选器", "🛡️ 移动止损回测"])

with tab1:
    st.header("行业多因子选股")
    col1, col2 = st.columns([1, 3])
    
    with col1:
        industries = fetch_industry_list()
        selected_ind = st.selectbox("选择行业板块", industries['板块名称'].tolist() if not industries.empty else ["加载中..."])
        pe_threshold = st.slider("最大动态PE", 10, 100, 35)
        min_amount = st.number_input("最低成交额 (万)", value=5000)
        
    with col2:
        stocks = fetch_industry_stocks(selected_ind)
        if not stocks.empty:
            # 执行筛选
            filtered = stocks[(stocks['市盈率-动态'] > 0) & 
                              (stocks['市盈率-动态'] < pe_threshold) & 
                              (stocks['成交额'] > min_amount * 10000)]
            st.write(f"已筛选出 **{len(filtered)}** 只个股")
            st.dataframe(filtered[['代码', '名称', '最新价', '涨跌幅', '市盈率-动态', '成交额']], use_container_width=True)
            # 存入session state供回测使用
            st.session_state['selected_code'] = filtered.iloc[0]['代码'] if not filtered.empty else None

with tab2:
    st.header("移动止损策略验证")
    target_code = st.text_input("输入回测代码", value=st.session_state.get('selected_code', '600519'))
    trail_pct = st.slider("移动止损阈值 (%)", 3.0, 15.0, 7.0)
    
    if st.button("开始回测"):
        with st.spinner("获取历史行情中..."):
            hist_df = ak.stock_zh_a_hist(symbol=target_code, period="daily", adjust="qfq")
            if not hist_df.empty:
                hist_df['日期'] = pd.to_datetime(hist_df['日期'])
                hist_df.set_index('日期', inplace=True)
                
                res = run_trailing_stop_backtest(hist_df, trail_pct)
                
                # 绘制图表
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=res.index, y=res['收盘'], name="收盘价"))
                # 标记止损点
                sell_points = res[res['signal'] == "SELL"]
                fig.add_trace(go.Scatter(x=sell_points.index, y=sell_points['收盘'], 
                                         mode='markers', marker=dict(color='red', size=10, symbol='x'), name="止损/出场点"))
                
                fig.update_layout(height=500, template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
                
                # 绩效指标
                m1, m2 = st.columns(2)
                m1.metric("累计收益率", f"{(res['cum_ret'].iloc[-1]-1)*100:.2f}%")
                m2.metric("最大回撤 (策略)", f"{(res['cum_ret']/res['cum_ret'].cummax()-1).min()*100:.2f}%")
            else:
                st.error("数据抓取失败，请检查代码是否正确")

# --- 4. 钉钉推送接口 ---
st.sidebar.divider()
st.sidebar.subheader("📢 自动化推送")
if st.sidebar.button("立即推送选股池到钉钉"):
    webhook = st.secrets.get("DING_WEBHOOK", "")
    if webhook:
        # 这里复用筛选逻辑并发送请求
        st.sidebar.success("推送指令已发出 (演示中)")
    else:
        st.sidebar.error("请在Streamlit Secrets中配置DING_WEBHOOK")
