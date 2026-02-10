"""Trading Economics Dashboard — powered by Dash + Plotly."""

import os
import dash
from dash import html, dcc, dash_table, callback_context, no_update
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd

from te_api import TEClient

# ── Config ───────────────────────────────────────────────────
API_KEY = os.environ.get("TE_API_KEY", "")
if not API_KEY:
    raise SystemExit("Set TE_API_KEY environment variable (e.g. set TE_API_KEY=your_key:your_secret)")
te = TEClient(API_KEY)

# Category groups for the Economy section
ECONOMY_GROUPS = [
    ("GDP", "GDP"),
    ("Labour", "Labour"),
    ("Prices", "Prices"),
    ("Housing", "Housing"),
    ("Consumer", "Consumer"),
    ("Business", "Business"),
    ("Trade", "Trade"),
    ("Money", "Money"),
    ("Government", "Government"),
    ("Energy", "Energy"),
]

MARKET_TYPES = [
    ("Indices", "index"),
    ("Bonds", "bond"),
    ("Currencies", "currency"),
    ("Commodities", "commodities"),
]

# Key indicators to highlight per economy category (stat cards + charts)
CATEGORY_HIGHLIGHTS = {
    "GDP": {
        "stats": ["GDP", "GDP Growth Rate", "GDP Annual Growth Rate", "GDP per Capita"],
        "charts": ["GDP Growth Rate", "GDP", "GDP per Capita"],
    },
    "Labour": {
        "stats": ["Non Farm Payrolls", "Unemployment Rate", "Job Vacancies", "Average Hourly Earnings YoY"],
        "charts": ["Unemployment Rate", "Non Farm Payrolls", "Initial Jobless Claims", "Job Vacancies"],
    },
    "Prices": {
        "stats": ["Inflation Rate", "Core Inflation Rate", "Core PCE Price Index Annual Change", "Producer Prices Change"],
        "charts": ["Inflation Rate", "Core Inflation Rate", "Core PCE Price Index Annual Change", "Producer Prices Change"],
    },
    "Housing": {
        "stats": ["30 Year Mortgage Rate", "Existing Home Sales", "Housing Starts", "Building Permits"],
        "charts": ["30 Year Mortgage Rate", "Existing Home Sales", "Housing Starts", "Case Shiller Home Price Index YoY"],
    },
    "Consumer": {
        "stats": ["Consumer Confidence", "Consumer Spending", "Retail Sales MoM", "Personal Savings"],
        "charts": ["Consumer Confidence", "Retail Sales YoY", "Personal Savings", "Consumer Credit"],
    },
    "Business": {
        "stats": ["Non Manufacturing PMI", "Business Confidence", "Industrial Production", "Durable Goods Orders"],
        "charts": ["Non Manufacturing PMI", "Business Confidence", "Industrial Production", "Capacity Utilization"],
    },
    "Trade": {
        "stats": ["Balance of Trade", "Exports", "Imports", "Current Account to GDP"],
        "charts": ["Balance of Trade", "Exports", "Imports", "Current Account"],
    },
    "Money": {
        "stats": ["Interest Rate", "Money Supply M2", "Effective Federal Funds Rate", "Banks Balance Sheet"],
        "charts": ["Interest Rate", "Effective Federal Funds Rate", "Money Supply M2"],
    },
    "Government": {
        "stats": ["Government Debt", "Government Debt to GDP", "Government Budget", "Government Budget Value"],
        "charts": ["Government Debt", "Government Debt to GDP", "Government Budget", "Government Budget Value"],
    },
    "Energy": {
        "stats": ["Crude Oil Rigs", "Total Rigs", "Strategic Petroleum Reserve Crude Oil Stocks", "Natural Gas Stocks Change"],
        "charts": ["Crude Oil Rigs", "Strategic Petroleum Reserve Crude Oil Stocks", "Natural Gas Stocks Change"],
    },
}

# Chart colors to cycle through
CHART_COLORS = ["#00b0ff", "#00e676", "#ffd740", "#ff1744", "#e040fb", "#00bcd4"]

# ── App init ─────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True,
    title="TE Dashboard",
)


# ── Helper: build ticker bar ────────────────────────────────
def build_ticker_items():
    tickers = te.get_ticker_data()
    items = []
    for t in tickers:
        chg = t.get("change", 0) or 0
        color = "#00e676" if chg >= 0 else "#ff1744"
        arrow = "\u25b2" if chg >= 0 else "\u25bc"
        val = t.get("value", 0) or 0
        items.append(
            html.Span(
                [
                    html.Span(f" {t['label']} ", style={"color": "#aaa", "fontWeight": "500"}),
                    html.Span(f"{val:,.2f} ", style={"color": "#fff", "fontWeight": "700"}),
                    html.Span(
                        f"{arrow} {chg:+.2f}%",
                        style={"color": color, "fontWeight": "600", "marginRight": "30px"},
                    ),
                ]
            )
        )
    # duplicate for seamless scroll
    return items + items


