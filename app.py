import streamlit as st, yfinance as yf, pandas as pd, ta, requests, pytz
from datetime import datetime
from urllib.parse import quote
from streamlit_autorefresh import st_autorefresh

# ====== CONFIG ======
MEU_NUMERO = "5542998195735"
MINHA_APIKEY = "4955675"
BANCA = 2000.0
RISCO_REAIS = BANCA * 0.10
FUSO_BR = pytz.timezone("America/Sao_Paulo")
HORARIOS_AUTO = ["09:30", "15:00"]

st.set_page_config(page_title="B3 V12 Corrigido", layout="wide")
st.title("🦈 TERMINAL B3 V12 - Tabela Completa + Auto")

# ====== RELÓGIO ======
st_autorefresh(interval=60*1000, key="relogio_v12")
agora = datetime.now(FUSO_BR)
hora_atual = agora.strftime("%H:%M")
data_atual = agora.strftime("%d/%m/%Y")

st.sidebar.metric("⏰ Brasília", hora_atual)
st.sidebar.write(f"📅 {data_atual}")
st.sidebar.success(f"Autos: {', '.join(HORARIOS_AUTO)} BRT")

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
        return {"ativo":ticker.replace(".SA",""), "preco":float(u['Close']), "rsi":float(u['RSI']), "score":score, "tubarao":tubarao, "vol_mult":float(vol_mult), "close_todos": close}
    except: return None

