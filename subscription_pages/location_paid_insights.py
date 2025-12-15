from dash import html, dcc, dash_table, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from dash.dash_table.Format import Format, Scheme, Symbol

# --- LAYOUT ---
layout = html.Div([
    html.H2("🌍 Location-Wise Paid Subscription Analytics", className="mb-4 text-center text-white"),
    html.Div(id="location-paid-content")
])


# --- CALLBACKS ---
def register_callbacks(app):
    @app.callback(
        Output("location-paid-content", "children"),
        Input("global-data-store", "data")
    )
    def update_location_paid_insights(data):
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

        # 1. Global Time Period (The Denominator for "Average Daily")
        global_min_date = df['Date'].min()
        global_max_date = df['Date'].max()
        total_days_period = (global_max_date - global_min_date).days + 1
        if total_days_period < 1: total_days_period = 1

        # 2. Total Traffic per Location (For Conversion Rate)
        # We calculate this BEFORE filtering for paid types to see the full picture.
        total_subs_by_location = df.groupby('Location').size()

        # ==============================================================================
        # 🔍 FILTER FOR PAID SUBSCRIPTIONS
        # ==============================================================================
        paid_types = ['new', 'renewed', 'upgraded']
        df_paid = df[df['type_norm'].isin(paid_types)].copy()

        if df_paid.empty:
            return dbc.Alert("No paid subscriptions (New/Renewed/Upgraded) found.", color="warning")

        # Global Stats
        total_paid = len(df_paid)
        unique_locations_active = df_paid['Location'].nunique()

        # ==============================================================================
        # 📊 LOCATION AGGREGATION
        # ==============================================================================

        # 1. Daily Counts per Location
        daily_loc_counts = df_paid.groupby(['Location', df_paid['Date'].dt.date]).size().reset_index(
            name='Daily_Count')
        daily_loc_counts.columns = ['Location', 'Date', 'Daily_Count']
        daily_loc_counts['Date'] = pd.to_datetime(daily_loc_counts['Date'])

        # 2. Helper to build the report
        def get_location_stats(group):
            location_name = group.name

            # Total Paid for this location
            total_loc_paid = group['Daily_Count'].sum()

            # Get Total Traffic (All Types) for this location
            total_loc_traffic = total_subs_by_location.get(location_name, 0)

            # Metrics
            # Paid Conversion Rate: What % of total traffic became paid?
            paid_rate = (total_loc_paid / total_loc_traffic * 100) if total_loc_traffic > 0 else 0

            # Avg Daily Paid: Spread over the global timeline
            avg_daily_paid = total_loc_paid / total_days_period

            # Max (Best Day)
            max_idx = group['Daily_Count'].idxmax()

            # Min (Worst Active Day)
            min_idx = group['Daily_Count'].idxmin()

            return pd.Series({
                'Total_Paid': total_loc_paid,
                'Total_Traffic': total_loc_traffic,
                'Paid_Rate': paid_rate,
                'Avg_Daily_Paid': avg_daily_paid,

                # Best Day
                'Best_Day_Date': group.loc[max_idx, 'Date'].strftime('%Y-%m-%d'),
                'Best_Day_Count': group.loc[max_idx, 'Daily_Count'],

                # Worst Day
                'Worst_Day_Date': group.loc[min_idx, 'Date'].strftime('%Y-%m-%d'),
                'Worst_Day_Count': group.loc[min_idx, 'Daily_Count']
            })

        # Apply logic
        location_report = daily_loc_counts.groupby('Location').apply(get_location_stats,
                                                                     include_groups=False).reset_index()

        # Sort by Total Paid descending
        location_report = location_report.sort_values(by='Total_Paid', ascending=False)

        # Top Location Logic
        if not location_report.empty:
            top_row = location_report.iloc[0]
            top_loc_name = top_row['Location']
            top_loc_count = top_row['Total_Paid']
        else:
            top_loc_name = "N/A"
            top_loc_count = 0

        # ==============================================================================
        # UI CONSTRUCTION
        # ==============================================================================

        # 1. KPI Cards
        cards = dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Total Paid Subs"),
                dbc.CardBody([
                    html.H3(f"{total_paid:,}", className="text-success"),
                    html.Small(f"Period: {total_days_period} Days", className="text-muted")
                ])
            ], className="text-center shadow-sm"), width=3),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Active Location"),
                dbc.CardBody(html.H3(f"{unique_locations_active}", className="text-info"))
            ], className="text-center shadow-sm"), width=3),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Top Location"),
                dbc.CardBody([
                    html.H4(f"{top_loc_name}", className="text-success"),
                    html.Small(f"{top_loc_count} Paid Subs", className="text-muted")
                ])
            ], className="text-center shadow-sm"), width=3),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Avg Paid / Loc"),
                dbc.CardBody(html.H3(f"{total_paid / unique_locations_active:,.1f}", className="text-secondary"))
            ], className="text-center shadow-sm"), width=3),
        ], className="mb-4")

        # 2. Graph (Green Theme)
        fig = px.bar(location_report, x='Location', y='Total_Paid',
                     title="Paid Subscription Volume by Location",
                     color='Total_Paid',
                     color_continuous_scale='Greens')  # Green gradient

        fig.update_layout(template="plotly_white", xaxis_title="Location", yaxis_title="Paid Subscriptions")
        graph_section = dbc.Card(dbc.CardBody(dcc.Graph(figure=fig)), className="mb-4 shadow-sm")

        # 3. Table
        table = dash_table.DataTable(
            data=location_report.to_dict('records'),
            columns=[
                {"name": "Location", "id": "Location"},
                {"name": "Total Paid", "id": "Total_Paid", "type": "numeric"},

                {"name": "Avg Daily Paid", "id": "Avg_Daily_Paid", "type": "numeric",
                 "format": Format(precision=2, scheme=Scheme.fixed)},

                {"name": "Total Traffic", "id": "Total_Traffic", "type": "numeric"},

                {"name": "Paid Rate (%)", "id": "Paid_Rate", "type": "numeric",
                 "format": Format(precision=2, scheme=Scheme.fixed, symbol=Symbol.yes, symbol_suffix="%")},

                {"name": "Best Day Date", "id": "Best_Day_Date"},
                {"name": "Best Day Count", "id": "Best_Day_Count", "type": "numeric"},

                {"name": "Min Day Date", "id": "Worst_Day_Date"},
                {"name": "Min Day Count", "id": "Worst_Day_Count", "type": "numeric"},
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
            html.H4("📍 Detailed Location Breakdown"),
            table
        ])