# ── Sidebar ──────────────────────────────────────────────────
def build_sidebar():
    market_links = [
        dbc.NavLink(
            label,
            id={"type": "nav-link", "page": f"market-{mtype}"},
            href="#",
            className="sidebar-link",
        )
        for label, mtype in MARKET_TYPES
    ]
    econ_links = [
        dbc.NavLink(
            label,
            id={"type": "nav-link", "page": f"econ-{group}"},
            href="#",
            className="sidebar-link",
        )
        for label, group in ECONOMY_GROUPS
    ]
    govt_link = dbc.NavLink(
        "Debt & Deficit",
        id={"type": "nav-link", "page": "government"},
        href="#",
        className="sidebar-link",
    )
    calendar_link = dbc.NavLink(
        "Calendar",
        id={"type": "nav-link", "page": "calendar"},
        href="#",
        className="sidebar-link",
    )
    news_link = dbc.NavLink(
        "News Feed",
        id={"type": "nav-link", "page": "news"},
        href="#",
        className="sidebar-link",
    )

    return html.Div(
        [
            html.Div(
                [
                    html.H5("TE DASHBOARD", className="sidebar-brand"),
                    html.Hr(style={"borderColor": "#444"}),
                ],
            ),
            html.Div("MARKETS", className="sidebar-heading"),
            dbc.Nav(market_links, vertical=True, pills=True),
            html.Hr(style={"borderColor": "#333", "margin": "12px 0"}),
            html.Div("ECONOMY", className="sidebar-heading"),
            dbc.Nav(econ_links, vertical=True, pills=True),
            html.Hr(style={"borderColor": "#333", "margin": "12px 0"}),
            html.Div("GOVERNMENT", className="sidebar-heading"),
            dbc.Nav([govt_link], vertical=True, pills=True),
            html.Hr(style={"borderColor": "#333", "margin": "12px 0"}),
            dbc.Nav([calendar_link, news_link], vertical=True, pills=True),
            html.Hr(style={"borderColor": "#333", "margin": "12px 0"}),
            html.Div(
                [
                    html.Label("Auto-refresh", style={"color": "#888", "fontSize": "12px"}),
                    dcc.Dropdown(
                        id="refresh-interval",
                        options=[
                            {"label": "Off", "value": 0},
                            {"label": "1 min", "value": 60},
                            {"label": "5 min", "value": 300},
                            {"label": "15 min", "value": 900},
                        ],
                        value=300,
                        clearable=False,
                        style={"backgroundColor": "#2a2a2e", "color": "#fff", "fontSize": "13px"},
                    ),
                    dbc.Button(
                        "Refresh Now",
                        id="btn-refresh",
                        color="info",
                        size="sm",
                        className="mt-2 w-100",
                    ),
                ],
                className="mt-2",
            ),
        ],
        className="sidebar",
    )


# ── Layout ───────────────────────────────────────────────────
app.layout = html.Div(
    [
        # Intervals
        dcc.Interval(id="ticker-interval", interval=60 * 1000, n_intervals=0),
        dcc.Interval(id="main-interval", interval=300 * 1000, n_intervals=0),
        # State stores
        dcc.Store(id="current-page", data="market-index"),
        dcc.Store(id="drilldown-indicator", data=None),
        dcc.Store(id="bond-drilldown", data=None),
        # Ticker bar
        html.Div(
            html.Div(id="ticker-content", className="ticker-track"),
            className="ticker-bar",
        ),
        # Body: sidebar + main
        html.Div(
            [
                build_sidebar(),
                html.Div(
                    [
                        dcc.Loading(
                            id="main-loading",
                            type="dot",
                            color="#00b0ff",
                            children=html.Div(id="main-content"),
                        )
                    ],
                    className="main-panel",
                ),
            ],
            className="body-wrapper",
        ),
    ]
)


# ── Callbacks ────────────────────────────────────────────────

# 1. Update ticker bar
@app.callback(Output("ticker-content", "children"), Input("ticker-interval", "n_intervals"))
def update_ticker(_):
    return build_ticker_items()


# 2. Update auto-refresh interval
@app.callback(Output("main-interval", "interval"), Input("refresh-interval", "value"))
def set_interval(val):
    if not val:
        return 24 * 60 * 60 * 1000  # effectively off
    return val * 1000


