from dash import html, dcc, dash_table, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from dash.dash_table.Format import Format, Scheme, Symbol

# --- LAYOUT ---
layout = html.Div([
    html.H2("📊 Advanced Revenue Insights", className="mb-4 text-center text-white"),
    html.Div(id="insights-content")
])


# --- LOGIC & CALLBACKS ---
def register_callbacks(app):
    @app.callback(
        Output("insights-content", "children"),
        Input("global-data-store", "data")
    )
    def update_insights(data):
        if not data:
            return dbc.Alert("No data available.", color="warning")

        # 1. Load Data
        df = pd.DataFrame(data)

        # 2. Data Cleaning
        required_cols = ['lastPaymentReceivedOn', 'lastAmountPaidEUR', 'Date', 'Subscription_Type']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return dbc.Alert(f"Data missing required columns: {missing_cols}.", color="danger")

        # --- DATE CONVERSION ---
        df['lastPaymentReceivedOn'] = pd.to_datetime(df['lastPaymentReceivedOn'], errors='coerce', utc=True)
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce', utc=True)
        df['lastAmountPaidEUR'] = pd.to_numeric(df['lastAmountPaidEUR'], errors='coerce')

        df = df.dropna(subset=['lastPaymentReceivedOn', 'Date', 'lastAmountPaidEUR', 'Subscription_Type'])

        # ==============================================================================
        # ✅ APPLIED FILTERS
        # ==============================================================================
        valid_types = ['new', 'renewed', 'upgraded']
        df['type_norm'] = df['Subscription_Type'].astype(str).str.lower()
        df = df[df['type_norm'].isin(valid_types)]

        df_clean = df[df['lastPaymentReceivedOn'] >= df['Date']].copy()

        if df_clean.empty:
            return dbc.Alert("No data found after applying filters.", color="warning")

        # ==============================================================================
        # 🧮 CALCULATIONS
        # ==============================================================================

        # --- 1. Global Time Period (Total Calendar Days) ---
        global_min_date = df_clean['lastPaymentReceivedOn'].min()
        global_max_date = df_clean['lastPaymentReceivedOn'].max()

        # Calculate span of days (inclusive)
        total_days_period = (global_max_date - global_min_date).days + 1
        if total_days_period < 1: total_days_period = 1

        # --- 2. Daily Aggregation ---
        # Normalize to date (Active days only initially)
        daily_sums = df_clean.groupby(df_clean['lastPaymentReceivedOn'].dt.date)[
            'lastAmountPaidEUR'].sum().reset_index()
        daily_sums.columns = ['Date', 'Daily_Revenue']

        # Ensure Date column is datetime objects for monthly extraction
        daily_sums['Date'] = pd.to_datetime(daily_sums['Date'])
        daily_sums['Month'] = daily_sums['Date'].dt.to_period('M')

        # --- 3. Monthly Analysis Function ---
        def get_monthly_details(group):
            total_month_rev = group['Daily_Revenue'].sum()

            # Count active days (rows in this group)
            active_days_count = len(group)

            # Determine total days in this specific month (e.g., Jan=31, Feb=28)
            # We take the first date in the group to check the month length
            sample_date = group['Date'].iloc[0]
            days_in_month = sample_date.days_in_month

            # Metric A: Avg per Calendar Day (Correct for Finance)
            avg_all_days = total_month_rev / days_in_month

            # Metric B: Avg per Active Day (Intensity)
            avg_active_days = total_month_rev / active_days_count if active_days_count > 0 else 0

            # Min/Max
            max_day_idx = group['Daily_Revenue'].idxmax()
            min_day_idx = group['Daily_Revenue'].idxmin()

            return pd.Series({
                'Total_Month_Revenue': total_month_rev,

                # Two Averages
                'Avg_All_Days': avg_all_days,
                'Avg_Active_Days': avg_active_days,

                # Details
                'Max_Rev_Date': group.loc[max_day_idx, 'Date'].strftime('%Y-%m-%d'),
                'Max_Rev_Amt': group.loc[max_day_idx, 'Daily_Revenue'],
                'Min_Rev_Date': group.loc[min_day_idx, 'Date'].strftime('%Y-%m-%d'),
                'Min_Rev_Amt': group.loc[min_day_idx, 'Daily_Revenue'],
            })

        monthly_report = daily_sums.groupby('Month').apply(get_monthly_details, include_groups=False).reset_index()
        monthly_report['Month'] = monthly_report['Month'].astype(str)

        # --- 4. Global Statistics ---
        total_rev_overall = df_clean['lastAmountPaidEUR'].sum()

        # KPI 1: Avg All Days (500/200)
        avg_daily_all_days = total_rev_overall / total_days_period

        # KPI 2: Avg Active Days (500/10)
        active_days_count_global = len(daily_sums)
        avg_daily_active_days = total_rev_overall / active_days_count_global if active_days_count_global > 0 else 0

        # Min/Max Global
        max_day_global = daily_sums.loc[daily_sums['Daily_Revenue'].idxmax()]
        min_day_global = daily_sums.loc[daily_sums['Daily_Revenue'].idxmin()]

        # ==============================================================================
        # UI CONSTRUCTION
        # ==============================================================================

        # 1. KPI Cards
        cards = dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Total Revenue"),
                dbc.CardBody([
                    html.H3(f"€{total_rev_overall:,.2f}", className="text-success"),
                    html.Small(f"Over {total_days_period} Days", className="text-muted")
                ])
            ], className="text-center shadow-sm"), width=3),

            # UPDATED CARD: Shows Global Average
            dbc.Col(dbc.Card([
                dbc.CardHeader("Avg Daily (All Days)"),
                dbc.CardBody([
                    html.H3(f"€{avg_daily_all_days:,.2f}", className="text-info"),
                    html.Small(f"Avg Active: €{avg_daily_active_days:,.0f}", className="text-muted")
                ])
            ], className="text-center shadow-sm"), width=3),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Best Day"),
                dbc.CardBody([
                    html.H4(f"€{max_day_global['Daily_Revenue']:,.2f}", className="text-success"),
                    html.Small(f"{max_day_global['Date'].strftime('%Y-%m-%d')}")
                ])
            ], className="text-center shadow-sm"), width=3),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Worst Day"),
                dbc.CardBody([
                    html.H4(f"€{min_day_global['Daily_Revenue']:,.2f}", className="text-danger"),
                    html.Small(f"{min_day_global['Date'].strftime('%Y-%m-%d')}")
                ])
            ], className="text-center shadow-sm"), width=3),
        ], className="mb-4")

        # 2. Graph
        fig = px.bar(daily_sums, x='Date', y='Daily_Revenue', title="Daily Revenue Timeline (Filtered)")
        fig.update_layout(template="plotly_white", xaxis_title="Date", yaxis_title="Revenue (€)")
        graph_section = dbc.Card(dbc.CardBody(dcc.Graph(figure=fig)), className="mb-4 shadow-sm")

        # 3. Data Table
        table_section = dash_table.DataTable(
            data=monthly_report.to_dict('records'),
            columns=[
                {"name": "Month", "id": "Month"},
                {"name": "Total Rev (€)", "id": "Total_Month_Revenue", "type": "numeric",
                 "format": Format(symbol=Symbol.yes, symbol_prefix="€", scheme=Scheme.fixed, precision=2)},

                # --- New Columns ---
                {"name": "Avg (All Days)", "id": "Avg_All_Days", "type": "numeric",
                 "format": Format(symbol=Symbol.yes, symbol_prefix="€", scheme=Scheme.fixed, precision=2)},
                {"name": "Avg (Active Days)", "id": "Avg_Active_Days", "type": "numeric",
                 "format": Format(symbol=Symbol.yes, symbol_prefix="€", scheme=Scheme.fixed, precision=2)},
                # -------------------

                {"name": "Max Date", "id": "Max_Rev_Date"},
                {"name": "Max Amt (€)", "id": "Max_Rev_Amt", "type": "numeric",
                 "format": Format(symbol=Symbol.yes, symbol_prefix="€", scheme=Scheme.fixed, precision=2)},
                {"name": "Min Date", "id": "Min_Rev_Date"},
                {"name": "Min Amt (€)", "id": "Min_Rev_Amt", "type": "numeric",
                 "format": Format(symbol=Symbol.yes, symbol_prefix="€", scheme=Scheme.fixed, precision=2)},
            ],
            style_cell={'padding': '10px', 'textAlign': 'left'},
            style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            sort_action="native",
            page_size=10
        )

        return html.Div([
            cards,
            graph_section,
            html.H4("📅 Detailed Monthly Breakdown", className="mb-3"),
            table_section
        ])