import pandas as pd
import numpy as np

class DNAEngineV2:
    @staticmethod
    def calculate_indicators(df):
        # 1. Definicja zagęszczonych okresów EMA
        red_periods = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
        green_periods = [30, 33, 36, 39, 42, 45, 48, 51, 54, 57, 60]
        blue_periods = [180, 185, 190, 195, 200, 205, 210, 215, 220]
        
        # 2. Masowe obliczanie EMA
        all_periods = red_periods + green_periods + blue_periods
        for p in all_periods:
            df[f'EMA_{p}'] = df['Close'].ewm(span=p, adjust=False).mean()
            
        # 3. Wyznaczanie stref (Agregaty)
        df['R_Max'] = df[[f'EMA_{p}' for p in red_periods]].max(axis=1)
        df['G_Min'] = df[[f'EMA_{p}' for p in green_periods]].min(axis=1)
        df['G_Max'] = df[[f'EMA_{p}' for p in green_periods]].max(axis=1)
        df['B_Min'] = df[[f'EMA_{p}' for p in blue_periods]].min(axis=1)
        df['B_Max'] = df[[f'EMA_{p}' for p in blue_periods]].max(axis=1)
        
        # 4. Statystyki pomocnicze
        df['V_Avg'] = df['Volume'].rolling(window=20).mean()
        return df

    @staticmethod
    def analyze_status(df):
        if len(df) < 2: return "Brak danych", "⚪"
        row = df.iloc[-1]
        
        # --- ANALIZA ŚWIECY (KNOTY) ---
        high, low = row['High'], row['Low']
        open_p, close_p = row['Open'], row['Close']
        range_total = high - low if high != low else 0.001
        body_bottom = min(open_p, close_p)
        body_size = abs(close_p - open_p)
        lower_wick = body_bottom - low
        
        # Detekcja Pin Baru (Dolny knot > 2x korpus i min. 50% całej świecy)
        is_pin_bar = (lower_wick > body_size * 2) and (lower_wick / range_total > 0.5)
        sentiment_icon = "🟢" if close_p >= open_p else "🔴"
        
        # --- LOGIKA SYGNAŁÓW DNA ---
        if row['Low'] <= row['G_Max'] and row['Close'] >= row['G_Min']:
            if row['Volume'] > row['V_Avg']:
                status, icon = ("DOKUP (SILNY PIN BAR!) 🔥", "🔨") if is_pin_bar else ("DOKUP (RETEST) ✅", "🟢")
                return f"{icon} {status} | Sesja: {sentiment_icon}", icon
            
        if row['Close'] < row['G_Min'] or row['Close'] < row['B_Min']:
            return f"⚠️ SPRZEDAJ (STOP) 🛡️ | Sesja: {sentiment_icon}", "⚠️"
            
        if row['Low'] <= row['B_Max'] and row['Close'] >= row['B_Min']:
            return f"🔵 KRYTYCZNE WSPARCIE ⚠️ | Sesja: {sentiment_icon}", "🔵"
            
        if row['Close'] > row['R_Max'] > row['G_Max'] > row['B_Max']:
            return f"🚀 SILNA HOSSA 🔥 | Sesja: {sentiment_icon}", "🚀"

        return f"⚪ OBSERWUJ | Sesja: {sentiment_icon}", "⚪"