# 3. Navigation: clicking sidebar links updates current-page store
@app.callback(
    Output("current-page", "data"),
    Input({"type": "nav-link", "page": dash.ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def navigate(clicks):
    ctx = callback_context
    if not ctx.triggered:
        return no_update
    prop_id = ctx.triggered[0]["prop_id"]
    # extract page from the pattern-matched id
    import json as _json
    try:
        id_dict = _json.loads(prop_id.split(".")[0])
        return id_dict["page"]
    except Exception:
        return no_update


# 4. Main content renderer
@app.callback(
    Output("main-content", "children"),
    [
        Input("current-page", "data"),
        Input("drilldown-indicator", "data"),
        Input("bond-drilldown", "data"),
        Input("main-interval", "n_intervals"),
        Input("btn-refresh", "n_clicks"),
    ],
)
def render_main(page, drilldown, bond_dd, _interval, _refresh):
    ctx = callback_context
    triggered = ctx.triggered[0]["prop_id"] if ctx.triggered else ""

    if "btn-refresh" in triggered:
        te.clear_cache()

    # Drill-down views
    if drilldown:
        return render_drilldown(drilldown)
    if bond_dd:
        return render_bond_drilldown(bond_dd["name"], bond_dd["symbol"])

    if not page:
        page = "market-index"

    if page.startswith("market-"):
        mtype = page.replace("market-", "")
        return render_market(mtype)
    elif page.startswith("econ-"):
        group = page.replace("econ-", "")
        return render_economy(group)
    elif page == "government":
        return render_government()
    elif page == "calendar":
        return render_calendar()
    elif page == "news":
        return render_news()
    return html.Div("Select a category from the sidebar.", className="text-muted p-4")


# 5. Table row click → drilldown
@app.callback(
    Output("drilldown-indicator", "data"),
    [
        Input("econ-table", "active_cell"),
        Input("btn-back", "n_clicks"),
    ],
    State("econ-table", "data"),
    prevent_initial_call=True,
)
def handle_drilldown(active_cell, back_clicks, table_data):
    ctx = callback_context
    triggered = ctx.triggered[0]["prop_id"] if ctx.triggered else ""
    if "btn-back" in triggered:
        return None
    if active_cell and table_data:
        row = table_data[active_cell["row"]]
        return row.get("Category", None)
    return no_update


# 6. Bond table row click → bond drilldown
@app.callback(
    Output("bond-drilldown", "data"),
    [
        Input("bond-table", "active_cell"),
        Input("btn-back-bond", "n_clicks"),
    ],
    State("bond-table", "data"),
    prevent_initial_call=True,
)
def handle_bond_drilldown(active_cell, back_clicks, table_data):
    ctx = callback_context
    triggered = ctx.triggered[0]["prop_id"] if ctx.triggered else ""
    if "btn-back-bond" in triggered:
        return None
    if active_cell and table_data:
        row = table_data[active_cell["row"]]
        name = row.get("Name", "")
        symbol = row.get("Symbol", "")
        if name and symbol:
            return {"name": name, "symbol": symbol}
    return no_update


# ── Render functions ─────────────────────────────────────────

def render_market(mtype):
    """Render a markets table (indices, bonds, FX, commodities)."""
    df = te.get_markets(mtype)
    if df.empty:
        return html.Div("No data available.", className="text-muted p-4")

    title_map = {"index": "Stock Indices", "bond": "Government Bonds",
                 "currency": "Currencies", "commodities": "Commodities"}

    cols_display = []
    for c in ["Name", "Last", "Close", "DailyChange", "DailyPercentualChange",
              "WeeklyPercentualChange", "MonthlyPercentualChange", "YearlyPercentualChange"]:
        if c in df.columns:
            cols_display.append(c)

    col_rename = {
        "DailyChange": "Chg",
        "DailyPercentualChange": "Chg %",
        "WeeklyPercentualChange": "Week %",
        "MonthlyPercentualChange": "Month %",
        "YearlyPercentualChange": "Year %",
    }

    display_df = df[cols_display].copy()
    display_df.rename(columns=col_rename, inplace=True)

    # Round numeric columns
    for c in display_df.select_dtypes(include="number").columns:
        display_df[c] = display_df[c].round(3)

    children = [html.H4(title_map.get(mtype, mtype), className="content-title")]

    # Special: yield curve chart for bonds
    if mtype == "bond":
        children.append(build_yield_curve(df))
        # Include Symbol column (hidden) for drill-down lookup
        if "Symbol" in df.columns:
            display_df["Symbol"] = df["Symbol"].values[:len(display_df)]
        children.append(
            html.P("Click any row to drill down into historical yield data.",
                    style={"color": "#888", "fontSize": "13px"}),
        )
        bond_cols = [{"name": c, "id": c} for c in display_df.columns if c != "Symbol"]
        bond_cols.append({"name": "Symbol", "id": "Symbol", "hideable": True})
        children.append(
            dash_table.DataTable(
                id="bond-table",
                data=display_df.to_dict("records"),
                columns=bond_cols,
                hidden_columns=["Symbol"],
                sort_action="native",
                style_table={"overflowX": "auto"},
                style_header=TABLE_HEADER_STYLE,
                style_cell={**TABLE_CELL_STYLE, "cursor": "pointer"},
                style_data_conditional=conditional_coloring(display_df, "Chg %"),
                page_size=30,
            )
        )
        return html.Div(children, className="p-3")

    children.append(
        dash_table.DataTable(
            data=display_df.to_dict("records"),
            columns=[{"name": c, "id": c} for c in display_df.columns],
            sort_action="native",
            style_table={"overflowX": "auto"},
            style_header=TABLE_HEADER_STYLE,
            style_cell=TABLE_CELL_STYLE,
            style_data_conditional=conditional_coloring(display_df, "Chg %"),
            page_size=30,
        )
    )
    return html.Div(children, className="p-3")


def _format_stat_value(val, unit):
    """Format a stat card value based on its unit."""
    unit_str = str(unit) if unit else ""
    if pd.isna(val):
        return "N/A"
    if "Billion" in unit_str and abs(val) >= 1000:
        return f"${val / 1000:,.1f}T"
    if "Billion" in unit_str:
        return f"${val:,.1f}B"
    if "Million" in unit_str and abs(val) >= 1_000_000:
        return f"${val / 1_000_000:,.2f}T"
    if "Million" in unit_str and abs(val) >= 1000:
        return f"${val / 1000:,.1f}B"
    if "Million" in unit_str:
        return f"${val:,.0f}M"
    if "percent" in unit_str.lower() or unit_str == "percent":
        return f"{val:,.1f}%"
    if "USD/Hour" in unit_str:
        return f"${val:.2f}/hr"
    if "USD" in unit_str and "per" not in unit_str.lower():
        return f"${val:,.1f}"
    if "points" in unit_str.lower():
        return f"{val:,.1f}"
    if "Thousand" in unit_str:
        return f"{val:,.0f}K"
    return f"{val:,.2f}"


def render_economy(group):
    """Render economy category with stat cards, charts, and clickable table."""
    df = te.get_snapshot_by_group(group)
    if df.empty:
        return html.Div("No data available.", className="text-muted p-4")

    group_labels = dict(ECONOMY_GROUPS)
    title = group_labels.get(group, group)
    highlights = CATEGORY_HIGHLIGHTS.get(group, {})

    children = [html.H4(title, className="content-title")]

    # ── Stat cards ──
    stat_names = highlights.get("stats", [])
    if stat_names:
        stat_cols = []
        for name in stat_names[:4]:
            row = df[df["Category"] == name]
            if row.empty:
                stat_cols.append(dbc.Col(dbc.Card(dbc.CardBody([
                    html.P(name, style={"color": "#888", "fontSize": "12px", "margin": 0}),
                    html.H5("N/A", style={"color": "#fff", "margin": 0}),
                ]), className="bg-dark border-secondary"), md=3))
                continue
            r = row.iloc[0]
            val = r.get("LatestValue", 0)
            prev = r.get("PreviousValue", 0)
            unit = r.get("Unit", "")
            val_str = _format_stat_value(val, unit)
            chg = (val - prev) if pd.notna(prev) and prev else 0
            color = "#ff1744" if chg < 0 else "#00e676" if chg > 0 else "#888"
            chg_str = f" ({chg:+,.2f})" if chg != 0 else ""
            stat_cols.append(dbc.Col(dbc.Card(dbc.CardBody([
                html.P(name, style={"color": "#888", "fontSize": "12px", "margin": 0}),
                html.H5(val_str, style={"color": "#fff", "margin": "4px 0"}),
                html.Span(chg_str, style={"color": color, "fontSize": "12px"}) if chg_str else html.Span(),
            ]), className="bg-dark border-secondary"), md=3))
        children.append(dbc.Row(stat_cols, className="mb-4 g-3"))

    # ── Historical charts for key indicators ──
    chart_names = highlights.get("charts", [])
    for i, ind_name in enumerate(chart_names[:4]):
        try:
            hist = te.get_historical(ind_name)
        except Exception:
            continue
        if hist.empty:
            continue

        color = CHART_COLORS[i % len(CHART_COLORS)]
        # Get unit for y-axis label
        ind_row = df[df["Category"] == ind_name]
        unit = str(ind_row.iloc[0].get("Unit", "")) if not ind_row.empty else ""

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hist["DateTime"], y=hist["Value"],
            mode="lines",
            name=ind_name,
            line=dict(color=color, width=2.5),
            fill="tozeroy",
            fillcolor=color.replace(")", ",0.08)").replace("rgb", "rgba") if "rgb" in color else f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.08)",
        ))

        y_title = unit if unit else ""
        tick_fmt = {}
        if "percent" in unit.lower():
            tick_fmt = {"ticksuffix": "%"}
        elif "Billion" in unit:
            tick_fmt = {"tickprefix": "$"}
        elif "Million" in unit:
            tick_fmt = {"tickprefix": "$"}

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e1e22", plot_bgcolor="#1e1e22",
            margin=dict(l=50, r=30, t=40, b=40),
            title=dict(text=ind_name, font=dict(size=16)),
            xaxis=dict(gridcolor="#333"),
            yaxis=dict(gridcolor="#333", title=y_title, **tick_fmt),
            hovermode="x unified",
            height=320,
        )

        # Add zero reference line for indicators that go negative
        if hist["Value"].min() < 0:
            fig.add_hline(y=0, line_color="#555", line_width=1)

        children.append(dcc.Graph(figure=fig, config={"displayModeBar": True}, className="mb-3"))

    # ── Full data table ──
    children.append(html.H5("All Indicators",
                             style={"color": "#aaa", "marginTop": "20px", "marginBottom": "10px"}))
    children.append(html.P("Click any row to drill down into historical data.",
                            style={"color": "#888", "fontSize": "13px"}))

    cols = ["Category", "LatestValue", "PreviousValue", "Change", "PctChange",
            "Unit", "LatestValueDate", "Frequency"]
    cols = [c for c in cols if c in df.columns]
    display_df = df[cols].copy()
    display_df.rename(columns={
        "LatestValue": "Latest",
        "PreviousValue": "Previous",
        "PctChange": "Chg %",
        "LatestValueDate": "Date",
    }, inplace=True)

    if "Date" in display_df.columns:
        display_df["Date"] = display_df["Date"].astype(str).str[:10]

    for c in display_df.select_dtypes(include="number").columns:
        display_df[c] = display_df[c].round(3)

    children.append(
        dash_table.DataTable(
            id="econ-table",
            data=display_df.to_dict("records"),
            columns=[{"name": c, "id": c} for c in display_df.columns],
            sort_action="native",
            style_table={"overflowX": "auto"},
            style_header=TABLE_HEADER_STYLE,
            style_cell={**TABLE_CELL_STYLE, "cursor": "pointer"},
            style_data_conditional=conditional_coloring(display_df, "Chg %"),
            page_size=30,
        )
    )

    return html.Div(children, className="p-3")


