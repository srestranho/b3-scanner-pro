import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import pytz
import random

st.set_page_config(page_title="Radar V13.1 Tubarao PRO", page_icon="🦈", layout="wide")

TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

def enviar_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False, "Configure Secrets"
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
        return r.status_code == 200, r.text
    except Exception as e:
        return False, str(e)

def gerar_dados_tubarao():
    ativos = ["PETR4", "VALE3", "ITUB4", "BBDC4", "BBAS3", "MGLU3", "LREN3", "WEGE3", "ABEV3", "B3SA3",
              "ITSA4", "JBSS3", "GGBR4", "USIM5", "SUZB3", "RAIL3", "RENT3", "CIEL3", "COGN3", "CYRE3",
              "ELET3", "GOLL4", "AZUL4", "VIIA3", "CVCB3"]
    dados = []
    for ativo in ativos:
        preco = np.random.uniform(12, 48)
        rsi = np.random.uniform(28, 78)
        fluxo_tub = random.choice(["COMPRA FORTE", "COMPRA", "NEUTRO", "VENDA", "VENDA FORTE"])
        tub_icone = "🦈" if "FORTE" in fluxo_tub else "🐟" if "COMPRA" in fluxo_tub else "🔴" if "VENDA" in fluxo_tub else "⚪"
        premio_call = np.random.uniform(0.3, 4.2)
        premio_put = np.random.uniform(0.3, 3.8)
        
        if premio_call > premio_put:
            melhor_tipo = "CALL"
            melhor_premio = premio_call
            strike = round(preco * 1.07, 2)
            codigo = f"{ativo[:4]}{random.choice(['I','J','K'])}{int(strike*100):05d}"
            entrada = "VENDA COBERTA"
        else:
            melhor_tipo = "PUT"
            melhor_premio = premio_put
            strike = round(preco * 0.93, 2)
            codigo = f"{ativo[:4]}{random.choice(['U','V','W'])}{int(strike*100):05d}"
            entrada = "VENDA DE PUT - SEGURO"
            
        dados.append({
            "Ativo": ativo, "Preço": round(preco,2), "RSI (14)": round(rsi,1),
            "Score": round(np.random.uniform(6,9.9),2), "Vol (k)": np.random.randint(80,8000),
            "🦈 Tubarão": f"{tub_icone} {fluxo_tub}", "Fluxo Vol x": round(np.random.uniform(0.5,8.5),1),
            "Melhor Tipo": melhor_tipo, "Código Melhor Opção": codigo, "Strike": strike,
            "Prêmio %": round(melhor_premio,2), "CALL %": round(premio_call,2), "PUT %": round(premio_put,2),
            "Entrada Sugerida": entrada, "Venc": "20/09"
        })
    return pd.DataFrame(dados)

# HEADER
c1,c2,c3 = st.columns([3,1,1])
with c1: st.title("🦈 RADAR V13.1 TUBARÃO PRO")
with c2: st.metric("Telegram", "✅" if TELEGRAM_TOKEN else "⚠️ Configurar")
with c3: 
    fuso = pytz.timezone('America/Sao_Paulo')
    st.metric("SP", datetime.now(fuso).strftime("%H:%M:%S"))

df = gerar_dados_tubarao()
tab1, tab2, tab3 = st.tabs(["📊 TOP25 + TUBARÃO", "🎯 MELHOR CÓDIGO", "🦈 SÓ TUBARÃO FORTE"])

with tab1:
    if st.button("🚀 GERAR TABELA COMPLETA MANUAL", type="primary", use_container_width=True):
        st.dataframe(df.sort_values(by="Score", ascending=False), use_container_width=True, height=700)
        st.download_button("📥 Baixar CSV", df.to_csv(index=False).encode('utf-8'), "tubarao_v13_1.csv", "text/csv")
        msg = f"🦈 TOP25 TUBARÃO {datetime.now().strftime('%H:%M')} - {len(df)} ativos\n"
        for _, r in df.head(5).iterrows():
            msg += f"{r['🦈 Tubarão']} {r['Ativo']} | {r['Melhor Tipo']} {r['Código Melhor Opção']} {r['Prêmio %']}%\n"
        enviar_telegram(msg)

with tab2:
    st.dataframe(df[["Ativo","Preço","🦈 Tubarão","Melhor Tipo","Código Melhor Opção","Strike","Prêmio %","Entrada Sugerida"]], use_container_width=True, height=600)
    if st.button("📲 ENVIAR CÓDIGOS", use_container_width=True):
        msg = "🎯 MELHORES CÓDIGOS\n"
        for _, r in df.head(8).iterrows():
            msg += f"{r['Ativo']} {r['Melhor Tipo']} {r['Código Melhor Opção']} R${r['Strike']} {r['Prêmio %']}% - {r['Entrada Sugerida']}\n"
        enviar_telegram(msg)
        st.success("Enviado!")

with tab3:
    df_tub = df[df["🦈 Tubarão"].str.contains("FORTE")]
    st.dataframe(df_tub, use_container_width=True)
    if st.button("🚨 ALERTA TUBARÃO FORTE"):
        msg = "🦈🚨 TUBARÃO FORTE\n"
        for _, r in df_tub.iterrows():
            msg += f"{r['🦈 Tubarão']} {r['Ativo']} {r['Código Melhor Opção']}\n"
        enviar_telegram(msg)