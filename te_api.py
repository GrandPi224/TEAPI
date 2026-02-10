"""Trading Economics API wrapper with in-memory caching."""

import time
import requests
import pandas as pd
from bs4 import BeautifulSoup


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

    # ── calendar (scraped from public page) ────────────────────

    def get_calendar(self):
        """Scrape today's US economic calendar from Trading Economics public page.

        The HTML table has:
          - Header rows (7 cells): cell[0] = date string
          - Data rows (12 cells): [0]=time, [1]=country, [2]=flag, [3]=iso,
            [4]=event, [5]=actual, [6]=previous, [7]=consensus, [8]=forecast,
            [9-11]=responsive/alert cells
          - Separator rows (2 cells): skip
        """
        cache_key = "_calendar"
        now = time.time()
        if cache_key in self._cache:
            ts, data = self._cache[cache_key]
            if now - ts < 900:  # 15 min cache
                return data

        url = "https://tradingeconomics.com/united-states/calendar"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
        except Exception:
            return pd.DataFrame()

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", {"class": "table"})
        if not table:
            return pd.DataFrame()

        rows = []
        current_date = ""
        for tr in table.find_all("tr"):
            # Header rows use <th> elements — first th has the date
            ths = tr.find_all("th")
            if ths:
                current_date = ths[0].get_text(strip=True)
                continue

            cells = tr.find_all("td")

            # Data rows have 12 cells; skip separator rows (2 cells)
            if len(cells) < 9:
                continue

            time_str = cells[0].get_text(strip=True)
            event = cells[4].get_text(strip=True)
            actual = cells[5].get_text(strip=True)
            previous = cells[6].get_text(strip=True)
            consensus = cells[7].get_text(strip=True)
            forecast = cells[8].get_text(strip=True)

            if not event:
                continue

            rows.append({
                "Date": current_date,
                "Time": time_str,
                "Event": event,
                "Actual": actual,
                "Previous": previous,
                "Consensus": consensus,
                "Forecast": forecast,
            })

        df = pd.DataFrame(rows)
        self._cache[cache_key] = (now, df)
        return df
