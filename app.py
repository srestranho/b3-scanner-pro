import streamlit as st, yfinance as yf, pandas as pd, ta, requests
from datetime import datetime
from urllib.parse import quote
import numpy as np

MEU_NUMERO = "5542998195735"
MINHA_APIKEY = "4955675"

st.set_page_config(page_title="B3 Opções Scanner", layout="wide")
st.title("💰 Scanner B3 - Ações + Opções CALL/PUT")

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
    score=0
    if p['MM9']<p['MM21'] and u['MM9']>u['MM21']: score+=3
    if u['RSI']<40: score+=2
    if u['RSI']>70: score-=3
    if u['MACD']>u['MACD_S']: score+=1
    if u['Close']>u['MM21']: score+=1
    return {"ativo": ticker.replace(".SA",""), "preco": float(u['Close']), "rsi": float(u['RSI']), "score": score, "df": df}

def sugere_opcao(analise):
    preco = analise['preco']
    score = analise['score']
    ativo = analise['ativo']
    
    if score >= 3:
        tipo = "CALL"
        strike_sugerido = round(preco * 1.05, 2) # 5% OTM - mais explosiva
        motivo = f"Tendência de ALTA forte (Score {score}). CALL OTM tem maior alavancagem."
        estrategia = f"Compra de CALL {ativo} Strike R$ {strike_sugerido} - Vencimento 20-30 dias"
        sinal = "🟢 COMPRA CALL"
    elif score <= -2:
        tipo = "PUT"
        strike_sugerido = round(preco * 0.95, 2) # 5% OTM
        motivo = f"Tendência de BAIXA (Score {score}). PUT protege e lucra na queda."
        estrategia = f"Compra de PUT {ativo} Strike R$ {strike_sugerido} - Vencimento 20-30 dias"
        sinal = "🔴 COMPRA PUT"
    else:
        tipo = "AGUARDAR"
        strike_sugerido = preco
        motivo = f"Sem tendência definida (Score {score}). Não opere opções agora."
        estrategia = "Fica de fora"
        sinal = "⚪ AGUARDAR"
    
    return {
        "Ativo Base": ativo,
        "Preço Base": f"R$ {preco:.2f}",
        "Sinal Ação": "ALTA" if score>=3 else "BAIXA" if score<=-2 else "NEUTRO",
        "Opção Sugerida": sinal,
        "Tipo": tipo,
        "Strike Ideal": f"R$ {strike_sugerido}",
        "Estratégia": estrategia,
        "Motivo": motivo,
        "Score": score,
        "Risco": "ALTO - 100% do prêmio" if tipo!="AGUARDAR" else "N/A"
    }

if st.button("🚀 GERAR SINAIS DE OPÇÕES AGORA", type="primary"):
    opcoes_lista = []
    prog = st.progress(0)
    for i, ticker in enumerate(TOP10):
        a = analisa(ticker)
        if a:
            sugestao = sugere_opcao(a)
            opcoes_lista.append(sugestao)
        prog.progress((i+1)/len(TOP10))
    
    df_op = pd.DataFrame(opcoes_lista).sort_values("Score", ascending=False)
    
    # Tabela principal
    st.subheader("📋 Sinais de Opções")
    st.dataframe(df_op[["Ativo Base","Preço Base","Sinal Ação","Opção Sugerida","Strike Ideal","Risco"]], use_container_width=True, hide_index=True)

    # Detalhes
    for _, row in df_op.iterrows():
        if row['Tipo'] != 'AGUARDAR':
            with st.expander(f"{row['Opção Sugerida']} - {row['Ativo Base']} | {row['Estratégia']}"):
                st.write(f"**Motivo:** {row['Motivo']}")
                st.write(f"**Como operar:** {row['Estratégia']}")
                st.write(f"**RSI do ativo:** {analisa(row['Ativo Base']+'.SA')['rsi']:.0f}")
                st.warning(f"⚠️ Opção é RENDA VARIÁVEL de alto risco. Entre com no máximo 2% da banca por operação. Stop é a perda total do prêmio.")

    # Mensagem para WhatsApp
    melhores_calls = df_op[df_op['Tipo']=='CALL']
    melhores_puts = df_op[df_op['Tipo']=='PUT']
    
    msg = f"💰 *SINAIS OPÇÕES B3 - {datetime.now().strftime('%d/%m %H:%M')}*\n\n"
    if not melhores_calls.empty:
        msg += "*🟢 CALLS (Aposta na ALTA):*\n"
        for _, r in melhores_calls.iterrows(): msg += f"✅ {r['Ativo Base']} -> {r['Strike Ideal']} | {r['Motivo'][:40]}...\n"
    if not melhores_puts.empty:
        msg += "\n*🔴 PUTS (Aposta na QUEDA):*\n"
        for _, r in melhores_puts.iterrows(): msg += f"🔻 {r['Ativo Base']} -> {r['Strike Ideal']} | {r['Motivo'][:40]}...\n"
    if melhores_calls.empty and melhores_puts.empty:
        msg += "⚪ Sem sinal forte hoje. Não operar opções.\n"

    st.code(msg)
    
    try:
        url = f"https://api.callmebot.com/whatsapp.php?phone={MEU_NUMERO}&text={quote(msg)}&apikey={MINHA_APIKEY}"
        requests.get(url, timeout=10)
        st.success("✅ Sinais enviados pro seu WhatsApp!")
        st.balloons()
    except:
        st.error("Erro ao enviar WhatsApp")