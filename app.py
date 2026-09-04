import streamlit as st, yfinance as yf, pandas as pd, ta, requests
from datetime import datetime
from urllib.parse import quote

MEU_NUMERO = "5542998195735"
MINHA_APIKEY = "4955675"
BANCA = 2000.0
RISCO_POR_TRADE = 0.10

# Tabela B3 de vencimento
MESES_CALL = {1:'A',2:'B',3:'C',4:'D',5:'E',6:'F',7:'G',8:'H',9:'I',10:'J',11:'K',12:'L'}
MESES_PUT = {1:'M',2:'N',3:'O',4:'P',5:'Q',6:'R',7:'S',8:'T',9:'U',10:'V',11:'W',12:'X'}

st.set_page_config(page_title="B3 Código Opção", layout="wide")
st.title(f"💰 Scanner R$ {BANCA:.0f} - Código da Opção Pronto")

TOP25 = ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA","B3SA3.SA", "ABEV3.SA", "BPAC11.SA", "PRIO3.SA", "ITSA4.SA","WEGE3.SA", "MGLU3.SA", "JBSS3.SA", "LREN3.SA", "GGBR4.SA","USIM5.SA", "RENT3.SA", "RAIL3.SA", "ELET3.SA", "SBSP3.SA","BBSE3.SA", "CYRE3.SA", "HAPV3.SA", "RADL3.SA", "SUZB3.SA"]

def get_vencimentos():
    hoje = datetime.now()
    mes_atual = hoje.month
    ano = hoje.year
    # Pega mês atual e próximo mês
    v1_mes = mes_atual
    v2_mes = mes_atual + 1 if mes_atual < 12 else 1
    return [(v1_mes, MESES_CALL[v1_mes], MESES_PUT[v1_mes]), (v2_mes, MESES_CALL[v2_mes], MESES_PUT[v2_mes])]

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
    score=0
    if p['MM9']<p['MM21'] and u['MM9']>u['MM21']: score+=3
    if u['RSI']<40: score+=2
    if u['RSI']>70: score-=3
    if u['MACD']>u['MACD_S']: score+=1
    if u['Close']>u['MM21']: score+=1
    return {"ativo": ticker.replace(".SA","")[:4], "ativo_full": ticker.replace(".SA",""), "preco": float(u['Close']), "rsi": float(u['RSI']), "score": score}

if st.button("🚀 GERAR CÓDIGOS DE OPÇÃO", type="primary"):
    v1, v2 = get_vencimentos()
    st.info(f"Vencimentos ativos: {v1[0]}º mês (CALL={v1[1]}/PUT={v1[2]}) e {v2[0]}º mês (CALL={v2[1]}/PUT={v2[2]}) - Foco em liquidez")

    lista=[]
    for ticker in TOP25:
        a=analisa(ticker)
        if not a: continue
        preco = a['preco']; score = a['score']; base = a['ativo']

        if score >= 3:
            strike = round(preco * 1.05, 2)
            strike_int = int(strike)
            # Gera os 2 códigos
            cod1 = f"{base}{v1[1]}{strike_int}"
            cod2 = f"{base}{v2[1]}{strike_int}"
            lista.append({"Ativo":a['ativo_full'], "Preço":f"R${preco:.2f}", "Sinal":"🟢 CALL", "Strike":f"R${strike}", "CÓDIGOS PRA COMPRAR":f"{cod1} ou {cod2}", "Exemplo Corretora":f"Digite {cod1} na busca", "Qtd c/ R$200":f"{int(200/(0.5*100))} cont.", "Score":score, "Tipo":"CALL"})
        elif score <= -2:
            strike = round(preco * 0.95, 2)
            strike_int = int(strike)
            cod1 = f"{base}{v1[2]}{strike_int}"
            cod2 = f"{base}{v2[2]}{strike_int}"
            lista.append({"Ativo":a['ativo_full'], "Preço":f"R${preco:.2f}", "Sinal":"🔴 PUT", "Strike":f"R${strike}", "CÓDIGOS PRA COMPRAR":f"{cod1} ou {cod2}", "Exemplo Corretora":f"Digite {cod1} na busca", "Qtd c/ R$200":f"{int(200/(0.5*100))} cont.", "Score":score, "Tipo":"PUT"})

    if lista:
        df = pd.DataFrame(lista).sort_values("Score", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.subheader("📲 Como comprar na prática")
        for _, r in df.iterrows():
            st.success(f"**{r['Sinal']} {r['Ativo']}** -> Na corretora digite: **{r['CÓDIGOS PRA COMPRAR'].split(' ou ')[0]}**")

        msg = f"💰 *CODIGOS OPCOES R${BANCA:.0f} - {datetime.now().strftime('%d/%m')}*\n\n"
        for _, r in df.iterrows():
            msg += f"{r['Sinal']} {r['Ativo']} {r['CÓDIGOS PRA COMPRAR']} Strike {r['Strike']}\n"

        st.code(msg)
        try:
            url = f"https://api.callmebot.com/whatsapp.php?phone={MEU_NUMERO}&text={quote(msg)}&apikey={MINHA_APIKEY}"
            requests.get(url, timeout=10)
            st.balloons()
            st.success("Enviado pro seu WhatsApp 42 99819-5735!")
        except: pass
    else:
        st.warning("Hoje sem sinal forte de CALL/PUT. Com R$2000 o melhor é preservar.")

st.divider()
st.caption("Ex: PETR4 a R$38 -> CALL Strike 40 Outubro = PETRJ40. Se não achar PETRJ40, tente PETRJ40.00 ou PETR160. Cada corretora formata diferente, mas o começo PETRJ40 é igual.")