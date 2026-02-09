"""Trading Economics API wrapper with in-memory caching."""

import time
import requests
import pandas as pd


class TEClient:
    BASE = "https://api.tradingeconomics.com"

    def __init__(self, api_key):
        self.api_key = api_key
        self._cache = {}

    # ── caching ──────────────────────────────────────────────

    def _get(self, path, ttl=300):
        now = time.time()
        if path in self._cache:
            ts, data = self._cache[path]
            if now - ts < ttl:
                return data
        url = f"{self.BASE}{path}"
        sep = "&" if "?" in path else "?"
        url += f"{sep}c={self.api_key}&f=json"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        self._cache[path] = (now, data)
        return data

    def clear_cache(self):
        self._cache.clear()

    # ── snapshot (all US indicators) ─────────────────────────

    def get_snapshot(self):
        """All ~280 US indicators with latest values."""
        raw = self._get("/country/united%20states", ttl=900)
        df = pd.DataFrame(raw)
        if df.empty:
            return df
        df["LatestValue"] = pd.to_numeric(df["LatestValue"], errors="coerce")
        df["PreviousValue"] = pd.to_numeric(df["PreviousValue"], errors="coerce")
        df["Change"] = df["LatestValue"] - df["PreviousValue"]
        df["PctChange"] = df.apply(
            lambda r: (r["Change"] / r["PreviousValue"] * 100)
            if r["PreviousValue"] and r["PreviousValue"] != 0
            else 0,
            axis=1,
        )
        return df

    def get_snapshot_by_group(self, group):
        """Filter snapshot to a single CategoryGroup."""
        df = self.get_snapshot()
        if df.empty:
            return df
        return df[df["CategoryGroup"] == group].reset_index(drop=True)

    # ── historical ───────────────────────────────────────────

    def get_historical(self, indicator):
        """Full history for one indicator, returns DataFrame with DateTime + Value."""
        path = f"/historical/country/united%20states/indicator/{requests.utils.quote(indicator)}"
        raw = self._get(path, ttl=3600)
        df = pd.DataFrame(raw)
        if df.empty:
            return df
        df["DateTime"] = pd.to_datetime(df["DateTime"])
        df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
        return df.sort_values("DateTime").reset_index(drop=True)

    # ── forecasts ────────────────────────────────────────────

    def get_forecasts(self):
        """Forecasts for all US indicators."""
        raw = self._get("/forecast/country/united%20states", ttl=3600)
        return pd.DataFrame(raw)

    # ── markets ──────────────────────────────────────────────

    def get_markets(self, market_type="index"):
        """Live market data. market_type: index, bond, currency, commodities."""
        try:
            raw = self._get(f"/markets/{market_type}", ttl=60)
        except Exception:
            return pd.DataFrame()
        df = pd.DataFrame(raw)
        if df.empty:
            return df
        for col in ["Last", "Close", "DailyChange", "DailyPercentualChange",
                     "WeeklyChange", "WeeklyPercentualChange",
                     "MonthlyChange", "MonthlyPercentualChange",
                     "YearlyChange", "YearlyPercentualChange"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    def get_ticker_data(self):
        """Curated ticker bar data: key indices, DXY, 10Y, WTI."""
        tickers = []

        try:
            idx = self.get_markets("index")
            for symbol, label in [("US500", "S&P 500"), ("US30", "Dow"),
                                  ("US100", "Nasdaq"), ("USVIX", "VIX")]:
                row = idx[idx["Symbol"] == symbol]
                if not row.empty:
                    r = row.iloc[0]
                    tickers.append({
                        "label": label,
                        "value": r.get("Last", 0),
                        "change": r.get("DailyPercentualChange", 0),
                    })
        except Exception:
            pass

        try:
            bonds = self.get_markets("bond")
            row = bonds[bonds["Name"].str.contains("US 10Y", case=False, na=False)]
            if not row.empty:
                r = row.iloc[0]
                tickers.append({
                    "label": "10Y Yield",
                    "value": r.get("Last", 0),
                    "change": r.get("DailyPercentualChange", 0),
                })
        except Exception:
            pass

        try:
            fx = self.get_markets("currency")
            row = fx[fx["Symbol"] == "DXY"]
            if row.empty:
                row = fx[fx["Name"].str.contains("DXY|Dollar Index", case=False, na=False)]
            if not row.empty:
                r = row.iloc[0]
                tickers.append({
                    "label": "DXY",
                    "value": r.get("Last", 0),
                    "change": r.get("DailyPercentualChange", 0),
                })
        except Exception:
            pass

        try:
            comm = self.get_markets("commodities")
            row = comm[comm["Name"].str.contains("Crude Oil", case=False, na=False)]
            if not row.empty:
                r = row.iloc[0]
                tickers.append({
                    "label": "WTI",
                    "value": r.get("Last", 0),
                    "change": r.get("DailyPercentualChange", 0),
                })
        except Exception:
            pass

        return tickers

    # ── market historical (OHLC) ───────────────────────────

    def get_market_historical(self, symbol):
        """OHLC history for a market symbol (e.g. 'USGG10YR:IND')."""
        path = f"/markets/historical/{requests.utils.quote(symbol, safe=':')}"
        try:
            raw = self._get(path, ttl=3600)
        except Exception:
            return pd.DataFrame()
        df = pd.DataFrame(raw)
        if df.empty:
            return df
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
        for col in ["Open", "High", "Low", "Close"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df.sort_values("Date").reset_index(drop=True)

    # ── news ─────────────────────────────────────────────────

    def get_news(self, limit=25):
        """Latest US economic news."""
        raw = self._get(f"/news/country/united%20states?limit={limit}", ttl=300)
        df = pd.DataFrame(raw)
        if df.empty:
            return df
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df.sort_values("date", ascending=False).reset_index(drop=True)