def render_drilldown(indicator):
    """Render historical chart + forecast for a single indicator."""
    hist = te.get_historical(indicator)
    chart_children = []

    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1e1e22",
        plot_bgcolor="#1e1e22",
        margin=dict(l=50, r=30, t=40, b=40),
        title=dict(text=indicator, font=dict(size=18)),
        xaxis=dict(gridcolor="#333"),
        yaxis=dict(gridcolor="#333"),
        hovermode="x unified",
    )

    if not hist.empty:
        fig.add_trace(go.Scatter(
            x=hist["DateTime"], y=hist["Value"],
            mode="lines",
            name="Actual",
            line=dict(color="#00b0ff", width=2),
            fill="tozeroy",
            fillcolor="rgba(0,176,255,0.08)",
        ))

    # Try to add forecast point
    try:
        fc = te.get_forecasts()
        fc_row = fc[fc["Category"] == indicator]
        if not fc_row.empty:
            r = fc_row.iloc[0]
            for qcol, dcol in [("q1", "q1_date"), ("q2", "q2_date"),
                                ("q3", "q3_date"), ("q4", "q4_date")]:
                if qcol in r and dcol in r and pd.notna(r[qcol]) and pd.notna(r[dcol]):
                    fig.add_trace(go.Scatter(
                        x=[pd.to_datetime(r[dcol])],
                        y=[float(r[qcol])],
                        mode="markers+text",
                        name=f"Forecast ({qcol.upper()})",
                        marker=dict(color="#ffd740", size=10, symbol="diamond"),
                        text=[f"{float(r[qcol]):.2f}"],
                        textposition="top center",
                        textfont=dict(color="#ffd740"),
                    ))
    except Exception:
        pass

    chart_children.append(dcc.Graph(figure=fig, config={"displayModeBar": True}))

    # Recent data table
    if not hist.empty:
        recent = hist.tail(20).iloc[::-1].copy()
        recent["DateTime"] = recent["DateTime"].dt.strftime("%Y-%m-%d")
        recent["Value"] = recent["Value"].round(3)
        chart_children.append(
            html.Div(
                [
                    html.H6("Recent Values", className="mt-3 mb-2", style={"color": "#aaa"}),
                    dash_table.DataTable(
                        data=recent[["DateTime", "Value"]].to_dict("records"),
                        columns=[{"name": "Date", "id": "DateTime"}, {"name": "Value", "id": "Value"}],
                        style_header=TABLE_HEADER_STYLE,
                        style_cell=TABLE_CELL_STYLE,
                        page_size=10,
                    ),
                ]
            )
        )

    return html.Div(
        [
            dbc.Button("\u2190 Back", id="btn-back", color="secondary", size="sm", className="mb-3"),
            html.H4(indicator, className="content-title"),
        ]
        + chart_children,
        className="p-3",
    )


