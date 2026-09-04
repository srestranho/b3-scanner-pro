import streamlit as st, yfinance as yf, pandas as pd, ta, requests, pytz
from datetime import datetime
from urllib.parse import quote
from streamlit_autorefresh import st_autorefresh

MEU_NUMERO = "5542998195735"
MINHA_APIKEY = "4955675"  # SUA API VALIDADA AGORA
BANCA = 2000.0
RISCO_REAIS = 200.0
FUSO_BR = pytz.timezone("America/Sao_Paulo")
HORARIOS_AUTO = ["09:30", "15:00"]

st.set_page_config(page_title="B3 V12 OK", layout="wide")
st.title("🦈 TERMINAL B3 V12 - API OK ✅")

st_autorefresh(interval=60*1000, key="v12_ok")
agora = datetime.now(FUSO_BR)
hora_atual = agora.strftime("%H:%M")
data_atual = agora.strftime("%d/%m/%Y")

st.sidebar.metric("⏰ Brasília", hora_atual)
st.sidebar.success("✅ API WhatsApp OK - 4955675")
st.sidebar.write(f"Autos: {', '.join(HORARIOS_AUTO)}")

TOP25 = ["PETR4.SA","VALE3.SA","ITUB4.SA","BBDC4.SA","BBAS3.SA","B3SA3.SA","ABEV3.SA","BPAC11.SA","PRIO3.SA","ITSA4.SA","WEGE3.SA","MGLU3.SA","JBSS3.SA","LREN3.SA","GGBR4.SA","USIM5.SA","RENT3.SA","RAIL3.SA","ELET3.SA","SBSP3.SA","BBSE3.SA","CYRE3.SA","HAPV3.SA","RADL3.SA","SUZB3.SA"]

def analisa(ticker):
    try:
        df = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
        if df.empty or len(df)<30: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']
        df['MM9'] = close.rolling(9).mean(); df['MM21'] = close.rolling(21).mean()
        df['RSI'] = ta.momentum.RSIIndicator(close).rsi()
        macd = ta.trend.MACD(close); df['MACD'] = macd.macd(); df['MACD_S'] = macd.macd_signal()
        vol_hoje = df['Volume'].iloc[-1]; vol_media = df['Volume'].rolling(20).mean().iloc[-1]
        tubarao = vol_hoje > (vol_media * 1.3); vol_mult = vol_hoje/vol_media if vol_media>0 else 1
        u,p = df.iloc[-1], df.iloc[-2]
        score=0
        if p['MM9']<p['MM21'] and u['MM9']>u['MM21']: score+=3
        if u['RSI']<40: score+=2
        if u['RSI']>70: score-=3
        if u['MACD']>u['MACD_S']: score+=1
        if u['Close']>u['MM21']: score+=1
        if tubarao and score>0: score+=2
        return {"ativo":ticker.replace(".SA",""), "preco":float(u['Close']), "rsi":float(u['RSI']), "score":score, "tubarao":tubarao, "vol_mult":float(vol_mult)}
    except: return None

def envia_whatsapp(msg):
    try:
        msg_limpa = msg.replace("🦈","").replace("🐋","").replace("🟢","CALL").replace("🔴","PUT")
        url = f"https://api.callmebot.com/whatsapp.php?phone={MEU_NUMERO}&text={quote(msg_limpa)}&apikey={MINHA_APIKEY}"
        resp = requests.get(url, timeout=15)
        return "queued" in resp.text.lower() or "sent" in resp.text.lower()
    except: return False

def executa_scan(motivo):
    lista=[]; tabela=[]
    barra = st.progress(0, text="Varrendo...")
    for i,t in enumerate(TOP25):
        a=analisa(t)
        if a:
            tabela.append({"Ativo":a['ativo'], "Preço":f"R$ {a['preco']:.2f}", "RSI":f"{a['rsi']:.0f}", "Score":a['score'], "Vol":f"{a['vol_mult']:.1f}x", "Tubarão":"🐋 SIM" if a['tubarao'] else "-", "Sinal":"🟢 CALL" if a['score']>=3 else "🔴 PUT" if a['score']<=-2 else "⚪ NEUTRO"})
            if a['score']>=3 or a['score']<=-2:
                strike = round(a['preco']*1.03,2) if a['score']>=3 else round(a['preco']*0.97,2)
                letra = "J" if a['score']>=3 else "V"
                cod = f"{a['ativo']}{letra}{int(strike)}"
                lista.append({"Ativo":a['ativo'], "Preço":f"R${a['preco']:.2f}", "Sinal":"🟢 CALL" if a['score']>=3 else "🔴 PUT", "Score":a['score'], "Tubarão":f"🐋 {a['vol_mult']:.1f}x" if a['tubarao'] else "-", "OPÇÃO":cod, "Strike":f"R${strike}", "Lote R$200":f"{int(RISCO_REAIS//50)} cont"})
        barra.progress((i+1)/len(TOP25))
    barra.empty()

    st.write("### 📋 Tabela Completa TOP25")
    st.dataframe(pd.DataFrame(tabela).sort_values("Score", ascending=False), use_container_width=True, hide_index=True, height=500)

    if lista:
        st.write("### 🎯 Oportunidades")
        df_s = pd.DataFrame(lista).sort_values("Score", ascending=False)
        st.dataframe(df_s, use_container_width=True, hide_index=True)
        msg = f"B3 {motivo} {hora_atual} BRT {data_atual} - {len(df_s)} sinais\n"
        for _, r in df_s.iterrows(): msg += f"{r['Sinal']} {r['Ativo']} {r['OPÇÃO']} {r['Tubarão']} Score {r['Score']}\n"
    else:
        msg = f"B3 {motivo} {hora_atual} BRT {data_atual} - Sem sinal. Preservar R${BANCA:.0f}."
        st.warning("Sem sinal forte.")

    st.code(msg)
    if envia_whatsapp(msg):
        st.success(f"✅ WhatsApp {motivo} enviado {hora_atual}!")
        st.balloons()
        return True
    else:
        st.error("Erro envio, mas tabela OK")
        return False

c1,c2 = st.columns(2)
with c1:
    if st.button("🚀 GERAR TABELA COMPLETA MANUAL", type="primary", use_container_width=True):
        executa_scan("MANUAL")
with c2:
    if st.button("🧪 TESTAR WHATSAPP", use_container_width=True):
        envia_whatsapp(f"TESTE B3 V12 {hora_atual} BRT API 4955675 OK")
        st.success("Teste enviado! Olha seu WhatsApp")

# AUTO
if agora.weekday()<5 and hora_atual in HORARIOS_AUTO:
    chave = f"{data_atual} {hora_atual}"
    if st.session_state.get("ultimo_auto","")!=chave:
        st.warning(f"⏰ AUTO {hora_atual} BRT! Disparando...")
        if executa_scan(f"AUTO {hora_atual}"):
            st.session_state["ultimo_auto"]=chave