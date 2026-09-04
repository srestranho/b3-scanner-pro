import streamlit as st, yfinance as yf, pandas as pd, ta, requests
from datetime import datetime
from urllib.parse import quote

MEU_NUMERO = "5542998195735"
MINHA_APIKEY = "4955675"

st.set_page_config(page_title="B3 Scanner Pro", layout="wide")
st.title("📊 Scanner B3 - Top 10 + WhatsApp")

TOP10 = ["VALE3.SA","PETR4.SA","ITUB4.SA","BBAS3.SA","BBDC4.SA","B3SA3.SA","BPAC11.SA","PRIO3.SA","ABEV3.SA","ITSA4.SA"]

def analisa(ticker):
    df = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
    if df.empty or len(df)<30: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    close = df['Close']
    df['MM9'] = close.rolling(9).mean()
    df['MM21'] = close.rolling(21).mean()
    df['RSI'] = ta.momentum.RSIIndicator(close).rsi()
    macd = ta.trend.MACD(close)
    df['MACD'] = macd.macd(); df['MACD_S'] = macd.macd_signal()
    u, p = df.iloc[-1], df.iloc[-2]
    score=0; motivos=[]
    if p['MM9']<p['MM21'] and u['MM9']>u['MM21']: score+=3; motivos.append("Cruzamento ALTA")
    if u['RSI']<40: score+=2; motivos.append(f"RSI barato {u['RSI']:.0f}")
    if u['RSI']>70: score-=3; motivos.append(f"RSI caro {u['RSI']:.0f}")
    if u['MACD']>u['MACD_S']: score+=1; motivos.append("MACD comprador")
    if u['Close']>u['MM21']: score+=1
    sinal = "🟢 COMPRAR AGORA" if score>=3 else "🔴 VENDER/SAÍDA" if score<=-2 else "⚪ AGUARDAR"
    return {"Ativo":ticker.replace(".SA",""), "Preço":f"R$ {u['Close']:.2f}", "RSI":f"{u['RSI']:.0f}", "Score":score, "Sinal":sinal, "Por que":", ".join(motivos)}

if st.button("🚀 ANALISAR TOP 10 AGORA", type="primary"):
    dados=[]; prog=st.progress(0)
    for i,t in enumerate(TOP10):
        r=analisa(t)
        if r: dados.append(r)
        prog.progress((i+1)/len(TOP10))
    df = pd.DataFrame(dados).sort_values("Score", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)
    melhores = df[df['Score']>=3]
    if not melhores.empty:
        msg = f"🚀 *B3 TOP 10 - {datetime.now().strftime('%d/%m %H:%M')}*\n\n*MELHORES ENTRADAS:*\n"
        for _,r in melhores.iterrows(): msg += f"✅ {r['Ativo']} {r['Preço']} - {r['Por que']}\n"
        st.code(msg)
        try:
            url = f"https://api.callmebot.com/whatsapp.php?phone={MEU_NUMERO}&text={quote(msg)}&apikey={MINHA_APIKEY}"
            requests.get(url, timeout=10)
            st.balloons()
            st.success(f"Enviado pro seu WhatsApp!")
        except: st.error("Erro no envio")
    else: st.warning("Hoje sem sinal forte. Aguardar.")