def render_bond_drilldown(name, symbol):
    """Render historical OHLC chart for a bond."""
    hist = te.get_market_historical(symbol)

    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1e1e22",
        plot_bgcolor="#1e1e22",
        margin=dict(l=50, r=30, t=50, b=40),
        title=dict(text=f"{name} — Yield History", font=dict(size=18)),
        xaxis=dict(gridcolor="#333", title="Date"),
        yaxis=dict(gridcolor="#333", title="Yield (%)"),
        hovermode="x unified",
        height=500,
    )

    if not hist.empty:
        # Candlestick chart
        fig.add_trace(go.Candlestick(
            x=hist["Date"],
            open=hist["Open"],
            high=hist["High"],
            low=hist["Low"],
            close=hist["Close"],
            name="OHLC",
            increasing_line_color="#00e676",
            decreasing_line_color="#ff1744",
        ))
        # Closing yield line overlay
        fig.add_trace(go.Scatter(
            x=hist["Date"], y=hist["Close"],
            mode="lines",
            name="Close",
            line=dict(color="#00b0ff", width=1.5),
            opacity=0.6,
        ))
        fig.update_layout(xaxis_rangeslider_visible=False)

    chart_children = [dcc.Graph(figure=fig, config={"displayModeBar": True})]

    # Recent data table
    if not hist.empty:
        recent = hist.tail(20).iloc[::-1].copy()
        recent["Date"] = recent["Date"].dt.strftime("%Y-%m-%d")
        for c in ["Open", "High", "Low", "Close"]:
            if c in recent.columns:
                recent[c] = recent[c].round(3)
        chart_children.append(
            html.Div(
                [
                    html.H6("Recent OHLC", className="mt-3 mb-2", style={"color": "#aaa"}),
                    dash_table.DataTable(
                        data=recent[["Date", "Open", "High", "Low", "Close"]].to_dict("records"),
                        columns=[{"name": c, "id": c} for c in ["Date", "Open", "High", "Low", "Close"]],
                        style_header=TABLE_HEADER_STYLE,
                        style_cell=TABLE_CELL_STYLE,
                        page_size=10,
                    ),
                ]
            )
        )

    return html.Div(
        [
            dbc.Button("\u2190 Back to Bonds", id="btn-back-bond", color="secondary", size="sm", className="mb-3"),
            html.H4(f"{name} Yield", className="content-title"),
        ]
        + chart_children,
        className="p-3",
    )


