import streamlit as st, yfinance as yf, pandas as pd, ta, requests, pytz
from datetime import datetime
from urllib.parse import quote
from streamlit_autorefresh import st_autorefresh

# ========= CONFIG =========
MEU_NUMERO = "5542998195735"
MINHA_APIKEY = "4955675"
BANCA = 2000.0
RISCO = 0.10 # R$200
FUSO_BR = pytz.timezone("America/Sao_Paulo")

st.set_page_config(page_title="Tubarão B3 Auto 9:30 15h", layout="wide")
st.title("🦈 TERMINAL B3 V10 - AUTO 09:30 / 15:00 BRT")

# ========= RELÓGIO AUTOMÁTICO (atualiza a cada 60s) =========
st_autorefresh(interval=60*1000, key="relogio_b3")

agora_br = datetime.now(FUSO_BR)
hora_str = agora_br.strftime("%H:%M")
data_str = agora_br.strftime("%d/%m/%Y")

st.sidebar.metric("⏰ Hora Brasília", hora_str)
st.sidebar.write(f"📅 {data_str} - {agora_br.strftime('%A')}")
st.sidebar.divider()

# Horários que você pediu
HORARIOS_ALERTA = ["09:30", "15:00"]
# MODO TESTE: se quiser testar agora, descomente a linha abaixo:
# HORARIOS_ALERTA.append(hora_str)

st.sidebar.write("**Alertas programados:**")
for h in HORARIOS_ALERTA:
    st.sidebar.write(f"🔔 {h} BRT")

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

def fazer_scan_e_mandar(motivo="MANUAL"):
    lista=[]
    prog=st.progress(0, text="Varrendo B3...")
    for i,t in enumerate(TOP25):
        a=analisa(t)
        if not a:
            prog.progress((i+1)/len(TOP25))
            continue
        preco=a['preco']; score=a['score']; base=a['ativo']
        # Código opção exemplo Outubro (J) CALL 3% OTM
        strike_call = round(preco*1.03,2)
        strike_put = round(preco*0.97,2)
        cod_call = f"{base}J{int(strike_call)}" if strike_call<100 else f"{base}J{int(strike_call*10)/10}"
        cod_put = f"{base}V{int(strike_put)}" if strike_put<100 else f"{base}V{int(strike_put*10)/10}"

        if score >= 3:
            qtd = int((BANCA*RISCO)//50) # ex R$0,50 = 4 cont
            lista.append({"Ativo":base, "Preço":f"R${preco:.2f}", "Sinal":"🟢 CALL", "Score":score, "Tubarão":f"🐋 {a['vol_mult']:.1f}x" if a['tubarao'] else "-", "OPÇÃO":cod_call, "Strike":f"R${strike_call}", "Lote R$200":f"{qtd} cont", "RSI":f"{a['rsi']:.0f}", "Tipo":"CALL"})
        elif score <= -2:
            qtd = int((BANCA*RISCO)//50)
            lista.append({"Ativo":base, "Preço":f"R${preco:.2f}", "Sinal":"🔴 PUT", "Score":score, "Tubarão":f"🐋 {a['vol_mult']:.1f}x" if a['tubarao'] else "-", "OPÇÃO":cod_put, "Strike":f"R${strike_put}", "Lote R$200":f"{qtd} cont", "RSI":f"{a['rsi']:.0f}", "Tipo":"PUT"})
        prog.progress((i+1)/len(TOP25))
    prog.empty()

    df = pd.DataFrame(lista)
    if df.empty:
        msg = f"⚪ *B3 AUTO {hora_str} BRT {data_str}* - Sem sinal. Preservar R${BANCA:.0f} é lucro. [{motivo}]"
        st.warning("Sem sinal hoje. Melhor preservar banca.")
    else:
        df = df.sort_values("Score", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)
        msg = f"🦈 *B3 ALERTA AUTO {hora_str} BRT - {data_str}* [{motivo}]\nBanca R${BANCA:.0f} - Risco R${BANCA*RISCO:.0f}\n\n"
        for _, r in df.iterrows():
            msg += f"{r['Sinal']} {r['Ativo']} {r['OPÇÃO']} {r['Tubarão']} Score {r['Score']}\n"
        msg += "\nAlvo +100% parcial. Stop -50%."

    st.code(msg)
    try:
        url = f"https://api.callmebot.com/whatsapp.php?phone={MEU_NUMERO}&text={quote(msg)}&apikey={MINHA_APIKEY}"
        r = requests.get(url, timeout=15)
        if "queued" in r.text.lower() or "sent" in r.text.lower():
            st.success(f"✅ WhatsApp enviado {hora_str} BRT! {r.text}")
            st.session_state["ultimo_disparo"] = f"{data_str} {hora_str}"
            return True
        else:
            st.error(f"Erro CallMeBot: {r.text}")
    except Exception as e:
        st.error(f"Erro envio: {e}")
    return False

# ========= BOTÃO MANUAL =========
if st.button("🚀 SCAN MANUAL AGORA", type="primary"):
    fazer_scan_e_mandar("MANUAL")

st.divider()

# ========= LÓGICA AUTOMÁTICA 9:30 e 15h =========
if hora_str in HORARIOS_ALERTA and agora_br.weekday() < 5: # seg a sex
    chave_hoje = f"{data_str} {hora_str}"
    if "ultimo_disparo" not in st.session_state or st.session_state.ultimo_disparo!= chave_hoje:
        st.toast(f"Disparo automático {hora_str} BRT!", icon="🦈")
        fazer_scan_e_mandar(f"AUTO {hora_str}")
    else:
        st.info(f"✅ Alerta {hora_str} de hoje já enviado às {st.session_state.ultimo_disparo}")
else:
    proximo = [h for h in HORARIOS_ALERTA if h > hora_str]
    if proximo:
        st.info(f"⏳ Próximo alerta automático hoje às {proximo[0]} BRT. App se atualiza a cada 1 min.")
    else:
        st.info(f"⏳ Alertas de hoje encerrados. Próximo amanhã às {HORARIOS_ALERTA[0]} BRT.")