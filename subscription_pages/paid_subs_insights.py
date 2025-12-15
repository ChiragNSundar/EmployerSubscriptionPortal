from dash import html, dcc, dash_table, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from dash.dash_table.Format import Format, Scheme, Symbol

# --- LAYOUT ---
layout = html.Div([
    html.H2("💸 Paid Subscription Analytics", className="mb-4 text-center text-white"),
    html.Div(id="paid-subs-content")
])


# --- CALLBACKS ---
def register_callbacks(app):
    @app.callback(
        Output("paid-subs-content", "children"),
        Input("global-data-store", "data")
    )
    def update_paid_subs_insights(data):
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

        # A. Global Stats (All records)
        total_records = len(df)

        # B. Filter for PAID Types (New, Renewed, Upgraded)
        paid_types = ['new', 'renewed', 'upgraded']
        df_paid = df[df['type_norm'].isin(paid_types)].copy()

        if df_paid.empty:
            return dbc.Alert("No paid subscriptions found in the dataset.", color="warning")

        total_paid_subs = len(df_paid)

        # Paid Conversion Rate (Paid Subs / Total Records)
        # This tells you what % of total traffic is actually paying vs trials/cancels
        paid_rate = (total_paid_subs / total_records) * 100 if total_records > 0 else 0

        # C. Daily Aggregation
        daily_counts = df_paid.groupby(df_paid['Date'].dt.date).size().reset_index(name='Daily_Count')
        daily_counts.columns = ['Date', 'Daily_Count']
        daily_counts['Date'] = pd.to_datetime(daily_counts['Date'])

        # Min/Max Logic (Best and Worst Performing Active Days)
        max_day_row = daily_counts.loc[daily_counts['Daily_Count'].idxmax()]
        min_day_row = daily_counts.loc[daily_counts['Daily_Count'].idxmin()]

        max_paid_count = max_day_row['Daily_Count']
        min_paid_count = min_day_row['Daily_Count']

        # D. Monthly Analysis
        daily_counts['Month'] = daily_counts['Date'].dt.to_period('M')

        def get_monthly_stats(group):
            total_month_paid = group['Daily_Count'].sum()

            # Calendar Average Logic
            sample_date = group['Date'].iloc[0]
            days_in_month = sample_date.days_in_month

            max_idx = group['Daily_Count'].idxmax()
            min_idx = group['Daily_Count'].idxmin()

            return pd.Series({
                'Total_Month_Paid': total_month_paid,
                'Avg_Daily_Paid': total_month_paid / days_in_month,  # Spread over calendar days
                'Max_Paid_Date': group.loc[max_idx, 'Date'].strftime('%Y-%m-%d'),
                'Max_Paid_Count': group.loc[max_idx, 'Daily_Count'],
                'Min_Paid_Date': group.loc[min_idx, 'Date'].strftime('%Y-%m-%d'),
                'Min_Paid_Count': group.loc[min_idx, 'Daily_Count'],
            })

        monthly_report = daily_counts.groupby('Month').apply(get_monthly_stats, include_groups=False).reset_index()
        monthly_report['Month'] = monthly_report['Month'].astype(str)

        # ==============================================================================
        # UI CONSTRUCTION
        # ==============================================================================

        # 1. KPI Cards
        cards = dbc.Row([
            # Total Paid
            dbc.Col(dbc.Card([
                dbc.CardHeader("Total Paid Subs"),
                dbc.CardBody([
                    html.H3(f"{total_paid_subs:,}", className="text-success"),
                    html.Small(f"New + Renewed + Upgraded", className="text-muted")
                ])
            ], className="text-center shadow-sm"), width=3),

            # Conversion Rate
            dbc.Col(dbc.Card([
                dbc.CardHeader("Paid Ratio"),
                dbc.CardBody([
                    html.H3(f"{paid_rate:.2f}%", className="text-info"),
                    html.Small("of Total Volume", className="text-muted")
                ])
            ], className="text-center shadow-sm"), width=3),

            # Best Day
            dbc.Col(dbc.Card([
                dbc.CardHeader("Best Day Volume"),
                dbc.CardBody([
                    html.H3(f"{max_paid_count}", className="text-success"),
                    html.Small(f"On {max_day_row['Date'].strftime('%Y-%m-%d')}")
                ])
            ], className="text-center shadow-sm"), width=3),

            # Worst Day (that wasn't zero)
            dbc.Col(dbc.Card([
                dbc.CardHeader("Lowest Active Day"),
                dbc.CardBody([
                    html.H3(f"{min_paid_count}", className="text-warning"),
                    html.Small(f"On {min_day_row['Date'].strftime('%Y-%m-%d')}")
                ])
            ], className="text-center shadow-sm"), width=3),
        ], className="mb-4")

        # 2. Graph (GREEN Theme)
        fig = px.bar(daily_counts, x='Date', y='Daily_Count',
                     title="Paid Subscription Volume Over Time",
                     # Green Color for Positive Growth
                     color_discrete_sequence=['#2ecc71'])

        fig.update_layout(template="plotly_white", xaxis_title="Date", yaxis_title="Paid Subscriptions")
        graph_section = dbc.Card(dbc.CardBody(dcc.Graph(figure=fig)), className="mb-4 shadow-sm")

        # 3. Table
        table = dash_table.DataTable(
            data=monthly_report.to_dict('records'),
            columns=[
                {"name": "Month", "id": "Month"},
                {"name": "Total Paid", "id": "Total_Month_Paid", "type": "numeric"},

                {"name": "Avg Daily Paid", "id": "Avg_Daily_Paid", "type": "numeric",
                 "format": Format(precision=2, scheme=Scheme.fixed)},

                {"name": "Max Date", "id": "Max_Paid_Date"},
                {"name": "Max Count", "id": "Max_Paid_Count", "type": "numeric"},

                {"name": "Min Date", "id": "Min_Paid_Date"},
                {"name": "Min Count", "id": "Min_Paid_Count", "type": "numeric"},
            ],
            style_cell={'padding': '10px', 'textAlign': 'left'},
            # Green Header
            style_header={'backgroundColor': '#27ae60', 'color': 'white', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            sort_action="native",
            page_size=10
        )

        return html.Div([
            cards,
            graph_section,
            html.H4("📅 Monthly Paid Volume Breakdown"),
            table
        ])