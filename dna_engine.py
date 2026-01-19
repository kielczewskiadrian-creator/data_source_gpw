import pandas as pd
import pandas_ta_classic as ta
import numpy as np

class DNAEngine:
    """Zintegrowany silnik DNA V11 - Sygnały TV + Dane do raportów + Metody dodatkowe."""
    
    @staticmethod
    def calculate_indicators(df):
        """Główna metoda obliczeniowa - łączy sygnały wstęg i dane raportu."""
        if df is None or df.empty:
            return df
        
        df = df.copy()

        # --- 1. WSTĘGI (EMA) - Logika 1:1 z Pine Script ---
        df['r_s'], df['r_e'] = ta.ema(df['Close'], 10), ta.ema(df['Close'], 35)
        df['mid_red'] = (df['r_s'] + df['r_e']) / 2
        
        df['b_s'], df['b_e'] = ta.ema(df['Close'], 45), ta.ema(df['Close'], 85)
        df['mid_blue'] = (df['b_s'] + df['b_e']) / 2
        
        df['g_s'], df['g_e'] = ta.ema(df['Close'], 100), ta.ema(df['Close'], 160)
        df['mid_green'] = (df['g_s'] + df['g_e']) / 2

        # --- 2. DANE POMOCNICZE (Wymagane przez DNAAnalyzer) ---
        df['rsi'] = ta.rsi(df['Close'], length=14)
        df['vol_ma'] = ta.sma(df['Volume'], length=20)
        
        # Bezpieczne pobieranie ADX
        try:
            adx_res = ta.adx(df['High'], df['Low'], df['Close'], length=14)
            df['adx'] = adx_res.iloc[:, 0] if isinstance(adx_res, pd.DataFrame) else adx_res
        except:
            df['adx'] = 0
            
        df['adx_slope'] = df['adx'].diff(2).fillna(0)

        # --- 3. LOGIKA SQUEEZE (Pine Script) ---
        dist_rb = (df['mid_red'] - df['mid_blue']).abs() / df['mid_blue'] * 100
        dist_bg = (df['mid_blue'] - df['mid_green']).abs() / df['mid_green'] * 100
        df['is_squeeze'] = (dist_rb <= 4) & (dist_bg <= 4)

        return df

    @staticmethod
    def get_signals(df):
        """Sygnały Kupna/Sprzedaży (Pine Script crossover)."""
        if 'mid_red' not in df.columns or 'mid_blue' not in df.columns:
            return pd.Series(False, index=df.index), pd.Series(False, index=df.index)

        buy = (df['mid_red'] > df['mid_blue']) & (df['mid_red'].shift(1) <= df['mid_blue'].shift(1))
        sell = (df['mid_red'] < df['mid_blue']) & (df['mid_red'].shift(1) >= df['mid_blue'].shift(1))
        return buy.fillna(False), sell.fillna(False)

    @staticmethod
    def calculate_all(df):
        """Metoda do szerokich wiązek EMA (wstęgi DNA)."""
        red_p = [3, 4, 5, 7, 8, 9, 10, 11, 12, 15]
        green_p = [30, 35, 40, 45, 50, 60]
        blue_p = [180, 190, 200, 210, 220]
        
        for p in red_p + green_p + blue_p:
            df[f'EMA_{p}'] = df['Close'].ewm(span=p, adjust=False).mean()

        df['G_Min'] = df[[f'EMA_{p}' for p in green_p]].min(axis=1)
        df['G_Max'] = df[[f'EMA_{p}' for p in green_p]].max(axis=1)
        df['B_Min'] = df[[f'EMA_{p}' for p in blue_p]].min(axis=1)
        df['B_Max'] = df[[f'EMA_{p}' for p in blue_p]].max(axis=1)
        
        df['Overheat'] = ((df['Close'] - df['EMA_30']) / df['EMA_30']) * 100
        df['SL_Level'] = df['EMA_60']
        df['V_Avg_20'] = df['Volume'].rolling(window=20).mean()
        df['Ribbon_Width'] = df['G_Max'] - df['G_Min']
        return df

    @staticmethod
    def get_rv_h1(df_h1):
        """Analiza wolumenu relatywnego."""
        df_h1['Hour'] = df_h1.index.hour
        avg_vol = df_h1.groupby('Hour')['Volume'].transform(lambda x: x.rolling(window=20).mean())
        df_h1['RV'] = df_h1['Volume'] / avg_vol
        return df_h1
        
