import pandas_ta_classic as ta
import pandas as pd

class DNAEngine:
    """Klasa odpowiedzialna za matematykę i sygnały."""
    @staticmethod
    def calculate_indicators(df):
        if df is None or df.empty: return df
        df = df.copy()

        # Wstęgi DNA - EMA
        df['r_s'], df['r_e'] = ta.ema(df['Close'], 10), ta.ema(df['Close'], 35)
        df['mid_red'] = (df['r_s'] + df['r_e']) / 2
        
        df['b_s'], df['b_e'] = ta.ema(df['Close'], 45), ta.ema(df['Close'], 85)
        df['mid_blue'] = (df['b_s'] + df['b_e']) / 2
        
        df['g_s'], df['g_e'] = ta.ema(df['Close'], 100), ta.ema(df['Close'], 160)
        df['mid_green'] = (df['g_s'] + df['g_e']) / 2

        # Oscylatory i Wolumen
        df['rsi'] = ta.rsi(df['Close'], 14)
        df['vol_ma'] = ta.sma(df['Volume'], 20)
        
        adx_df = ta.adx(df['High'], df['Low'], df['Close'], 14)
        df['adx'] = adx_df['ADX_14']
        df['adx_slope'] = df['adx'].diff(2)
        
        return df

    @staticmethod
    def get_signals(df):
        vol_ok = df['Volume'] > (df['vol_ma'] * 1.05)
        rsi_ok = (df['rsi'] > 45) & (df['rsi'] < 80)
        cross_red = (df['Close'] > df['mid_red']) & (df['Close'].shift(1) < df['mid_red'].shift(1))
        ribbon_cross = (df['mid_red'] > df['mid_blue']) & (df['mid_red'].shift(1) < df['mid_blue'].shift(1))
        
        buy = ((cross_red & (df['adx_slope'] > 0.15)) | ribbon_cross) & vol_ok & rsi_ok
        sell = ((df['Close'] < df['mid_blue']) & (df['Close'].shift(1) > df['mid_blue'].shift(1))) | (df['rsi'] > 85)
        
        return buy, sell

class DNAAnalyzer:
    """Klasa odpowiedzialna za interpretację wyników i przygotowanie danych raportu."""
    @staticmethod
    def prepare_report_data(df, ticker, target_date_str):
        try:
            valid_sessions = df[df.index <= target_date_str]
            if valid_sessions.empty: return None
            
            current_session = valid_sessions.index[-1]
            idx = df.index.get_loc(current_session)
            
            # Pobranie wartości
            close_val = df['Close'].iloc[idx]
            rsi_val = df['rsi'].iloc[idx]
            slope_val = df['adx_slope'].iloc[idx]
            mid_green = df['mid_green'].iloc[idx]
            dist_green = ((close_val - mid_green) / mid_green) * 100
            
            # Sygnały
            buy_sig, sell_sig = DNAEngine.get_signals(df)
            signal_text = "⚪ neutralny"
            if buy_sig.iloc[idx]: signal_text = "🟢 KUPUJ (Sygnał Potwierdzony)"
            elif sell_sig.iloc[idx]: signal_text = "🔴 SPRZEDAJ / REDUKUJ"

            # Interpretacje
            is_bull = df['mid_red'].iloc[idx] > df['mid_blue'].iloc[idx] > df['mid_green'].iloc[idx]
            align_desc = "✅ DOBRZE: Pełny trend wzrostowy." if is_bull else "⚠️ RYZYKO: Trend w budowie (brak stabilności)."
            
            if rsi_val > 75: rsi_desc = "❗ UWAGA: Przegrzanie (możliwa korekta)."
            elif rsi_val > 55: rsi_desc = "✅ DOBRZE: Silny impet (momentum)."
            else: rsi_desc = "⚪ NEUTRALNIE: Brak wyraźnej siły."

            if slope_val > 1.0: slope_desc = "🚀 EKSTREMALNIE: Gwałtowny atak popytu!"
            elif slope_val > 0.2: slope_desc = "✅ DOBRZE: Trend nabiera siły."
            else: slope_desc = "⚪ SŁABO: Brak dynamiki."

            dist_desc = "✅ OK: Blisko bazy." if dist_green < 15 else "❗ RYZYKO: Duże odchylenie (ryzyko cofnięcia)."

            # Historia Wolumenu
            vol_history = []
            for i in range(idx - 2, idx + 1):
                v_val = int(df['Volume'].iloc[i])
                v_rel = v_val / df['vol_ma'].iloc[i]
                v_emoji = "🔥" if v_rel > 2 else ("✨" if v_rel > 1.2 else " ")
                vol_history.append(f"{df.index[i].strftime('%d.%m')}: {v_val:,} {v_emoji}")

            return {
                "ticker": ticker, "date": current_session.strftime("%Y-%m-%d"), "price": round(float(close_val), 2),
                "signal": signal_text, "align_desc": align_desc, "rsi_desc": rsi_desc, "slope_desc": slope_desc,
                "dist_desc": dist_desc, "vol_history": vol_history, "dist_val": round(dist_green, 1),
                "rsi_val": round(rsi_val, 1), "slope_val": round(slope_val, 2)
            }
        except Exception as e:
            print(f"Błąd Analyzer: {e}"); return None

class DNAReporter:
    """Klasa odpowiedzialna za wizualne formatowanie tekstu."""
    @staticmethod
    def generate_text_report(data):
        if not data: return "❌ Błąd: Brak danych raportu."
        
        report = [
            f"\n🔍 RAPORT DNA PRO V11: {data['ticker']} | {data['date']}",
            "=" * 70,
            f"CENA: {data['price']} PLN | SYGNAŁ: {data['signal']}",
            "-" * 70,
            f"1. HIERARCHIA:   {data['align_desc']}",
            f"2. IMPET (RSI):  {data['rsi_val']} -> {data['rsi_desc']}",
            f"3. DYNAMIKA:     {data['slope_val']} -> {data['slope_desc']}",
            f"4. DYSTANS:      {data['dist_val']}% -> {data['dist_desc']}",
            "-" * 70,
            "OSTATNI WOLUMEN (🔥 = wysoki):"
        ]
        for v in data['vol_history']:
            report.append(f"   {v}")
        report.append("=" * 70)
        
        return "\n".join(report)
