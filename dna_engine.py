import pandas_ta_classic as ta
import pandas as pd

class DNAEngine:
    """
    Silnik analityczny DNA PRO V11.
    Centralna logika obliczeń wskaźników i generowania sygnałów dla GPW.
    """

    @staticmethod
    def calculate_indicators(df):
        """Oblicza pełny zestaw wskaźników DNA na danych historycznych."""
        if df is None or df.empty:
            return df
        
        # Kopia, aby uniknąć SettingWithCopyWarning
        df = df.copy()

        # 1. Wstęgi (Ribbons) - EMA
        # Red Ribbon (Krótki trend)
        df['r_s'] = ta.ema(df['Close'], length=10)
        df['r_e'] = ta.ema(df['Close'], length=35)
        df['mid_red'] = (df['r_s'] + df['r_e']) / 2
        
        # Blue Ribbon (Średni trend)
        df['b_s'] = ta.ema(df['Close'], length=45)
        df['b_e'] = ta.ema(df['Close'], length=85)
        df['mid_blue'] = (df['b_s'] + df['b_e']) / 2
        
        # Green Ribbon (Długi trend / Baza)
        df['g_s'] = ta.ema(df['Close'], length=100)
        df['g_e'] = ta.ema(df['Close'], length=160)
        df['mid_green'] = (df['g_s'] + df['g_e']) / 2

        # 2. Oscylatory i Wolumen
        df['rsi'] = ta.rsi(df['Close'], length=14)
        df['vol_ma'] = ta.sma(df['Volume'], length=20)
        
        # 3. ADX i Dynamika (Slope)
        # pandas_ta_classic zwraca DataFrame przy ADX
        adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
        df['adx'] = adx_df['ADX_14']
        df['adx_slope'] = df['adx'].diff(2)
        
        return df

    @staticmethod
    def get_signals(df):
        """
        Zwraca dwie serie logiczne (True/False): sygnał kupna i sprzedaży.
        Zoptymalizowane pod GPW (wyłapuje ruchy typu 8 stycznia na WPL).
        """
        # Filtry bazowe
        vol_ok = df['Volume'] > (df['vol_ma'] * 1.05)
        rsi_ok = (df['rsi'] > 45) & (df['rsi'] < 80)
        
        # Logika A: Cena przecina czerwoną wstęgę od dołu (Dip Buy)
        cross_red = (df['Close'] > df['mid_red']) & (df['Close'].shift(1) < df['mid_red'].shift(1))
        
        # Logika B: Przecięcie czerwonej wstęgi nad niebieską (Trend Buy)
        ribbon_cross = (df['mid_red'] > df['mid_blue']) & (df['mid_red'].shift(1) < df['mid_blue'].shift(1))
        
        # Agregacja sygnału kupna (Dynamika ADX_Slope > 0.15)
        buy = ((cross_red & (df['adx_slope'] > 0.15)) | ribbon_cross) & vol_ok & rsi_ok
        
        # Sygnał sprzedaży (Przebicie niebieskiej wstęgi lub ekstremalne wykupienie)
        sell = ((df['Close'] < df['mid_blue']) & (df['Close'].shift(1) > df['mid_blue'].shift(1))) | (df['rsi'] > 85)
        
        return buy, sell

    @staticmethod
    def get_distance_metrics(df):
        """Dodatkowa metryka: procentowe odchylenie od zielonej wstęgi (bazy)."""
        df['dist_green_pct'] = ((df['Close'] - df['mid_green']) / df['mid_green']) * 100
        return df['dist_green_pct']