def render_government():
    """Render Government Debt & Deficit dashboard with charts and stats."""
    snapshot = te.get_snapshot_by_group("Government")

    # ── Key stats cards ──
    def _stat(label, category, fmt=",.0f", suffix=""):
        if snapshot.empty:
            return dbc.Col(dbc.Card(dbc.CardBody([
                html.P(label, style={"color": "#888", "fontSize": "12px", "margin": 0}),
                html.H5("N/A", style={"color": "#fff", "margin": 0}),
            ]), className="bg-dark border-secondary"), md=3)
        row = snapshot[snapshot["Category"] == category]
        if row.empty:
            val_str = "N/A"
            chg = 0
        else:
            r = row.iloc[0]
            val = r.get("LatestValue", 0)
            prev = r.get("PreviousValue", 0)
            unit = r.get("Unit", "")
            chg = val - prev if prev else 0
            if "Million" in str(unit) and val > 1_000_000:
                val_str = f"${val / 1_000_000:,.2f}T"
            elif "Million" in str(unit) and val > 1_000:
                val_str = f"${val / 1_000:,.1f}B"
            elif "Million" in str(unit):
                val_str = f"${val:,.0f}M"
            elif "Billion" in str(unit):
                val_str = f"${val:,.0f}B"
            elif "percent" in str(unit).lower():
                val_str = f"{val:.1f}%"
            else:
                val_str = f"{val:{fmt}}{suffix}"
        color = "#ff1744" if chg < 0 else "#00e676" if chg > 0 else "#888"
        return dbc.Col(dbc.Card(dbc.CardBody([
            html.P(label, style={"color": "#888", "fontSize": "12px", "margin": 0}),
            html.H5(val_str, style={"color": "#fff", "margin": "4px 0"}),
        ]), className="bg-dark border-secondary"), md=3)

    stat_row = dbc.Row([
        _stat("Total Debt", "Government Debt"),
        _stat("Debt / GDP", "Government Debt to GDP"),
        _stat("Budget Deficit (% GDP)", "Government Budget"),
        _stat("Monthly Deficit", "Government Budget Value"),
    ], className="mb-4 g-3")

    children = [
        html.H4("US Government Debt & Deficit", className="content-title"),
        stat_row,
    ]

    # ── Debt chart ──
    debt_hist = te.get_historical("Government Debt")
    if not debt_hist.empty:
        debt_hist["Trillions"] = debt_hist["Value"] / 1_000_000  # value in millions
        fig_debt = go.Figure()
        fig_debt.add_trace(go.Scatter(
            x=debt_hist["DateTime"], y=debt_hist["Trillions"],
            mode="lines",
            name="Total Debt",
            line=dict(color="#ff1744", width=2.5),
            fill="tozeroy",
            fillcolor="rgba(255,23,68,0.08)",
        ))
        fig_debt.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e1e22", plot_bgcolor="#1e1e22",
            margin=dict(l=50, r=30, t=40, b=40),
            title=dict(text="US Federal Debt (Trillions USD)", font=dict(size=16)),
            xaxis=dict(gridcolor="#333"),
            yaxis=dict(gridcolor="#333", title="$ Trillions", tickprefix="$", tickformat=",.1f"),
            hovermode="x unified",
            height=350,
        )
        children.append(dcc.Graph(figure=fig_debt, config={"displayModeBar": True}, className="mb-3"))

    # ── Debt-to-GDP chart ──
    dtg_hist = te.get_historical("Government Debt to GDP")
    if not dtg_hist.empty:
        fig_dtg = go.Figure()
        fig_dtg.add_trace(go.Scatter(
            x=dtg_hist["DateTime"], y=dtg_hist["Value"],
            mode="lines+markers",
            name="Debt / GDP",
            line=dict(color="#ffd740", width=2.5),
            marker=dict(size=4),
            fill="tozeroy",
            fillcolor="rgba(255,215,64,0.08)",
        ))
        # Reference line at 100%
        fig_dtg.add_hline(y=100, line_dash="dash", line_color="#ff1744",
                          annotation_text="100% of GDP", annotation_position="top left",
                          annotation_font_color="#ff1744")
        fig_dtg.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e1e22", plot_bgcolor="#1e1e22",
            margin=dict(l=50, r=30, t=40, b=40),
            title=dict(text="Debt-to-GDP Ratio (%)", font=dict(size=16)),
            xaxis=dict(gridcolor="#333"),
            yaxis=dict(gridcolor="#333", title="% of GDP", ticksuffix="%"),
            hovermode="x unified",
            height=350,
        )
        children.append(dcc.Graph(figure=fig_dtg, config={"displayModeBar": True}, className="mb-3"))

    # ── Budget Deficit (% of GDP) chart ──
    budget_hist = te.get_historical("Government Budget")
    if not budget_hist.empty:
        fig_bud = go.Figure()
        colors = ["#00e676" if v >= 0 else "#ff1744" for v in budget_hist["Value"]]
        fig_bud.add_trace(go.Bar(
            x=budget_hist["DateTime"], y=budget_hist["Value"],
            name="Budget Balance",
            marker_color=colors,
        ))
        fig_bud.add_hline(y=0, line_color="#555", line_width=1)
        fig_bud.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e1e22", plot_bgcolor="#1e1e22",
            margin=dict(l=50, r=30, t=40, b=40),
            title=dict(text="Budget Balance (% of GDP)", font=dict(size=16)),
            xaxis=dict(gridcolor="#333"),
            yaxis=dict(gridcolor="#333", title="% of GDP", ticksuffix="%"),
            hovermode="x unified",
            height=350,
        )
        children.append(dcc.Graph(figure=fig_bud, config={"displayModeBar": True}, className="mb-3"))

    # ── Monthly Budget Value chart ──
    monthly_hist = te.get_historical("Government Budget Value")
    if not monthly_hist.empty:
        monthly_hist["Billions"] = monthly_hist["Value"] / 1_000  # value in millions
        fig_mth = go.Figure()
        colors_m = ["#00e676" if v >= 0 else "#ff1744" for v in monthly_hist["Billions"]]
        fig_mth.add_trace(go.Bar(
            x=monthly_hist["DateTime"], y=monthly_hist["Billions"],
            name="Monthly Balance",
            marker_color=colors_m,
        ))
        fig_mth.add_hline(y=0, line_color="#555", line_width=1)
        fig_mth.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e1e22", plot_bgcolor="#1e1e22",
            margin=dict(l=50, r=30, t=40, b=40),
            title=dict(text="Monthly Budget Surplus / Deficit (Billions USD)", font=dict(size=16)),
            xaxis=dict(gridcolor="#333"),
            yaxis=dict(gridcolor="#333", title="$ Billions", tickprefix="$", tickformat=",.0f"),
            hovermode="x unified",
            height=350,
        )
        children.append(dcc.Graph(figure=fig_mth, config={"displayModeBar": True}, className="mb-3"))

    # ── All Government indicators table ──
    if not snapshot.empty:
        cols = ["Category", "LatestValue", "PreviousValue", "Change", "PctChange",
                "Unit", "LatestValueDate", "Frequency"]
        cols = [c for c in cols if c in snapshot.columns]
        tbl_df = snapshot[cols].copy()
        tbl_df.rename(columns={
            "LatestValue": "Latest", "PreviousValue": "Previous",
            "PctChange": "Chg %", "LatestValueDate": "Date",
        }, inplace=True)
        if "Date" in tbl_df.columns:
            tbl_df["Date"] = tbl_df["Date"].astype(str).str[:10]
        for c in tbl_df.select_dtypes(include="number").columns:
            tbl_df[c] = tbl_df[c].round(2)

        children.append(html.H5("All Government Indicators",
                                 style={"color": "#aaa", "marginTop": "20px", "marginBottom": "10px"}))
        children.append(
            dash_table.DataTable(
                data=tbl_df.to_dict("records"),
                columns=[{"name": c, "id": c} for c in tbl_df.columns],
                sort_action="native",
                style_table={"overflowX": "auto"},
                style_header=TABLE_HEADER_STYLE,
                style_cell=TABLE_CELL_STYLE,
                style_data_conditional=conditional_coloring(tbl_df, "Chg %"),
                page_size=20,
            )
        )

    return html.Div(children, className="p-3")


