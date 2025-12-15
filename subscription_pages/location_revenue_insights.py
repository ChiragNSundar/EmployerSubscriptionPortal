from dash import html, dcc, dash_table, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from dash.dash_table.Format import Format, Scheme, Symbol

# --- LAYOUT ---
layout = html.Div([
    html.H2("🌍 Location-Wise Revenue Insights", className="mb-4 text-center text-white"),
    html.Div(id="location-insights-content")
])


# --- CALLBACKS ---
def register_callbacks(app):
    @app.callback(
        Output("location-insights-content", "children"),
        Input("global-data-store", "data")
    )
    def update_location_insights(data):
        if not data:
            return dbc.Alert("No data available.", color="warning")

        df = pd.DataFrame(data)

        # 1. Check Columns
        required_cols = ['lastPaymentReceivedOn', 'lastAmountPaidEUR', 'Date', 'Location', 'Subscription_Type']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            return dbc.Alert(f"Data missing required columns: {missing_cols}", color="danger")

        # 2. Data Prep
        df['lastPaymentReceivedOn'] = pd.to_datetime(df['lastPaymentReceivedOn'], errors='coerce', utc=True)
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce', utc=True)
        df['lastAmountPaidEUR'] = pd.to_numeric(df['lastAmountPaidEUR'], errors='coerce')

        # Drop rows with missing essential data
        df = df.dropna(subset=['lastPaymentReceivedOn', 'Date', 'lastAmountPaidEUR', 'Location', 'Subscription_Type'])

        # ==============================================================================
        # ✅ APPLIED FILTERS
        # ==============================================================================

        # 3. Filter by Subscription Type
        valid_types = ['new', 'renewed', 'upgraded']
        df['type_norm'] = df['Subscription_Type'].astype(str).str.lower()
        df = df[df['type_norm'].isin(valid_types)]

        # 4. Filter Condition: Payment Date >= Creation Date
        df_clean = df[df['lastPaymentReceivedOn'] >= df['Date']].copy()

        if df_clean.empty:
            return dbc.Alert("No data found after applying filters (Type & Date).", color="warning")

        # ==============================================================================
        # 🧮 CALCULATIONS
        # ==============================================================================

        # 1. Global Time Period (e.g. 200 Days)
        global_min_date = df_clean['lastPaymentReceivedOn'].min()
        global_max_date = df_clean['lastPaymentReceivedOn'].max()
        total_days_period = (global_max_date - global_min_date).days + 1
        if total_days_period < 1: total_days_period = 1

        # 2. Daily Aggregation per Location
        daily_location_sums = df_clean.groupby(['Location', df_clean['lastPaymentReceivedOn'].dt.date])[
            'lastAmountPaidEUR'].sum().reset_index()
        daily_location_sums.columns = ['Location', 'Date', 'Daily_Revenue']

        # 3. Location Details Helper
        def get_location_details(group):
            # Calculate Totals
            total_revenue = group['Daily_Revenue'].sum()

            # --- Active Day Count (Days with > 0 Revenue) ---
            # Since 'group' is built from transaction logs, rows usually imply activity.
            # We enforce > 0 to be safe.
            active_days_df = group[group['Daily_Revenue'] > 0]
            active_days_count = len(active_days_df)

            # Metric 1: Avg per Active Day (e.g. 500 / 10)
            avg_active = total_revenue / active_days_count if active_days_count > 0 else 0

            # Metric 2: Avg per Calendar Day (e.g. 500 / 200)
            avg_overall = total_revenue / total_days_period

            # Min/Max Logic
            max_day_idx = group['Daily_Revenue'].idxmax()
            min_day_idx = group['Daily_Revenue'].idxmin()

            return pd.Series({
                'Total_Location_Revenue': total_revenue,

                # The Two Averages
                'Avg_Daily_Revenue': avg_overall,  # 500 / 200
                'Avg_Active_Day_Revenue': avg_active,  # 500 / 10

                # Dates & Amounts
                'Max_Rev_Date': group.loc[max_day_idx, 'Date'],
                'Max_Rev_Amt': group.loc[max_day_idx, 'Daily_Revenue'],
                'Min_Rev_Date': group.loc[min_day_idx, 'Date'],
                'Min_Rev_Amt': group.loc[min_day_idx, 'Daily_Revenue'],
            })

        location_report = daily_location_sums.groupby('Location').apply(get_location_details,
                                                                        include_groups=False).reset_index()

        # Global Stats
        total_rev_overall = df_clean['lastAmountPaidEUR'].sum()

        # Determine Top Location
        if not location_report.empty:
            top_loc_row = location_report.loc[location_report['Total_Location_Revenue'].idxmax()]
            top_loc_name = top_loc_row['Location']
            top_loc_val = top_loc_row['Total_Location_Revenue']
        else:
            top_loc_name = "N/A"
            top_loc_val = 0

        # ==============================================================================
        # UI COMPONENTS
        # ==============================================================================

        cards = dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Total Revenue"),
                dbc.CardBody([
                    html.H3(f"€{total_rev_overall:,.2f}", className="text-success"),
                    html.Small(f"Period: {total_days_period} Days", className="text-muted")
                ])
            ], className="text-center shadow-sm"), width=4),
            dbc.Col(dbc.Card([
                dbc.CardHeader("🏆 Top Location"),
                dbc.CardBody([
                    html.H4(f"{top_loc_name}", className="text-primary"),
                    html.Small(f"€{top_loc_val:,.2f}")
                ])
            ], className="text-center shadow-sm"), width=4),
            dbc.Col(dbc.Card([
                dbc.CardHeader("Active Locations"),
                dbc.CardBody(html.H3(f"{len(location_report)}", className="text-info"))
            ], className="text-center shadow-sm"), width=4),
        ], className="mb-4")

        # Graph
        location_report_sorted = location_report.sort_values(by='Total_Location_Revenue', ascending=False)
        fig = px.bar(location_report_sorted, x='Location', y='Total_Location_Revenue', title="Revenue by Location",
                     color='Total_Location_Revenue', color_continuous_scale='Viridis')
        fig.update_layout(template="plotly_white", xaxis_title="Location", yaxis_title="Revenue (€)")

        # Table
        table = dash_table.DataTable(
            data=location_report.to_dict('records'),
            columns=[
                {"name": "Location", "id": "Location"},
                {"name": "Total Rev (€)", "id": "Total_Location_Revenue", "type": "numeric",
                 "format": Format(symbol=Symbol.yes, symbol_prefix="€", scheme=Scheme.fixed, precision=2)},

                # --- The Two Average Columns ---
                {"name": "Avg (All Days)", "id": "Avg_Daily_Revenue", "type": "numeric",
                 "format": Format(symbol=Symbol.yes, symbol_prefix="€", scheme=Scheme.fixed, precision=2)},

                {"name": "Avg (Active Days)", "id": "Avg_Active_Day_Revenue", "type": "numeric",
                 "format": Format(symbol=Symbol.yes, symbol_prefix="€", scheme=Scheme.fixed, precision=2)},
                # -------------------------------

                {"name": "Best Day Date", "id": "Max_Rev_Date"},
                {"name": "Best Day Amt (€)", "id": "Max_Rev_Amt", "type": "numeric",
                 "format": Format(symbol=Symbol.yes, symbol_prefix="€", scheme=Scheme.fixed, precision=2)},

                {"name": "Worst Day Date", "id": "Min_Rev_Date"},
                {"name": "Worst Day Amt (€)", "id": "Min_Rev_Amt", "type": "numeric",
                 "format": Format(symbol=Symbol.yes, symbol_prefix="€", scheme=Scheme.fixed, precision=2)},
            ],
            style_cell={'padding': '10px', 'textAlign': 'left'},
            style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            sort_action="native",
            page_size=10
        )

        return html.Div(
            [cards, dbc.Card(dbc.CardBody(dcc.Graph(figure=fig)), className="mb-4"), html.H4("📍 Detailed Breakdown"),
             table])