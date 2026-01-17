import pandas_ta_classic as ta
import pandas as pd

class DNAEngine:
    """Klasa odpowiedzialna za matematykę i sygnały."""
    import pandas_ta_classic as ta
import pandas as pd

class DNAEngine:
    import pandas_ta_classic as ta
import pandas as pd

class DNAEngine:
    """Zoptymalizowany silnik DNA V11 - naprawia KeyError i wykrywa sygnały na CPS."""
    
    import pandas_ta_classic as ta
import pandas as pd

class DNAEngine:
    """Zoptymalizowany silnik DNA - naprawia błąd adx_slope i wykrywa wcześniejsze sygnały."""
    
    @staticmethod
    def calculate_indicators(df):
        if df is None or df.empty: return df
        df = df.copy()

        # 1. Wstęgi DNA - EMA
        df['r_s'], df['r_e'] = ta.ema(df['Close'], 10), ta.ema(df['Close'], 35)
        df['mid_red'] = (df['r_s'] + df['r_e']) / 2
        
        df['b_s'], df['b_e'] = ta.ema(df['Close'], 45), ta.ema(df['Close'], 85)
        df['mid_blue'] = (df['b_s'] + df['b_e']) / 2
        
        df['g_s'], df['g_e'] = ta.ema(df['Close'], 100), ta.ema(df['Close'], 160)
        df['mid_green'] = (df['g_s'] + df['g_e']) / 2

        # 2. Oscylatory i Wolumen
        df['rsi'] = ta.rsi(df['Close'], 14)
        df['vol_ma'] = ta.sma(df['Volume'], 20)
        
        # 3. ADX i kluczowy ADX_SLOPE (Naprawa KeyError)
        adx_df = ta.adx(df['High'], df['Low'], df['Close'], 14)
        df['adx'] = adx_df['ADX_14']
        # Obliczamy zmianę ADX z 2 sesji, aby złapać dynamikę trendu
        df['adx_slope'] = df['adx'].diff(2)
        
        return df

    @staticmethod
    def get_signals(df):
        """Wersja dostosowana do wczesnego wykrywania trendu (np. na CPS)."""
        if 'mid_red' not in df.columns or 'adx_slope' not in df.columns:
            return pd.Series(False, index=df.index), pd.Series(False, index=df.index)

        # --- FILTRY (Poluzowane, by złapać sygnał sprzed kilku dni) ---
        # 1. Wolumen: nie musi być ekstremalny (0.9 zamiast 1.05)
        vol_ok = df['Volume'] > (df['vol_ma'] * 0.9)
        # 2. RSI: CPS odbijał przy RSI ok. 40, więc próg 45 był za wysoki
        rsi_ok = (df['rsi'] > 38) & (df['rsi'] < 75)

        # --- LOGIKA WEJŚCIA ---
        # A. Przecięcie ceny przez czerwoną wstęgę (szybki sygnał)
        cross_red = (df['Close'] > df['mid_red']) & (df['Close'].shift(1) < df['mid_red'].shift(1))
        
        # B. Przecięcie wstęg (potwierdzenie trendu)
        ribbon_cross = (df['mid_red'] > df['mid_blue']) & (df['mid_red'].shift(1) < df['mid_blue'].shift(1))

        # --- FINALNY SYGNAŁ KUPNA ---
        # Poluzowany adx_slope (0.05 zamiast 0.15), aby szybciej reagować na zmianę kierunku
        buy = ((cross_red & (df['adx_slope'] > 0.05)) | ribbon_cross) & vol_ok & rsi_ok

        # --- FINALNY SYGNAŁ SPRZEDAŻY ---
        sell = ((df['Close'] < df['mid_blue']) & (df['Close'].shift(1) > df['mid_blue'].shift(1))) | (df['rsi'] > 85)

        # Filtrowanie, aby pokazać tylko PIERWSZY dzień sygnału
        final_buy = buy & (~buy.shift(1).fillna(False))
        final_sell = sell & (~sell.shift(1).fillna(False))

        return final_buy, final_sell

    @staticmethod
    def calculate_all(df):
        # 1. Obliczanie EMA (Wiązki)
        red_p = [3, 4, 5, 7, 8, 9, 10, 11, 12, 15]
        green_p = [30, 35, 40, 45, 50, 60]
        blue_p = [180, 190, 200, 210, 220]
        
        for p in red_p + green_p + blue_p:
            df[f'EMA_{p}'] = df['Close'].ewm(span=p, adjust=False).mean()

        # 2. Granice wstęg i wskaźniki
        df['G_Min'] = df[[f'EMA_{p}' for p in green_p]].min(axis=1)
        df['G_Max'] = df[[f'EMA_{p}' for p in green_p]].max(axis=1)
        df['B_Min'] = df[[f'EMA_{p}' for p in blue_p]].min(axis=1)
        df['B_Max'] = df[[f'EMA_{p}' for p in blue_p]].max(axis=1)
        
        # 3. Przegrzanie i SL
        df['Overheat'] = ((df['Close'] - df['EMA_30']) / df['EMA_30']) * 100
        df['SL_Level'] = df['EMA_60']
        df['V_Avg_20'] = df['Volume'].rolling(window=20).mean()
        
        # 4. Szerokość wstęgi (do akceleracji)
        df['Ribbon_Width'] = df['G_Max'] - df['G_Min']
        return df

    @staticmethod
    def get_rv_h1(df_h1):
        df_h1['Hour'] = df_h1.index.hour
        avg_vol = df_h1.groupby('Hour')['Volume'].transform(lambda x: x.rolling(window=20).mean())
        df_h1['RV'] = df_h1['Volume'] / avg_vol
        return df_h1
        
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

    @staticmethod
    def predict_price_wave(df, ticker, target_date=None):
        # Filtrujemy dane do podanej daty (symulacja "teraz")
        if target_date:
            df = df.loc[:target_date].copy()
        
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # Obliczamy środek kanału (Twoja baza - Green Ribbon)
        base_price = last_row['mid_green']
        current_price = last_row['Close']
        
        # Obliczamy zmienność (uproszczony ATR)
        daily_range = (df['High'] - df['Low']).rolling(10).mean().iloc[-1]
        
        # Wyznaczamy ekstremum fali (Wstęgi jako bandy)
        upper_band = last_row['mid_red'] * 1.02 # 2% powyżej czerwonej
        lower_band = last_row['mid_green'] * 0.98 # 2% poniżej zielonej
        
        # Logika przewidywania
        prediction = ""
        expected_move = ""
        confidence = "Niska"
        
        # Scenariusz A: Wyprzedanie (Szukamy dołka)
        if current_price <= last_row['mid_green'] and last_row['rsi'] < 35:
            prediction = "📈 ODBICIE (Wyczerpanie spadku)"
            expected_move = f"Powrót w stronę {round(last_row['mid_blue'], 2)}"
            confidence = "Wysoka" if last_row['rsi'] < 30 else "Średnia"
            
        # Scenariusz B: Wykupienie (Szukamy szczytu)
        elif current_price >= last_row['mid_red'] and last_row['rsi'] > 65:
            prediction = "📉 KOREKTA (Wyczerpanie wzrostu)"
            expected_move = f"Spadek w stronę {round(last_row['mid_blue'], 2)}"
            confidence = "Wysoka" if last_row['rsi'] > 75 else "Średnia"
            
        else:
            prediction = "↔️ KONTYNUACJA (Ruch wewnątrz kanału)"
            expected_move = "Brak wyraźnego punktu zwrotnego"
            confidence = "Niska"

        return {
            "ticker": ticker,
            "date": df.index[-1].strftime('%Y-%m-%d'),
            "current_price": round(current_price, 2),
            "prediction": prediction,
            "expected_target": expected_move,
            "confidence": confidence,
            "rsi": round(last_row['rsi'], 1),
            "dist_to_base": f"{round(((current_price - base_price)/base_price)*100, 2)}%"
        }

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
