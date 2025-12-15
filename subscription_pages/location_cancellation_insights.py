from dash import html, dcc, dash_table, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from dash.dash_table.Format import Format, Scheme, Symbol

# --- LAYOUT ---
layout = html.Div([
    html.H2("🌍 Location-Wise Cancellation Analytics", className="mb-4 text-center text-white"),
    html.Div(id="location-cancel-content")
])


# --- CALLBACKS ---
def register_callbacks(app):
    @app.callback(
        Output("location-cancel-content", "children"),
        Input("global-data-store", "data")
    )
    def update_location_cancel_insights(data):
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
        df['type_norm'] = df['Subscription_Type'].astype(str).str.lower()

        # ==============================================================================
        # 🧮 PRE-CALCULATIONS
        # ==============================================================================

        # 1. Global Time Period
        global_min_date = df['Date'].min()
        global_max_date = df['Date'].max()
        total_days_period = (global_max_date - global_min_date).days + 1
        if total_days_period < 1: total_days_period = 1

        # 2. Total Traffic per Location
        total_subs_by_location = df.groupby('Location').size()

        # ==============================================================================
        # 🔍 FILTER FOR CANCELLATIONS
        # ==============================================================================
        df_cancel = df[df['type_norm'] == 'cancelled'].copy()

        if df_cancel.empty:
            return dbc.Alert("Great news! No cancellations found in the dataset.", color="success")

        # Global Stats
        total_cancellations = len(df_cancel)
        unique_locations_affected = df_cancel['Location'].nunique()

        # ==============================================================================
        # 📊 LOCATION AGGREGATION
        # ==============================================================================

        # 1. Daily Counts per Location
        daily_loc_counts = df_cancel.groupby(['Location', df_cancel['Date'].dt.date]).size().reset_index(
            name='Daily_Count')
        daily_loc_counts.columns = ['Location', 'Date', 'Daily_Count']
        daily_loc_counts['Date'] = pd.to_datetime(daily_loc_counts['Date'])

        # 2. Helper to build the report
        def get_location_stats(group):
            location_name = group.name

            # Totals
            total_loc_cancel = group['Daily_Count'].sum()
            total_loc_traffic = total_subs_by_location.get(location_name, 0)

            # Metrics
            churn_rate = (total_loc_cancel / total_loc_traffic * 100) if total_loc_traffic > 0 else 0
            avg_daily_cancel = total_loc_cancel / total_days_period

            # Max (Worst Day)
            max_idx = group['Daily_Count'].idxmax()

            # ✅ Min (Best Day - Least Cancellations)
            min_idx = group['Daily_Count'].idxmin()

            return pd.Series({
                'Total_Cancel': total_loc_cancel,
                'Total_Traffic': total_loc_traffic,
                'Churn_Rate': churn_rate,
                'Avg_Daily_Cancel': avg_daily_cancel,

                # Max (Worst)
                'Worst_Day_Date': group.loc[max_idx, 'Date'].strftime('%Y-%m-%d'),
                'Worst_Day_Count': group.loc[max_idx, 'Daily_Count'],

                # ✅ NEW: Min (Best/Lowest Cancellation)
                'Best_Day_Date': group.loc[min_idx, 'Date'].strftime('%Y-%m-%d'),
                'Best_Day_Count': group.loc[min_idx, 'Daily_Count']
            })

        # Apply logic
        location_report = daily_loc_counts.groupby('Location').apply(get_location_stats,
                                                                     include_groups=False).reset_index()

        # Sort by Total Cancellations descending
        location_report = location_report.sort_values(by='Total_Cancel', ascending=False)

        # Top Location Logic
        if not location_report.empty:
            top_row = location_report.iloc[0]
            top_loc_name = top_row['Location']
            top_loc_count = top_row['Total_Cancel']
        else:
            top_loc_name = "N/A"
            top_loc_count = 0

        # ==============================================================================
        # UI CONSTRUCTION
        # ==============================================================================

        # 1. KPI Cards
        cards = dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Total Cancellations"),
                dbc.CardBody([
                    html.H3(f"{total_cancellations:,}", className="text-danger"),
                    html.Small(f"Period: {total_days_period} Days", className="text-muted")
                ])
            ], className="text-center shadow-sm"), width=3),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Locations Affected"),
                dbc.CardBody(html.H3(f"{unique_locations_affected}", className="text-warning"))
            ], className="text-center shadow-sm"), width=3),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Highest Churn Location"),
                dbc.CardBody([
                    html.H4(f"{top_loc_name}", className="text-danger"),
                    html.Small(f"{top_loc_count} Cancellations", className="text-muted")
                ])
            ], className="text-center shadow-sm"), width=3),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Avg Cancels / Loc"),
                dbc.CardBody(html.H3(f"{total_cancellations / unique_locations_affected:,.1f}", className="text-info"))
            ], className="text-center shadow-sm"), width=3),
        ], className="mb-4")

        # 2. Graph
        fig = px.bar(location_report, x='Location', y='Total_Cancel',
                     title="Cancellation Volume by Location",
                     color='Total_Cancel',
                     color_continuous_scale='Reds')

        fig.update_layout(template="plotly_white", xaxis_title="Location", yaxis_title="Cancellations")
        graph_section = dbc.Card(dbc.CardBody(dcc.Graph(figure=fig)), className="mb-4 shadow-sm")

        # 3. Table
        table = dash_table.DataTable(
            data=location_report.to_dict('records'),
            columns=[
                {"name": "Location", "id": "Location"},
                {"name": "Total Cancel", "id": "Total_Cancel", "type": "numeric"},
                {"name": "Avg Daily Cancel", "id": "Avg_Daily_Cancel", "type": "numeric",
                 "format": Format(precision=2, scheme=Scheme.fixed)},
                {"name": "Total Traffic", "id": "Total_Traffic", "type": "numeric"},
                {"name": "Churn Rate (%)", "id": "Churn_Rate", "type": "numeric",
                 "format": Format(precision=2, scheme=Scheme.fixed, symbol=Symbol.yes, symbol_suffix="%")},

                # Worst Day (Max Cancellations)
                {"name": "Max Cancel Date", "id": "Worst_Day_Date"},
                {"name": "Max Cancel Count", "id": "Worst_Day_Count", "type": "numeric"},

                # ✅ NEW: Best Day (Min Cancellations)
                {"name": "Min Cancel Date", "id": "Best_Day_Date"},
                {"name": "Min Cancel Count", "id": "Best_Day_Count", "type": "numeric"},
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
            html.H4("📍 Detailed Location Breakdown"),
            table
        ])