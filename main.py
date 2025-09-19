# main.py
import os
# Backend estável no Windows + ignora config antiga
os.environ["KIVY_GL_BACKEND"] = "angle_sdl2"
os.environ["KIVY_NO_CONFIG"] = "1"

from threading import Thread
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import StringProperty
from kivy_garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg

import analysis_service as svc

# Janela
Window.size = (1000, 700)
Window.clearcolor = (0.96, 0.97, 1, 1)

class ProjetoApp(App):
    status = StringProperty("Pronto.")

    def build(self):
        return Builder.load_file("tela.kv")

    def _normalize_ticker(self, t: str) -> str:
        t = (t or "").strip().upper()
        # Se for B3 sem sufixo, adiciona .SA (ex.: BBAS3 -> BBAS3.SA)
        if t and "." not in t and len(t) <= 6:
            return t + ".SA"
        return t or "BBAS3.SA"

    def on_analyze(self):
        ticker_raw = self.root.ids.ticker_input.text
        ticker = self._normalize_ticker(ticker_raw)
        period = self.root.ids.period_spinner.text

        self.status = f"Baixando/analisando {ticker} ({period})..."
        self.root.ids.analyze_btn.disabled = True

        # Download + cálculo em thread (não trava a UI)
        Thread(target=self._bg_fetch_compute, args=(ticker, period), daemon=True).start()

    def _bg_fetch_compute(self, ticker, period):
        try:
            dados = svc.baixar_dados(ticker, period)
            dados = svc.calcular_indicadores(dados)
            # Criação do gráfico deve ser feita na thread da UI
            Clock.schedule_once(lambda *_: self._render_plot_on_ui(dados, ticker))
        except Exception as e:
            msg = f"{type(e).__name__}: {e}"
            Clock.schedule_once(lambda *_: self._fail(msg))

    def _render_plot_on_ui(self, dados, ticker):
        try:
            # Figura com mais altura + mais respiro entre subplots
            fig = svc.plotar_analise(dados, ticker, hspace=0.8, figsize=(16, 18), dpi=100)

            # Converte tamanho da Figure para pixels (para o ScrollView funcionar)
            w_in, h_in = fig.get_size_inches()
            dpi = fig.get_dpi()
            px_h = int(h_in * dpi)

            box = self.root.ids.plot_container  # <<< ScrollView -> BoxLayout interno
            box.clear_widgets()

            canvas = FigureCanvasKivyAgg(fig)
            canvas.size_hint_y = None
            canvas.height = px_h          # altura fixa para habilitar o scroll
            canvas.size_hint_x = 1        # ocupar a largura disponível

            box.add_widget(canvas)

            inicio = dados.index[0].strftime("%d/%m/%Y")
            fim = dados.index[-1].strftime("%d/%m/%Y")
            buys = int(dados["Buy_Signal"].sum())
            self.status = f"OK. {inicio} → {fim} | Sinais de compra: {buys}"
        except Exception as e:
            self._fail(f"{type(e).__name__}: {e}")
        finally:
            self.root.ids.analyze_btn.disabled = False

    def _fail(self, msg: str):
        self.status = f"Erro: {msg}"
        self.root.ids.analyze_btn.disabled = False

if __name__ == "__main__":
    ProjetoApp().run()
