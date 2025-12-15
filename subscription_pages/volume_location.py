from dash import html, dcc, dash_table, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from dash.dash_table.Format import Format, Scheme

# --- LAYOUT ---
layout = html.Div([
    html.H2("🌍 Location-Wise Subscription Volume", className="mb-4 text-center text-white"),
    html.Div(id="volume-location-content")
])


# --- CALLBACKS ---
def register_callbacks(app):
    @app.callback(
        Output("volume-location-content", "children"),
        Input("global-data-store", "data")
    )
    def update_volume_location(data):
        if not data:
            return dbc.Alert("No data available.", color="warning")

        df = pd.DataFrame(data)

        # 1. Check Required Columns
        required_cols = ['Date', 'Location', 'Subscription_Type']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            return dbc.Alert(f"Data missing required columns: {missing_cols}", color="danger")

        # 2. Data Cleaning
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce', utc=True)
        df = df.dropna(subset=['Date', 'Location', 'Subscription_Type'])

        df_clean = df.copy()
        # Normalize type for counting
        df_clean['type_norm'] = df_clean['Subscription_Type'].astype(str).str.lower()

        if df_clean.empty:
            return dbc.Alert("No data found after cleaning.", color="warning")

        # ==============================================================================
        # 🧮 CALCULATIONS
        # ==============================================================================

        # 1. Global Time Period Calculation (e.g., 200 Days)
        global_min_date = df_clean['Date'].min()
        global_max_date = df_clean['Date'].max()
        total_days_period = (global_max_date - global_min_date).days + 1
        if total_days_period < 1: total_days_period = 1

        # 2. Global KPIs
        total_subs = len(df_clean)
        count_cancelled = len(df_clean[df_clean['type_norm'] == 'cancelled'])
        count_trial = len(df_clean[df_clean['type_norm'] == 'trial'])
        paid_types = ['new', 'renewed', 'upgraded']
        count_paid = len(df_clean[df_clean['type_norm'].isin(paid_types)])

        # 3. Location Aggregation
        # Group by Location AND Date to find daily counts per location
        daily_loc_counts = df_clean.groupby(['Location', df_clean['Date'].dt.date]).size().reset_index(
            name='Daily_Count')
        daily_loc_counts.columns = ['Location', 'Date', 'Daily_Count']

        # 4. Location Details Helper
        def get_location_details(group):
            # Total Subs for this location
            total_loc_subs = group['Daily_Count'].sum()

            # Active Days (rows in this group)
            active_days_count = len(group)

            # --- Averages ---
            # 1. Avg per Calendar Day (e.g. 500 / 200)
            avg_all_days = total_loc_subs / total_days_period

            # 2. Avg per Active Day (e.g. 500 / 10)
            avg_active_days = total_loc_subs / active_days_count if active_days_count > 0 else 0

            # Min/Max Logic
            max_day_idx = group['Daily_Count'].idxmax()
            min_day_idx = group['Daily_Count'].idxmin()

            return pd.Series({
                'Total_Location_Subs': total_loc_subs,

                # The Two Averages
                'Avg_All_Days': avg_all_days,
                'Avg_Active_Days': avg_active_days,

                # Best Day
                'Best_Day_Date': group.loc[max_day_idx, 'Date'],
                'Best_Day_Count': group.loc[max_day_idx, 'Daily_Count'],

                # Worst Day
                'Worst_Day_Date': group.loc[min_day_idx, 'Date'],
                'Worst_Day_Count': group.loc[min_day_idx, 'Daily_Count']
            })

        location_report = daily_loc_counts.groupby('Location').apply(get_location_details,
                                                                     include_groups=False).reset_index()

        # Identify Top Location
        if not location_report.empty:
            top_loc_row = location_report.loc[location_report['Total_Location_Subs'].idxmax()]
            top_loc_name = top_loc_row['Location']
            top_loc_val = top_loc_row['Total_Location_Subs']
        else:
            top_loc_name = "N/A"
            top_loc_val = 0

        # ==============================================================================
        # UI CONSTRUCTION (KPI CARDS)
        # ==============================================================================

        cards = dbc.Row([
            # 1. Total
            dbc.Col(dbc.Card([
                dbc.CardHeader("Total Subs"),
                dbc.CardBody([
                    html.H4(f"{total_subs:,}", className="text-dark"),
                    html.Small(f"Period: {total_days_period} Days", className="text-muted")
                ])
            ], className="text-center shadow-sm"), width=2),

            # 2. Paid (New/Renew/Upgrade)
            dbc.Col(dbc.Card([
                dbc.CardHeader("Paid Subs"),
                dbc.CardBody(html.H4(f"{count_paid:,}", className="text-success"))
            ], className="text-center shadow-sm"), width=2),

            # 3. Trial
            dbc.Col(dbc.Card([
                dbc.CardHeader("Trial"),
                dbc.CardBody(html.H4(f"{count_trial:,}", className="text-info"))
            ], className="text-center shadow-sm"), width=2),

            # 4. Cancelled
            dbc.Col(dbc.Card([
                dbc.CardHeader("Cancelled"),
                dbc.CardBody(html.H4(f"{count_cancelled:,}", className="text-danger"))
            ], className="text-center shadow-sm"), width=2),

            # 5. Top Location
            dbc.Col(dbc.Card([
                dbc.CardHeader("Top Location"),
                dbc.CardBody(html.H4(f"{top_loc_name}", className="text-primary", style={"fontSize": "1.1rem"}))
            ], className="text-center shadow-sm"), width=2),

            # 6. Active Locations
            dbc.Col(dbc.Card([
                dbc.CardHeader("Locations"),
                dbc.CardBody(html.H4(f"{len(location_report)}", className="text-secondary"))
            ], className="text-center shadow-sm"), width=2),
        ], className="mb-4 g-2")

        # Graph
        location_report_sorted = location_report.sort_values(by='Total_Location_Subs', ascending=False)
        fig = px.bar(location_report_sorted, x='Location', y='Total_Location_Subs',
                     title="Total Subscriptions by Location",
                     color='Total_Location_Subs',
                     color_continuous_scale='Viridis')
        fig.update_layout(template="plotly_white", xaxis_title="Location", yaxis_title="Count")
        graph_section = dbc.Card(dbc.CardBody(dcc.Graph(figure=fig)), className="mb-4 shadow-sm")

        # Table
        table = dash_table.DataTable(
            data=location_report.to_dict('records'),
            columns=[
                {"name": "Location", "id": "Location"},
                {"name": "Total Subs", "id": "Total_Location_Subs", "type": "numeric"},

                # --- New Average Columns ---
                {"name": "Avg (All Days)", "id": "Avg_All_Days", "type": "numeric",
                 "format": Format(precision=2, scheme=Scheme.fixed)},

                {"name": "Avg (Active Days)", "id": "Avg_Active_Days", "type": "numeric",
                 "format": Format(precision=2, scheme=Scheme.fixed)},
                # ---------------------------

                {"name": "Best Day Date", "id": "Best_Day_Date"},
                {"name": "Best Day Count", "id": "Best_Day_Count", "type": "numeric"},

                # --- New Worst Day Columns ---
                {"name": "Worst Day Date", "id": "Worst_Day_Date"},
                {"name": "Worst Day Count", "id": "Worst_Day_Count", "type": "numeric"},
            ],
            style_cell={'padding': '10px', 'textAlign': 'left'},
            style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            sort_action="native",
            page_size=10
        )

        return html.Div([cards, graph_section, html.H4("📍 Detailed Location Breakdown"), table])