def render_calendar():
    """Render today's US economic calendar."""
    from datetime import datetime
    df = te.get_calendar()
    if df.empty:
        return html.Div(
            [
                html.H4("Economic Calendar", className="content-title"),
                html.P("No calendar events available.", className="text-muted"),
            ],
            className="p-3",
        )

    today_str = datetime.now().strftime("%A %B %d %Y")

    # Build grouped content by date
    children = [html.H4("US Economic Calendar", className="content-title")]

    dates = df["Date"].unique() if "Date" in df.columns else [""]
    for date_label in dates:
        if date_label:
            # Highlight today's date
            is_today = today_str.lower() in date_label.lower()
            date_style = {
                "color": "#00e676" if is_today else "#00b0ff",
                "marginTop": "20px",
                "marginBottom": "10px",
                "fontSize": "16px",
            }
            label_text = f"{date_label}  (TODAY)" if is_today else date_label
            children.append(html.H5(label_text, style=date_style))

        date_df = df[df["Date"] == date_label] if date_label else df

        rows_data = []
        for _, row in date_df.iterrows():
            rows_data.append({
                "Time": row.get("Time", ""),
                "Event": row.get("Event", ""),
                "Actual": row.get("Actual", ""),
                "Consensus": row.get("Consensus", ""),
                "Previous": row.get("Previous", ""),
                "Forecast": row.get("Forecast", ""),
            })

        if not rows_data:
            continue

        cond_styles = [
            {
                "if": {"column_id": "Actual", "filter_query": '{Actual} ne ""'},
                "fontWeight": "700",
                "color": "#00e676",
            },
            {
                "if": {"column_id": "Event"},
                "textAlign": "left",
                "minWidth": "280px",
            },
            {
                "if": {"column_id": "Time"},
                "color": "#888",
                "width": "80px",
            },
        ]

        children.append(
            dash_table.DataTable(
                data=rows_data,
                columns=[
                    {"name": "Time", "id": "Time"},
                    {"name": "Event", "id": "Event"},
                    {"name": "Actual", "id": "Actual"},
                    {"name": "Consensus", "id": "Consensus"},
                    {"name": "Previous", "id": "Previous"},
                    {"name": "TE Forecast", "id": "Forecast"},
                ],
                style_table={"overflowX": "auto", "marginBottom": "20px"},
                style_header=TABLE_HEADER_STYLE,
                style_cell={**TABLE_CELL_STYLE, "textAlign": "center"},
                style_data_conditional=cond_styles,
                page_size=50,
            )
        )

    return html.Div(children, className="p-3")


