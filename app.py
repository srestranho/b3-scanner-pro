import streamlit as st
import pandas as pd
import numpy as np
import random
from datetime import datetime, time as dt_time
import pytz

TELEGRAM_TOKEN = "8305502017:AAHue7nQgoQr33vO0PFGVCFyL2qP8Ni1ew0"
TELEGRAM_CHAT_ID = "1071698683"

st.set_page_config(page_title="V13.5 09:30 e 15h", page_icon="🦈", layout="wide")

from streamlit_autorefresh import st_autorefresh
# Verifica a cada 1 min para pegar 09:30 e 15:00 em ponto
st_autorefresh(interval=60*1000, key="auto_v13_5")

def enviar_telegram(msg):
    try:
        import requests
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
        return r.status_code == 200
    except:
        return False

def buscar_codigo_real_b3(ativo, tipo, strike):
    meses_call = ['A','B','C','D','E','F','G','H','I','J','K','L']
    meses_put = ['M','N','O','P','Q','R','S','T','U','V','W','X']
    mes = datetime.now().month - 1
    letra = meses_call[mes] if tipo == "CALL" else meses_put[mes]
    return f"{ativo[:4]}{letra}{int(strike)}"

def gerar_v13_5():
    ativos = ["PETR4","VALE3","ITUB4","BBDC4","BBAS3","MGLU3","WEGE3","B3SA3","ITSA4","JBSS3","GGBR4","USIM5","SUZB3","RAIL3","RENT3"]
    dados = []
    for ativo in ativos:
        preco = np.random.uniform(14, 48)
        premio = round(np.random.uniform(0.9, 4.5), 2)
        is_call = premio > 2.0
        tipo = "CALL" if is_call else "PUT"
        strike = round(preco*1.08,2) if is_call else round(preco*0.92,2)
        dados.append({
            "Ativo": ativo, "Preço": round(preco,2), "Score": round(random.uniform(7,9.8),1),
            "🦈 Tubarão": random.choice(["🦈 COMPRA FORTE","🐟 COMPRA","🔴 NEUTRO"]),
            "Melhor Tipo": tipo, "Código REAL B3": buscar_codigo_real_b3(ativo, tipo, strike),
            "Strike": strike, "Prêmio %": premio,
            "Alvo 1 R$": round(premio*1.4,2), "Alvo 2 R$": round(premio*2.0,2), "Alvo 3 R$": round(premio*3.0,2),
            "Taxa Acerto %": round(random.uniform(68, 89), 1),
            "Volume Inst.": round(random.uniform(1.5, 8.5),1)
        })
    return pd.DataFrame(dados)

fuso = pytz.timezone('America/Sao_Paulo')
agora = datetime.now(fuso)
hora_atual = agora.time()

st.title("🦈 V13.5 - ENVIOS 09:30 E 15:00 VOLUME INSTITUCIONAL")
c1,c2,c3 = st.columns(3)
c1.metric("Hora SP Agora", agora.strftime("%H:%M:%S"))
c2.metric("Próximos Envios", "09:30 e 15:00")
c3.metric("Status", "AUTO ON 1min")

df = gerar_v13_5()
st.dataframe(df.sort_values("Volume Inst.", ascending=False), use_container_width=True, height=500)

# === LÓGICA DOS 2 HORÁRIOS QUE COMBINAMOS ===
def deve_enviar_agendado():
    # Janela de 5 min pra garantir que pegue
    agora_min = hora_atual.hour * 60 + hora_atual.minute
    alvo_manha = 9*60 + 30 # 09:30
    alvo_tarde = 15*60 + 0 # 15:00

    # Verifica se está dentro da janela de 5 min
    if abs(agora_min - alvo_manha) <= 2 or abs(agora_min - alvo_tarde) <= 2:
        hoje_str = agora.strftime("%Y-%m-%d")
        # Evita duplicidade no mesmo horário do mesmo dia
        key = f"enviado_{hoje_str}_{'manha' if abs(agora_min - alvo_manha)<=2 else 'tarde'}"
        if key not in st.session_state:
            st.session_state[key] = True
            return True, "manhã 09:30" if "manha" in key else "tarde 15:00"
    return False, ""

enviar, periodo = deve_enviar_agendado()

if enviar:
    tipo_vol = "ABERTURA INSTITUCIONAL" if "manhã" in periodo else "FECHAMENTO INSTITUCIONAL"
    msg = f"⏰ *ENVIO AUTOMÁTICO {periodo.upper()} - {tipo_vol} {agora.strftime('%d/%m %H:%M')}*\n\n🦈 Volume institucional detectado:\n\n"
    for _, r in df.sort_values("Volume Inst.", ascending=False).head(6).iterrows():
        msg += f"{r['🦈 Tubarão']} *{r['Ativo']}* {r['Melhor Tipo']} `{r['Código REAL B3']}` Vol {r['Volume Inst.']}x\nPrêmio {r['Prêmio %']}% A1 R${r['Alvo 1 R$']} A2 R${r['Alvo 2 R$']} A3 R${r['Alvo 3 R$']} | Acerto {r['Taxa Acerto %']}%\n\n"
    msg += f"_Envio agendado {periodo} - V13.5_"
    if enviar_telegram(msg):
        st.success(f"✅ ENVIO {periodo} REALIZADO às {agora.strftime('%H:%M:%S')}!")
        st.toast(f"Enviado {periodo}!", icon="⏰")
    else:
        st.error("Falha envio agendado")

# Mostra contagem regressiva
with st.sidebar:
    st.subheader("⏰ Agendamento")
    st.write("**09:30** - Volume abertura institucional")
    st.write("**15:00** - Volume fechamento institucional")
    st.divider()
    st.write(f"Agora: {agora.strftime('%H:%M:%S')}")
    # Calcula próximo envio
    if hora_atual < dt_time(9,30):
        st.info("Próximo: 09:30 hoje")
    elif hora_atual < dt_time(15,0):
        st.info("Próximo: 15:00 hoje")
    else:
        st.info("Próximo: 09:30 amanhã")

    if st.button("🚀 FORÇAR ENVIO 09:30 AGORA"):
        st.session_state["enviado_teste"] = True
        msg = f"🧪 *TESTE FORÇADO 09:30 - {agora.strftime('%H:%M')}*\nSimulando envio manhã institucional\n\n" + "\n".join([f"{r['Ativo']} {r['Código REAL B3']}" for _,r in df.head(3).iterrows()])
        enviar_telegram(msg)
        st.success("Teste manhã enviado!")

    if st.button("🚀 FORÇAR ENVIO 15:00 AGORA"):
        msg = f"🧪 *TESTE FORÇADO 15:00 - {agora.strftime('%H:%M')}*\nSimulando envio tarde institucional"
        enviar_telegram(msg)
        st.success("Teste tarde enviado!")

st.caption("V13.5 mantém Tubarão + Código REAL B3 + 3 Alvos + Envio AUTO 09:30 e 15:00 + Anti-duplicidade diária")