class DNAAnalyzer:
    @staticmethod
    def prepare_report_data(df, ticker, target_date_str):
        try:
            valid_sessions = df[df.index <= target_date_str]
            if valid_sessions.empty: return None
            
            current_session = valid_sessions.index[-1]
            idx = df.index.get_loc(current_session)
            
            close_val = df['Close'].iloc[idx]
            rsi_val = df['rsi'].iloc[idx]
            slope_val = df['adx_slope'].iloc[idx]
            mid_green = df['mid_green'].iloc[idx]
            dist_green = ((close_val - mid_green) / mid_green) * 100
            
            # --- MAPOWANIE LINKU TRADINGVIEW ---
            # Obsługa formatów: DNP (GPW) oraz ORA.PA (Zagranica)
            if "." in ticker:
                parts = ticker.split(".")
                # Zamiana ORA.PA na PA:ORA (Euronext Paris) lub podobne
                tv_symbol = f"{parts[1]}:{parts[0]}"
            else:
                tv_symbol = f"GPW:{ticker}"
            
            tv_link = f"https://pl.tradingview.com/chart/4dItPTLJ/?symbol={tv_symbol}"
            
            # --- SYGNAŁY I OPISY ---
            buy_sig, sell_sig = DNAEngine.get_signals(df)
            signal_text = "⚪ neutralny"
            if buy_sig.iloc[idx]: signal_text = "🟢 KUPUJ (Sygnał Potwierdzony)"
            elif sell_sig.iloc[idx]: signal_text = "🔴 SPRZEDAJ / REDUKUJ"

            is_bull = df['mid_red'].iloc[idx] > df['mid_blue'].iloc[idx] > df['mid_green'].iloc[idx]
            align_desc = "✅ DOBRZE: Pełny trend wzrostowy." if is_bull else "⚠️ RYZYKO: Trend w budowie."
            
            if rsi_val > 75: rsi_desc = "❗ UWAGA: Przegrzanie."
            elif rsi_val > 55: rsi_desc = "✅ DOBRZE: Silny impet."
            else: rsi_desc = "⚪ NEUTRALNIE: Brak siły."

            # Historia wolumenu
            vol_history = []
            for i in range(max(0, idx - 2), idx + 1):
                v_val = int(df['Volume'].iloc[i])
                v_rel = v_val / df['vol_ma'].iloc[i] if df['vol_ma'].iloc[i] > 0 else 1
                v_emoji = "🔥" if v_rel > 2 else ("✨" if v_rel > 1.2 else " ")
                vol_history.append(f"{df.index[i].strftime('%d.%m')}: {v_val:,} {v_emoji}")

            return {
                "ticker": ticker, 
                "date": current_session.strftime("%Y-%m-%d"), 
                "price": round(float(close_val), 2),
                "signal": signal_text, 
                "align_desc": align_desc, 
                "rsi_desc": rsi_desc,
                "vol_history": vol_history, 
                "dist_val": round(dist_green, 1),
                "rsi_val": round(rsi_val, 1), 
                "slope_val": round(slope_val, 2),
                "slope_desc": "Trend rośnie" if slope_val > 0.2 else "Brak dynamiki",
                "dist_desc": "OK" if dist_green < 15 else "Ryzyko odchylenia",
                "tv_link": tv_link
            }
        except Exception as e:
            print(f"Błąd Analyzer: {e}"); return None

    @staticmethod
    def predict_price_wave(df, ticker, target_date=None):
        if target_date: df = df.loc[:target_date].copy()
        last_row = df.iloc[-1]
        base_price = last_row['mid_green']
        current_price = last_row['Close']
        
        prediction = "↔️ KONTYNUACJA"
        expected_move = "Brak punktu zwrotnego"
        confidence = "Niska"
        
        if current_price <= last_row['mid_green'] and last_row['rsi'] < 35:
            prediction = "📈 ODBICIE"
            expected_move = f"Powrót do {round(last_row['mid_blue'], 2)}"
            confidence = "Wysoka"
        elif current_price >= last_row['mid_red'] and last_row['rsi'] > 65:
            prediction = "📉 KOREKTA"
            expected_move = f"Spadek do {round(last_row['mid_blue'], 2)}"
            confidence = "Wysoka"

        return {
            "ticker": ticker, "date": df.index[-1].strftime('%Y-%m-%d'),
            "current_price": round(current_price, 2), "prediction": prediction,
            "expected_target": expected_move, "confidence": confidence,
            "rsi": round(last_row['rsi'], 1),
            "dist_to_base": f"{round(((current_price - base_price)/base_price)*100, 2)}%"
        }

class DNAReporter:
    @staticmethod
    def generate_text_report(data):
        if not data: return "❌ Błąd: Brak danych raportu."
        report = [
            f"\n🔍 RAPORT DNA PRO: {data['ticker']} | {data['date']}",
            "=" * 60,
            f"CENA: {data['price']} | SYGNAŁ: {data['signal']}",
            f"WYKRES TV: {data['tv_link']}",
            "-" * 60,
            f"1. TREND:    {data['align_desc']}",
            f"2. IMPET:    {data['rsi_val']} -> {data['rsi_desc']}",
            f"3. DYNAMIKA: {data['slope_val']} -> {data['slope_desc']}",
            f"4. DYSTANS:  {data['dist_val']}% -> {data['dist_desc']}",
            "-" * 60,
            "WOLUMEN:",
            "\n".join(f"   {v}" for v in data['vol_history']),
            "=" * 60
        ]
        return "\n".join(report)

# --- PRZYKŁAD UŻYCIA ---
# df = yf.download("DNP.WA", start="2025-01-01")
# df = DNAEngine.calculate_indicators(df)
# data = DNAAnalyzer.prepare_report_data(df, "DNP", "2026-01-19")
# print(DNAReporter.generate_text_report(data))
