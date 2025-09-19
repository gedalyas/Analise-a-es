# analysis_service.py
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import gridspec

def baixar_dados(ticker: str, periodo: str) -> pd.DataFrame:
    """Baixa e padroniza OHLCV (adaptado do seu Colab)."""
    dados = yf.download(
        tickers=ticker,
        period=periodo,
        progress=False,
        auto_adjust=True,
        threads=True,
    )
    if dados.empty:
        raise ValueError("Dados não encontrados - verifique o ticker")

    colunas_padrao = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "adj close": "Close",
        "volume": "Volume",
    }

    dados_limpos = pd.DataFrame(index=dados.index)
    for col in dados.columns:
        col_lower = str(col).lower()
        for padrao in colunas_padrao:
            if padrao in col_lower:
                dados_limpos[colunas_padrao[padrao]] = dados[col]
                break

    return dados_limpos[["Open", "High", "Low", "Close", "Volume"]].dropna()

def calcular_indicadores(dados: pd.DataFrame) -> pd.DataFrame:
    """Bollinger (20,2), RSI(14), MACD(12,26,9), Vol MA5 + Buy_Signal."""
    df = dados.copy()

    # Bandas de Bollinger
    df["MA20"] = df["Close"].rolling(20).mean()
    std20 = df["Close"].rolling(20).std()
    df["Upper_BB"] = df["MA20"] + 2 * std20
    df["Lower_BB"] = df["MA20"] - 2 * std20

    # RSI
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / (avg_loss.replace(0, pd.NA))
    df["RSI"] = 100 - (100 / (1 + rs))
    df["RSI"] = df["RSI"].fillna(method="bfill")

    # MACD
    df["EMA12"] = df["Close"].ewm(span=12, adjust=False).mean()
    df["EMA26"] = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = df["EMA12"] - df["EMA26"]
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    # Vol MA5
    df["Vol_MA5"] = df["Volume"].rolling(5).mean()

    # Sinais (mesma lógica do Colab)
    cond1 = df["Close"] < df["Lower_BB"]
    cond2 = df["RSI"] < 30
    cond3 = (df["MACD"] > df["Signal"]) & (df["MACD"].shift(1) <= df["Signal"].shift(1))
    cond4 = df["Volume"] > df["Vol_MA5"]
    df["Buy_Signal"] = ((cond1 & cond2) | (cond1 & cond3) | (cond2 & cond3)) & cond4

    return df.dropna()

def plotar_analise(dados: pd.DataFrame, ticker: str, *, hspace: float = 0.8,
                   figsize=(16, 18), dpi: int = 100):
    plt.style.use('default')
    fig = plt.figure(figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor('white')
    gs = gridspec.GridSpec(4, 1, height_ratios=[3, 1, 1, 1], figure=fig)

    # 1) Preço + Bandas
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(dados.index, dados['Close'], label='Preço', color='#1f77b4', linewidth=2)
    ax1.plot(dados.index, dados['MA20'], label='MM20', color='#ff7f0e', linestyle='--', linewidth=2)
    ax1.fill_between(dados.index, dados['Upper_BB'], dados['Lower_BB'],
                     color='gray', alpha=0.2, label='Bandas Bollinger')
    compras = dados[dados['Buy_Signal']]
    if not compras.empty:
        ax1.scatter(compras.index, compras['Close'], marker='^',
                    color='green', s=150, label='Sinal de Compra', zorder=3)
    ax1.set_title(f'Análise: {ticker}', fontsize=16, pad=20)
    ax1.legend(loc='best')
    ax1.grid(alpha=0.3)

    # 2) Volume
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax2.bar(dados.index, dados['Volume'], color='#17becf', alpha=0.6)
    ax2.plot(dados.index, dados['Vol_MA5'], color='#e377c2', linewidth=2, label='Média 5 dias')
    ax2.legend(loc='best'); ax2.grid(alpha=0.3)

    # 3) RSI
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    ax3.plot(dados.index, dados['RSI'], color='#9467bd', linewidth=2)
    ax3.axhline(30, color='red', linestyle='--'); ax3.axhline(70, color='red', linestyle='--')
    ax3.fill_between(dados.index, 30, dados['RSI'], where=(dados['RSI']<=30), color='red', alpha=0.2)
    ax3.fill_between(dados.index, 70, dados['RSI'], where=(dados['RSI']>=70), color='green', alpha=0.3)
    ax3.set_ylim(0, 100); ax3.grid(alpha=0.3)

    # 4) MACD
    ax4 = fig.add_subplot(gs[3], sharex=ax1)
    ax4.plot(dados.index, dados['MACD'], label='MACD', color='blue')
    ax4.plot(dados.index, dados['Signal'], label='Signal', color='orange')
    ax4.axhline(0, color='gray', linestyle='--')
    ax4.legend(loc='best'); ax4.grid(alpha=0.3)

    # Espaçamento e margens (mais “respiro”)
    fig.subplots_adjust(top=0.96, bottom=0.06, left=0.08, right=0.98, hspace=hspace, wspace=0.2)
    return fig