# FUNÇÃO CORRIGIDA - SEMPRE MOSTRA TABELA COMPLETA
def executa_scan(motivo):
    st.divider()
    st.subheader(f"📊 Resultado {motivo} - {hora_atual} BRT")

    lista=[]
    barra = st.progress(0, text="Analisando 25 ativos...")
    # Para tabela completa vamos guardar todos
    tabela_completa = []

    for i,t in enumerate(TOP25):
        a = analisa(t)
        if a:
            tabela_completa.append({
                "Ativo": a['ativo'],
                "Preço": f"R$ {a['preco']:.2f}",
                "RSI": f"{a['rsi']:.0f}",
                "Score": a['score'],
                "Volume": f"{a['vol_mult']:.1f}x",
                "Tubarão": "🐋 SIM" if a['tubarao'] else "-",
                "Sinal": "🟢 CALL" if a['score']>=3 else "🔴 PUT" if a['score']<=-2 else "⚪ NEUTRO"
            })
            preco=a['preco']; score=a['score']; base=a['ativo']
            strike_c = round(preco*1.03,2)
            strike_p = round(preco*0.97,2)
            cod_c = f"{base}J{int(strike_c)}"
            cod_p = f"{base}V{int(strike_p)}"
            qtd = int(RISCO_REAIS // 50)
            if score >= 3:
                lista.append({"Ativo":base, "Preço":f"R${preco:.2f}", "Sinal":"🟢 CALL", "Score":score, "Tubarão":f"🐋 {a['vol_mult']:.1f}x" if a['tubarao'] else "-", "OPÇÃO":cod_c, "Strike":f"R${strike_c}", "Lote R$200":f"{qtd} cont", "RSI":f"{a['rsi']:.0f}"})
            elif score <= -2:
                lista.append({"Ativo":base, "Preço":f"R${preco:.2f}", "Sinal":"🔴 PUT", "Score":score, "Tubarão":f"🐋 {a['vol_mult']:.1f}x" if a['tubarao'] else "-", "OPÇÃO":cod_p, "Strike":f"R${strike_p}", "Lote R$200":f"{qtd} cont", "RSI":f"{a['rsi']:.0f}"})
        barra.progress((i+1)/len(TOP25))
    barra.empty()

    # 1. SEMPRE MOSTRA TABELA COMPLETA DOS 25
    st.write("### 📋 Tabela Completa TOP25 (como antes)")
    df_completo = pd.DataFrame(tabela_completa).sort_values("Score", ascending=False)
    st.dataframe(df_completo, use_container_width=True, hide_index=True, height=500)

    # 2. DESTAQUE SÓ DOS SINAIS
    if not lista:
        msg = f"B3 {motivo} {hora_atual} BRT {data_atual} - Sem sinal forte. Preservar R${BANCA:.0f}."
        st.warning("⚪ Sem sinal de CALL/PUT hoje. Preservar banca.")
        st.code(msg)
    else:
        df_sinais = pd.DataFrame(lista).sort_values("Score", ascending=False)
        st.write("### 🎯 Só Oportunidades CALL/PUT")
        st.dataframe(df_sinais, use_container_width=True, hide_index=True)

        msg = f"🦈 B3 {motivo} {hora_atual} BRT {data_atual} - {len(df_sinais)} sinais\nBanca R${BANCA:.0f} Risco R${RISCO_REAIS:.0f}\n\n"
        for _, r in df_sinais.iterrows():
            msg += f"{r['Sinal']} {r['Ativo']} {r['OPÇÃO']} {r['Tubarão']} Score {r['Score']}\n"
        st.code(msg)

    # ENVIA
    return envia_whatsapp(msg, motivo)

def envia_whatsapp(msg, motivo):
    # CORREÇÃO DO TESTE: CallMeBot precisa URL encode e sem emoji no teste
    try:
        # Limpa mensagem pra API não bloquear
        msg_limpa = msg.replace("🦈","").replace("🐋","").replace("🟢","CALL").replace("🔴","PUT").replace("⚪","")
        url = f"https://api.callmebot.com/whatsapp.php?phone={MEU_NUMERO}&text={quote(msg_limpa)}&apikey={MINHA_APIKEY}"
        st.write(f"🔗 Enviando para API...") # debug
        resp = requests.get(url, timeout=20)
        st.write(f"Resposta API: {resp.text}") # debug pra você ver
        if resp.status_code==200 and ("queued" in resp.text.lower() or "sent" in resp.text.lower() or "message" in resp.text.lower()):
            st.success(f"✅ WhatsApp {motivo} enviado {hora_atual} BRT!")
            st.balloons()
            return True
        else:
            st.error(f"❌ Falha API: {resp.text} | Status {resp.status_code}")
            st.warning("⚠️ Vá no WhatsApp e mande 'I allow callmebot to send me messages' pro +34 644 51 95 23 e ative de novo o link: https://api.callmebot.com/whatsapp.php?phone=5542998195735&text=teste&apikey=4955675")
            return False
    except Exception as e:
        st.error(f"Erro conexão: {e}")
        return False

# ====== BOTÕES ======
c1,c2,c3 = st.columns([2,1,1])
with c1:
    if st.button("🚀 GERAR TABELA COMPLETA AGORA", type="primary", use_container_width=True):
        executa_scan("MANUAL")

with c2:
    if st.button("🧪 TESTAR WHATSAPP CORRIGIDO", use_container_width=True):
        # TESTE SIMPLES SEM ACENTO NEM EMOJI
        msg_teste = f"TESTE B3 V12 {hora_atual} BRT {data_atual} - Banca R${BANCA:.0f} OK"
        envia_whatsapp(msg_teste, "TESTE")

with c3:
    if st.button("🔄 Limpar histórico auto", use_container_width=True):
        st.session_state["ultimo_auto"] = ""
        st.success("Histórico limpo!")

st.divider()

# ====== AUTO 9:30 e 15h ======
if agora.weekday() < 5:
    if hora_atual in HORARIOS_AUTO:
        chave = f"{data_atual} {hora_atual}"
        if st.session_state.get("ultimo_auto","")!= chave:
            st.warning(f"⏰ AUTO {hora_atual} BRT detectado! Disparando...")
            ok = executa_scan(f"AUTO {hora_atual}")
            if ok:
                st.session_state["ultimo_auto"] = chave
        else:
            st.info(f"✅ Auto {hora_atual} já enviado hoje.")
    else:
        prox = [h for h in HORARIOS_AUTO if h > hora_atual]
        if prox:
            st.info(f"⏳ Próximo auto {prox[0]} BRT. Manual funciona sempre.")
else:
    st.info("Fim de semana sem auto.")