from dash import html, dcc, dash_table, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from dash.dash_table.Format import Format, Scheme, Symbol

# --- LAYOUT ---
layout = html.Div([
    html.H2("📉 Cancellation Analytics", className="mb-4 text-center text-white"),
    html.Div(id="cancellation-content")
])


# --- CALLBACKS ---
def register_callbacks(app):
    @app.callback(
        Output("cancellation-content", "children"),
        Input("global-data-store", "data")
    )
    def update_cancellation_insights(data):
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
        df = df.dropna(subset=['Date', 'Subscription_Type'])

        # Normalize type
        df['type_norm'] = df['Subscription_Type'].astype(str).str.lower()

        # ==============================================================================
        # 🧮 CALCULATIONS
        # ==============================================================================

        # A. Global Stats
        total_records = len(df)
        global_min_date = df['Date'].min()
        global_max_date = df['Date'].max()
        total_days_period = (global_max_date - global_min_date).days + 1
        if total_days_period < 1: total_days_period = 1

        # B. Filter for Cancellations
        df_cancel = df[df['type_norm'] == 'cancelled'].copy()

        if df_cancel.empty:
            return dbc.Alert("Great news! No cancellations found in the dataset.", color="success")

        total_cancellations = len(df_cancel)
        cancellation_rate = (total_cancellations / total_records) * 100 if total_records > 0 else 0

        # C. Daily Aggregation
        daily_counts = df_cancel.groupby(df_cancel['Date'].dt.date).size().reset_index(name='Daily_Count')
        daily_counts.columns = ['Date', 'Daily_Count']
        daily_counts['Date'] = pd.to_datetime(daily_counts['Date'])

        # Min/Max Logic
        max_day_row = daily_counts.loc[daily_counts['Daily_Count'].idxmax()]
        min_day_row = daily_counts.loc[daily_counts['Daily_Count'].idxmin()]
        max_cancel_count = max_day_row['Daily_Count']
        min_cancel_count = min_day_row['Daily_Count']

        # D. Monthly Analysis
        daily_counts['Month'] = daily_counts['Date'].dt.to_period('M')

        def get_monthly_stats(group):
            total_month_cancel = group['Daily_Count'].sum()
            sample_date = group['Date'].iloc[0]
            days_in_month = sample_date.days_in_month
            max_idx = group['Daily_Count'].idxmax()
            min_idx = group['Daily_Count'].idxmin()

            return pd.Series({
                'Total_Month_Cancel': total_month_cancel,
                'Avg_Daily_Cancel': total_month_cancel / days_in_month,
                'Max_Cancel_Date': group.loc[max_idx, 'Date'].strftime('%Y-%m-%d'),
                'Max_Cancel_Count': group.loc[max_idx, 'Daily_Count'],
                'Min_Cancel_Date': group.loc[min_idx, 'Date'].strftime('%Y-%m-%d'),
                'Min_Cancel_Count': group.loc[min_idx, 'Daily_Count'],
            })

        monthly_report = daily_counts.groupby('Month').apply(get_monthly_stats, include_groups=False).reset_index()
        monthly_report['Month'] = monthly_report['Month'].astype(str)

        # ==============================================================================
        # UI CONSTRUCTION
        # ==============================================================================

        # 1. KPI Cards
        cards = dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Total Cancellations"),
                dbc.CardBody([
                    html.H3(f"{total_cancellations:,}", className="text-danger"),
                    html.Small(f"Out of {total_records:,} Total Records", className="text-muted")
                ])
            ], className="text-center shadow-sm"), width=3),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Churn / Cancel Rate"),
                dbc.CardBody(html.H3(f"{cancellation_rate:.2f}%", className="text-warning"))
            ], className="text-center shadow-sm"), width=3),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Max Daily Cancels"),
                dbc.CardBody([
                    html.H3(f"{max_cancel_count}", className="text-danger"),
                    html.Small(f"On {max_day_row['Date'].strftime('%Y-%m-%d')}")
                ])
            ], className="text-center shadow-sm"), width=3),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Min Daily Cancels"),
                dbc.CardBody([
                    html.H3(f"{min_cancel_count}", className="text-success"),
                    html.Small(f"On {min_day_row['Date'].strftime('%Y-%m-%d')}")
                ])
            ], className="text-center shadow-sm"), width=3),
        ], className="mb-4")

        # 2. Graph (UPDATED COLOR)
        fig = px.bar(daily_counts, x='Date', y='Daily_Count',
                     title="Cancellation Volume Over Time",
                     # ✅ CHANGED: Removed gradient, used solid color
                     # You can change '#e55039' to any Hex code (e.g., Blue: '#0d6efd')
                     color_discrete_sequence=['#e55039'])

        fig.update_layout(template="plotly_white", xaxis_title="Date", yaxis_title="Cancellations")
        graph_section = dbc.Card(dbc.CardBody(dcc.Graph(figure=fig)), className="mb-4 shadow-sm")

        # 3. Table
        table = dash_table.DataTable(
            data=monthly_report.to_dict('records'),
            columns=[
                {"name": "Month", "id": "Month"},
                {"name": "Total Cancel", "id": "Total_Month_Cancel", "type": "numeric"},
                {"name": "Avg Daily Cancel", "id": "Avg_Daily_Cancel", "type": "numeric",
                 "format": Format(precision=2, scheme=Scheme.fixed)},
                {"name": "Max Date", "id": "Max_Cancel_Date"},
                {"name": "Max Count", "id": "Max_Cancel_Count", "type": "numeric"},
                {"name": "Min Date", "id": "Min_Cancel_Date"},
                {"name": "Min Count", "id": "Min_Cancel_Count", "type": "numeric"},
            ],
            style_cell={'padding': '10px', 'textAlign': 'left'},
            style_header={'backgroundColor': '#c0392b', 'color': 'white', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            sort_action="native",
            page_size=10
        )

        return html.Div([
            cards,
            graph_section,
            html.H4("📅 Monthly Cancellation Breakdown"),
            table
        ])