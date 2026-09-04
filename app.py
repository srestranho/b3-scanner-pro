import streamlit as st, yfinance as yf, pandas as pd, ta, requests, pytz
from datetime import datetime
from urllib.parse import quote
from streamlit_autorefresh import st_autorefresh

# ====== SEUS DADOS - NÃO MUDA ======
MEU_NUMERO = "+5504298195735"
MINHA_APIKEY = "4955675"
BANCA = 2000.0
RISCO_REAIS = BANCA * 0.10  # R$200
FUSO_BR = pytz.timezone("America/Sao_Paulo")
HORARIOS_AUTO = ["09:30", "15:00"]  # <<< seus horários

# ====== CONFIG PÁGINA ======
st.set_page_config(page_title="B3 Tubarão V11 Auto+Manual", layout="wide")
st.title("🦈 TERMINAL B3 V11 - AUTO 09:30/15h + MANUAL")

# ====== RELÓGIO - ATUALIZA A CADA 60 SEGUNDOS ======
st_autorefresh(interval=60*1000, key="relogio_v11")
agora = datetime.now(FUSO_BR)
hora_atual = agora.strftime("%H:%M")
data_atual = agora.strftime("%d/%m/%Y")
dia_semana = agora.weekday()  # 0=segunda, 6=domingo

# Sidebar
st.sidebar.metric("⏰ Brasília Agora", hora_atual)
st.sidebar.write(f"📅 {data_atual}")
st.sidebar.info(f"🔔 Autos: {', '.join(HORARIOS_AUTO)} BRT")
st.sidebar.write("Deixe essa aba aberta das 9h às 15h30")

TOP25 = ["PETR4.SA","VALE3.SA","ITUB4.SA","BBDC4.SA","BBAS3.SA","B3SA3.SA","ABEV3.SA","BPAC11.SA","PRIO3.SA","ITSA4.SA","WEGE3.SA","MGLU3.SA","JBSS3.SA","LREN3.SA","GGBR4.SA","USIM5.SA","RENT3.SA","RAIL3.SA","ELET3.SA","SBSP3.SA","BBSE3.SA","CYRE3.SA","HAPV3.SA","RADL3.SA","SUZB3.SA"]

def analisa(ticker):
    try:
        df = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
        if df.empty or len(df)<30: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']
        df['MM9'] = close.rolling(9).mean()
        df['MM21'] = close.rolling(21).mean()
        df['RSI'] = ta.momentum.RSIIndicator(close).rsi()
        macd = ta.trend.MACD(close)
        df['MACD'] = macd.macd(); df['MACD_S'] = macd.macd_signal()
        vol_hoje = df['Volume'].iloc[-1]
        vol_media = df['Volume'].rolling(20).mean().iloc[-1]
        tubarao = vol_hoje > (vol_media * 1.3)
        vol_mult = vol_hoje/vol_media if vol_media>0 else 1
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