def render_news():
    """Render news feed as cards."""
    df = te.get_news()
    if df.empty:
        return html.Div("No news available.", className="text-muted p-4")

    cards = []
    for _, row in df.iterrows():
        imp = row.get("importance", 1)
        badge_color = "danger" if imp >= 3 else "warning" if imp >= 2 else "info"
        badge = dbc.Badge(f"Imp: {imp}", color=badge_color, className="me-2")
        cat_badge = dbc.Badge(row.get("category", ""), color="secondary", className="me-2")

        date_str = ""
        if pd.notna(row.get("date")):
            date_str = row["date"].strftime("%b %d, %H:%M")

        cards.append(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.Div(
                            [badge, cat_badge, html.Span(date_str, style={"color": "#888", "fontSize": "12px"})],
                            className="mb-2",
                        ),
                        html.H6(row.get("title", ""), className="card-title", style={"color": "#e0e0e0"}),
                        html.P(
                            row.get("description", "")[:300] + ("..." if len(str(row.get("description", ""))) > 300 else ""),
                            style={"color": "#999", "fontSize": "13px", "lineHeight": "1.5"},
                        ),
                    ]
                ),
                className="news-card mb-2",
            )
        )

    return html.Div(
        [html.H4("US Economic News", className="content-title")] + cards,
        className="p-3",
    )


def build_yield_curve(bond_df):
    """Build a US Treasury yield curve chart."""
    # Parse tenor from bond names
    tenors = []
    import re
    for _, row in bond_df.iterrows():
        name = str(row.get("Name", ""))
        if not name.startswith("US "):
            continue
        tenor_str = name.replace("US ", "")
        # Skip TIPS and other non-standard bonds
        if "TIPS" in tenor_str or "BOND" in tenor_str.upper():
            continue
        last = row.get("Last", None)
        if last is None:
            continue
        # Convert to months for sorting
        months = 0
        try:
            num = float(re.search(r"[\d.]+", tenor_str).group())
        except (AttributeError, ValueError):
            continue
        if "W" in tenor_str:
            months = num / 4.33
        elif "M" in tenor_str:
            months = num
        elif "Y" in tenor_str:
            months = num * 12
        else:
            continue
        tenors.append({"tenor": tenor_str, "months": months, "yield": last})

    if not tenors:
        return html.Div()

    tenors.sort(key=lambda x: x["months"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[t["tenor"] for t in tenors],
        y=[t["yield"] for t in tenors],
        mode="lines+markers",
        line=dict(color="#00e676", width=3),
        marker=dict(size=8, color="#00e676"),
        fill="tozeroy",
        fillcolor="rgba(0,230,118,0.08)",
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1e1e22",
        plot_bgcolor="#1e1e22",
        margin=dict(l=50, r=30, t=40, b=40),
        title=dict(text="US Treasury Yield Curve", font=dict(size=16)),
        xaxis=dict(title="Tenor", gridcolor="#333"),
        yaxis=dict(title="Yield (%)", gridcolor="#333"),
        height=320,
    )
    return dcc.Graph(figure=fig, config={"displayModeBar": False}, className="mb-3")


# ── Table styles ─────────────────────────────────────────────

TABLE_HEADER_STYLE = {
    "backgroundColor": "#2a2a2e",
    "color": "#aaa",
    "fontWeight": "600",
    "fontSize": "13px",
    "border": "1px solid #333",
}
TABLE_CELL_STYLE = {
    "backgroundColor": "#1e1e22",
    "color": "#e0e0e0",
    "fontSize": "13px",
    "border": "1px solid #2a2a2e",
    "padding": "8px 12px",
}


def conditional_coloring(df, chg_col):
    """Green/red coloring for change columns."""
    styles = []
    if chg_col in df.columns:
        styles.extend([
            {
                "if": {"filter_query": f"{{{chg_col}}} > 0", "column_id": chg_col},
                "color": "#00e676",
            },
            {
                "if": {"filter_query": f"{{{chg_col}}} < 0", "column_id": chg_col},
                "color": "#ff1744",
            },
        ])
    if "Change" in df.columns:
        styles.extend([
            {
                "if": {"filter_query": "{Change} > 0", "column_id": "Change"},
                "color": "#00e676",
            },
            {
                "if": {"filter_query": "{Change} < 0", "column_id": "Change"},
                "color": "#ff1744",
            },
        ])
    if "Chg" in df.columns:
        styles.extend([
            {
                "if": {"filter_query": "{Chg} > 0", "column_id": "Chg"},
                "color": "#00e676",
            },
            {
                "if": {"filter_query": "{Chg} < 0", "column_id": "Chg"},
                "color": "#ff1744",
            },
        ])
    return styles


# ── Run ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n  Trading Economics Dashboard")
    print("  Open http://127.0.0.1:8050 in your browser\n")
    app.run(debug=False, port=8050)
