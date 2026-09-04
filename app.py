import streamlit as st, yfinance as yf, pandas as pd, ta, requests
from datetime import datetime
from urllib.parse import quote

# CONFIG SEU
MEU_NUMERO = "554298195735"
MINHA_APIKEY = "4955675"
BANCA = 2000.0
RISCO_POR_TRADE = 0.10 # R$ 200

MESES_CALL = {1:'A',2:'B',3:'C',4:'D',5:'E',6:'F',7:'G',8:'H',9:'I',10:'J',11:'K',12:'L'}
MESES_PUT = {1:'M',2:'N',3:'O',4:'P',5:'Q',6:'R',7:'S',8:'T',9:'U',10:'V',11:'W',12:'X'}

st.set_page_config(page_title="Terminal Tubarão R$2000", layout="wide")
st.title(f"🦈 TERMINAL TUBARÃO - Banca R$ {BANCA:.0f}")

TOP25 = ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.","B3SA3.SA", "ABEV3.SA", "BPAC11.SA", "PRIO3.SA", "ITSA4.SA","WEGE3.SA", "MGLU3.SA", "JBSS3.SA", "LREN3.SA", "GGBR4.SA","USIM5.SA", "RENT3.SA", "RAIL3.SA", "ELET3.SA", "SBSP3.SA","BBSE3.SA", "CYRE3.SA", "HAPV3.SA", "RADL3.SA", "SUZB3.SA"]

def get_venc():
    hoje = datetime.now()
    m1 = hoje.month
    m2 = m1+1 if m1<12 else 1
    return [(m1, MESES_CALL[m1], MESES_PUT[m1]), (m2, MESES_CALL[m2], MESES_PUT[m2])]

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

        # Detector Tubarão
        vol_hoje = df['Volume'].iloc[-1]
        vol_media = df['Volume'].rolling(20).mean().iloc[-1]
        tubarao = vol_hoje > (vol_media * 1.3)
        vol_mult = vol_hoje / vol_media if vol_media>0 else 1

        u, p = df.iloc[-1], df.iloc[-2]
        score=0
        if p['MM9']<p['MM21'] and u['MM9']>u['MM21']: score+=3
        if u['RSI']<40: score+=2
        if u['RSI']>70: score-=3
        if u['MACD']>u['MACD_S']: score+=1
        if u['Close']>u['MM21']: score+=1
        if tubarao and score>0: score+=2 # Bonus tubarão
        if tubarao and score<0: score-=2

        return {"ativo": ticker.replace(".SA","")[:4], "ativo_full": ticker.replace(".SA",""), "preco": float(u['Close']), "rsi": float(u['RSI']), "score": score, "tubarao": tubarao, "vol_mult": float(vol_mult)}
    except:
        return None

v1, v2 = get_venc()
st.info(f"📅 Vencimentos: {v1[0]}º mês CALL={v1[1]}/PUT={v1[2]} | {v2[0]}º mês CALL={v2[1]}/PUT={v2[2]} | Banca R${BANCA:.0f} | Risco R${BANCA*RISCO_POR_TRADE:.0f}/trade")

if st.button("🦈 ESCANEAR TUBARÕES + OPÇÕES", type="primary"):
    lista=[]
    prog=st.progress(0)
    for i,t in enumerate(TOP25):
        a=analisa(t)
        if not a:
            prog.progress((i+1)/len(TOP25))
            continue

        preco=a['preco']; score=a['score']; base=a['ativo']; tub=a['tubarao']

        if score >= 3:
            strike = int(round(preco*1.05,2))
            cod1 = f"{base}{v1[1]}{strike}"
            cod2 = f"{base}{v2[1]}{strike}"
            lista.append({"Ativo":a['ativo_full'], "Preço":f"R${preco:.2f}", "Sinal":"🟢 CALL", "Score":score, "Tubarão":f"🐋 SIM {a['vol_mult']:.1f}x" if tub else "Não", "CÓDIGO":f"{cod1} ou {cod2}", "Strike":f"R${strike}", "Custo R$200":f"{int((BANCA*RISCO_POR_TRADE)/(0.5*100))} cont.", "RSI":f"{a['rsi']:.0f}", "Tipo":"CALL"})
        elif score <= -2:
            strike = int(round(preco*0.95,2))
            cod1 = f"{base}{v1[2]}{strike}"
            cod2 = f"{base}{v2[2]}{strike}"
            lista.append({"Ativo":a['ativo_full'], "Preço":f"R${preco:.2f}", "Sinal":"🔴 PUT", "Score":score, "Tubarão":f"🐋 SIM {a['vol_mult']:.1f}x" if tub else "Não", "CÓDIGO":f"{cod1} ou {cod2}", "Strike":f"R${strike}", "Custo R$200":f"{int((BANCA*RISCO_POR_TRADE)/(0.5*100))} cont.", "RSI":f"{a['rsi']:.0f}", "Tipo":"PUT"})
        else:
            lista.append({"Ativo":a['ativo_full'], "Preço":f"R${preco:.2f}", "Sinal":"⚪ FORA", "Score":score, "Tubarão":f"🐋 SIM {a['vol_mult']:.1f}x" if tub else "Não", "CÓDIGO":"-", "Strike":"-", "Custo R$200":"-", "RSI":f"{a['rsi']:.0f}", "Tipo":"AGUARDAR"})
        prog.progress((i+1)/len(TOP25))

    df = pd.DataFrame(lista).sort_values("Score", ascending=False)

    # Destaque Tubarões
    tubaroes = df[df['Tubarão'].str.contains("SIM")]
    if not tubaroes.empty:
        st.subheader("🦈 ONDE OS TUBARÕES ESTÃO ENTRANDO AGORA")
        st.dataframe(tubaroes, use_container_width=True, hide_index=True)
    else:
        st.warning("Nenhum volume institucional anormal hoje. Mercado sem tubarão.")

    st.subheader("📋 Todos os 25 ativos")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Mensagem WhatsApp só com tubarões + score alto
    operaveis = df[(df['Tipo']!='AGUARDAR') & (df['Tubarão'].str.contains("SIM"))]
    if not operaveis.empty:
        msg = f"🦈 *TUBARÕES R${BANCA:.0f} - {datetime.now().strftime('%d/%m %H:%M')}*\nFluxo estrangeiro voltou +R$3.2bi\n\n"
        for _, r in operaveis.iterrows():
            msg += f"{r['Sinal']} {r['Ativo']} {r['CÓDIGO'].split(' ou ')[0]} Vol {r['Tubarão']}\n"
        msg += "\nSiga o tubarão. Meta +100% e sai."
        st.code(msg)
        try:
            url = f"https://api.callmebot.com/whatsapp.php?phone={MEU_NUMERO}&text={quote(msg)}&apikey={MINHA_APIKEY}"
            requests.get(url, timeout=10)
            st.balloons()
            st.success(f"Enviado pro 42 99819-5735! {len(operaveis)} oportunidades com tubarão.")
        except: st.error("Erro WhatsApp")
    else:
        st.info("Sem oportunidade com tubarão + sinal hoje. Isso é bom - te protege de perder R$200.")

st.caption("Como os grandes invest")