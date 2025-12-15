from dash import html, dcc, dash_table, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from dash.dash_table.Format import Format, Scheme

# --- LAYOUT ---
layout = html.Div([
    html.H2("📅 Subscription Volume Over Time", className="mb-4 text-center text-white"),
    html.Div(id="volume-time-content")
])


# --- CALLBACKS ---
def register_callbacks(app):
    @app.callback(
        Output("volume-time-content", "children"),
        Input("global-data-store", "data")
    )
    def update_volume_time(data):
        if not data:
            return dbc.Alert("No data available.", color="warning")

        df = pd.DataFrame(data)

        # 1. Check Required Columns
        required_cols = ['Date', 'Subscription_Type']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            return dbc.Alert(f"Data missing required columns: {missing_cols}", color="danger")

        # 2. Data Cleaning
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce', utc=True)
        df = df.dropna(subset=['Date'])

        # Keep all data (Active, Trials, Cancelled)
        df_clean = df.copy()

        if df_clean.empty:
            return dbc.Alert("No data found.", color="warning")

        # ==============================================================================
        # 🧮 CALCULATIONS
        # ==============================================================================

        # --- A. Global Period Calculation ---
        global_min_date = df_clean['Date'].min()
        global_max_date = df_clean['Date'].max()
        total_days_period = (global_max_date - global_min_date).days + 1
        if total_days_period < 1: total_days_period = 1

        # --- B. Categorical Counts ---
        df_clean['type_norm'] = df_clean['Subscription_Type'].astype(str).str.lower()

        count_active = len(df_clean[df_clean['type_norm'].isin(['new', 'renewed', 'upgraded'])])
        count_trial = len(df_clean[df_clean['type_norm'] == 'trial'])
        count_cancelled = len(df_clean[df_clean['type_norm'] == 'cancelled'])
        total_subs = len(df_clean)

        # Global Average (Total Subs / Total Calendar Days)
        avg_daily_global = total_subs / total_days_period

        # --- C. Daily Aggregation ---
        daily_counts = df_clean.groupby(df_clean['Date'].dt.date).size().reset_index(name='Daily_Count')
        daily_counts.columns = ['Date', 'Daily_Count']

        # Busiest Day Global
        max_day_global = daily_counts.loc[daily_counts['Daily_Count'].idxmax()]

        # Prepare for Monthly Grouping
        daily_counts['Date'] = pd.to_datetime(daily_counts['Date'])  # Ensure datetime for moth methods
        daily_counts['Month'] = daily_counts['Date'].dt.to_period('M')

        # --- D. Monthly Analysis Helper ---
        def get_monthly_details(group):
            # 1. Total Subs in this Month
            total_month_subs = group['Daily_Count'].sum()

            # 2. Calculate Calendar Days in this specific Month (e.g., Feb=28, Jan=31)
            # We take the first date in the group to identify the month length
            sample_date = group['Date'].iloc[0]
            days_in_month = sample_date.days_in_month

            # 3. Calculate Active Days (Rows in this group)
            active_days_count = len(group)

            # 4. Averages
            avg_all_days = total_month_subs / days_in_month
            avg_active_days = total_month_subs / active_days_count if active_days_count > 0 else 0

            # 5. Min/Max Logic
            max_idx = group['Daily_Count'].idxmax()
            min_idx = group['Daily_Count'].idxmin()

            return pd.Series({
                'Total_Month_Subs': total_month_subs,

                # The Two Averages
                'Avg_All_Days': avg_all_days,
                'Avg_Active_Days': avg_active_days,

                # Peak Day
                'Max_Sub_Date': group.loc[max_idx, 'Date'].strftime('%Y-%m-%d'),
                'Max_Sub_Count': group.loc[max_idx, 'Daily_Count'],

                # Worst Day
                'Min_Sub_Date': group.loc[min_idx, 'Date'].strftime('%Y-%m-%d'),
                'Min_Sub_Count': group.loc[min_idx, 'Daily_Count']
            })

        monthly_report = daily_counts.groupby('Month').apply(get_monthly_details, include_groups=False).reset_index()
        monthly_report['Month'] = monthly_report['Month'].astype(str)

        # ==============================================================================
        # UI CONSTRUCTION
        # ==============================================================================

        # Row 1: Volume Breakdown
        row_1 = dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Total Records"),
                dbc.CardBody([
                    html.H3(f"{total_subs:,}", className="text-dark"),
                    html.Small(f"Over {total_days_period} Days", className="text-muted")
                ])
            ], className="text-center shadow-sm"), width=4),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Active (New/Renew/Up)"),
                dbc.CardBody(html.H3(f"{count_active:,}", className="text-success"))
            ], className="text-center shadow-sm"), width=4),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Trials"),
                dbc.CardBody(html.H3(f"{count_trial:,}", className="text-info"))
            ], className="text-center shadow-sm"), width=4),
        ], className="mb-4")

        # Row 2: Status & Time Stats
        row_2 = dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Cancelled"),
                dbc.CardBody(html.H3(f"{count_cancelled:,}", className="text-danger"))
            ], className="text-center shadow-sm"), width=4),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Avg Daily (Global)"),
                dbc.CardBody([
                    html.H3(f"{avg_daily_global:,.1f}", className="text-primary"),
                    html.Small("Total Subs / Total Cal. Days")
                ])
            ], className="text-center shadow-sm"), width=4),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Busiest Day"),
                dbc.CardBody([
                    html.H4(f"{max_day_global['Daily_Count']:,}", className="text-success"),
                    html.Small(f"{max_day_global['Date'].strftime('%Y-%m-%d')}")
                ])
            ], className="text-center shadow-sm"), width=4),
        ], className="mb-4")

        # Graph
        fig = px.bar(daily_counts, x='Date', y='Daily_Count', title="Daily Subscription Volume (All Types)",
                     color_discrete_sequence=['#0d6efd'])
        fig.update_layout(template="plotly_white", xaxis_title="Date", yaxis_title="Count")
        graph_section = dbc.Card(dbc.CardBody(dcc.Graph(figure=fig)), className="mb-4 shadow-sm")

        # Table
        table = dash_table.DataTable(
            data=monthly_report.to_dict('records'),
            columns=[
                {"name": "Month", "id": "Month"},
                {"name": "Total Subs", "id": "Total_Month_Subs", "type": "numeric"},

                # --- New Average Columns ---
                {"name": "Avg (All Days)", "id": "Avg_All_Days", "type": "numeric",
                 "format": Format(precision=2, scheme=Scheme.fixed)},
                {"name": "Avg (Active Days)", "id": "Avg_Active_Days", "type": "numeric",
                 "format": Format(precision=2, scheme=Scheme.fixed)},
                # ---------------------------

                {"name": "Best Day Date", "id": "Max_Sub_Date"},
                {"name": "Best Day Count", "id": "Max_Sub_Count", "type": "numeric"},

                # --- New Worst Day Columns ---
                {"name": "Worst Day Date", "id": "Min_Sub_Date"},
                {"name": "Worst Day Count", "id": "Min_Sub_Count", "type": "numeric"},
            ],
            style_cell={'padding': '10px', 'textAlign': 'left'},
            style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            sort_action="native",
            page_size=10
        )

        return html.Div([row_1, row_2, graph_section, html.H4("📅 Monthly Breakdown"), table])