# FUNÇÃO ÚNICA QUE FAZ TUDO - MANUAL E AUTO USAM A MESMA
def executa_scan(motivo):
    st.subheader(f"📊 Scan {motivo} - {hora_atual} BRT")
    lista=[]
    barra = st.progress(0, text="Varrendo B3...")
    for i,t in enumerate(TOP25):
        a = analisa(t)
        if a:
            preco=a['preco']; score=a['score']; base=a['ativo']
            strike_c = round(preco*1.03,2)
            strike_p = round(preco*0.97,2)
            # Código legível
            cod_c = f"{base}J{int(strike_c)}"
            cod_p = f"{base}V{int(strike_p)}"
            qtd = int(RISCO_REAIS // 50) # se opção R$0,50 = 4 contratos
            if score >= 3:
                lista.append({"Ativo":base, "Preço":f"R${preco:.2f}", "Sinal":"🟢 CALL", "Score":score, "Tubarão":f"🐋 {a['vol_mult']:.1f}x" if a['tubarao'] else "-", "OPÇÃO":cod_c, "Strike":f"R${strike_c}", "Lote R$200":f"{qtd} cont", "RSI":f"{a['rsi']:.0f}", "Tipo":"CALL"})
            elif score <= -2:
                lista.append({"Ativo":base, "Preço":f"R${preco:.2f}", "Sinal":"🔴 PUT", "Score":score, "Tubarão":f"🐋 {a['vol_mult']:.1f}x" if a['tubarao'] else "-", "OPÇÃO":cod_p, "Strike":f"R${strike_p}", "Lote R$200":f"{qtd} cont", "RSI":f"{a['rsi']:.0f}", "Tipo":"PUT"})
        barra.progress((i+1)/len(TOP25))
    barra.empty()

    if not lista:
        df = pd.DataFrame()
        msg = f"⚪ *B3 {motivo} {hora_atual} BRT {data_atual}* - Sem sinal. Preservar R${BANCA:.0f}."
        st.warning("Sem sinal hoje. Preservar capital é o trade.")
    else:
        df = pd.DataFrame(lista).sort_values("Score", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)
        tubaroes = df[df['Tubarão'].str.contains("🐋")]
        if not tubaroes.empty:
            st.success(f"🦈 {len(tubaroes)} tubarões detectados!")
        msg = f"🦈 *B3 {motivo} {hora_atual} BRT {data_atual}*\nBanca R${BANCA:.0f} Risco R${RISCO_REAIS:.0f}\n\n"
        for _, r in df.iterrows():
            msg += f"{r['Sinal']} {r['Ativo']} {r['OPÇÃO']} {r['Tubarão']} Score {r['Score']}\n"
        msg += "\nAlvo +100% parcial. Stop -50%."

    st.code(msg)
    # ENVIA WHATSAPP
    try:
        url = f"https://api.callmebot.com/whatsapp.php?phone={MEU_NUMERO}&text={quote(msg)}&apikey={MINHA_APIKEY}"
        resp = requests.get(url, timeout=15)
        if "queued" in resp.text.lower() or "sent" in resp.text.lower():
            st.success(f"✅ WhatsApp {motivo} enviado! {hora_atual}")
            st.toast(f"WhatsApp {motivo} enviado!", icon="✅")
            return True
        else:
            st.error(f"Erro CallMeBot: {resp.text}")
    except Exception as e:
        st.error(f"Erro envio: {e}")
    return False

# ====== ÁREA MANUAL - SEMPRE FUNCIONA ======
col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 GERAR DADOS MANUAL AGORA", type="primary", use_container_width=True):
        executa_scan("MANUAL")

with col2:
    if st.button("🧪 TESTAR WHATSAPP", use_container_width=True):
        requests.get(f"https://api.callmebot.com/whatsapp.php?phone={MEU_NUMERO}&text={quote(f'Teste B3 V11 {hora_atual} BRT OK')}&apikey={MINHA_APIKEY}")
        st.success("Teste enviado!")

st.divider()

# ====== ÁREA AUTOMÁTICA - NÃO PRECISA CLICAR ======
# Só dispara se for dia de semana e hora bater
if dia_semana < 5: # 0-4 = seg a sex
    if hora_atual in HORARIOS_AUTO:
        chave = f"{data_atual} {hora_atual}"
        ultimo = st.session_state.get("ultimo_auto", "")
        if ultimo != chave:
            st.warning(f"⏰ HORÁRIO AUTO DETECTADO {hora_atual} BRT - Disparando...")
            ok = executa_scan(f"AUTO {hora_atual}")
            if ok:
                st.session_state["ultimo_auto"] = chave
                st.balloons()
        else:
            st.info(f"✅ Auto {hora_atual} de hoje já enviado em {ultimo}")
    else:
        # Mostra contagem regressiva
        proximos = [h for h in HORARIOS_AUTO if h > hora_atual]
        if proximos:
            st.info(f"⏳ Próximo auto hoje às {proximos[0]} BRT. App atualiza sozinho a cada 1 min. Pode clicar no MANUAL quando quiser.")
        else:
            st.info(f"✅ Autos de hoje encerrados. Amanhã às {HORARIOS_AUTO[0]} BRT.")
else:
    st.info("📴 Fim de semana - sem alertas auto.")