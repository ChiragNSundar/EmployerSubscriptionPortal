from dash import html, dcc, dash_table, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import traceback

# --- LAYOUT ---
layout = html.Div([
    html.H2("⏱️ Time to First Subscription", className="mb-4 text-center text-white"),
    html.Div(id="first-sub-content")
])


# --- LOGIC & CALLBACKS ---
def register_callbacks(app):
    @app.callback(
        Output("first-sub-content", "children"),
        Input("global-data-store", "data")
    )
    def update_first_sub_page(data):
        if not data:
            return dbc.Alert("Global Data Store is empty.", color="warning")

        try:
            # 1. Load Data
            df = pd.DataFrame(data)

            # 2. Check Columns
            required_cols = ['customerCreatedTimeUTC', 'initialSubsStartDate', 'User_ID', 'Company']
            type_col = 'Type' if 'Type' in df.columns else None

            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                return dbc.Alert(f"Data missing required columns: {missing_cols}", color="danger")

            # 3. Date Conversion
            df['customerCreatedTimeUTC'] = pd.to_datetime(df['customerCreatedTimeUTC'], errors='coerce', utc=True)
            df['initialSubsStartDate'] = pd.to_datetime(df['initialSubsStartDate'], errors='coerce', utc=True)

            # ==============================================================================
            # 🧹 DATA CLEANING & LOGIC (Earliest Subscription)
            # ==============================================================================

            df_subs = df.dropna(subset=['initialSubsStartDate']).copy()
            df_subs = df_subs.sort_values(by='initialSubsStartDate', ascending=True)
            first_subs = df_subs.drop_duplicates(subset=['User_ID'], keep='first').copy()

            # Calculate Time Difference (Days)
            first_subs['Days_to_First_Sub'] = (first_subs['initialSubsStartDate'] - first_subs[
                'customerCreatedTimeUTC']).dt.total_seconds() / 86400

            # Clean negative values
            first_subs['Days_to_First_Sub'] = first_subs['Days_to_First_Sub'].apply(lambda x: x if x >= 0 else 0)

            # ==============================================================================
            # 🧮 STATISTICS & FORMATTING
            # ==============================================================================

            total_subscribers = len(first_subs)

            if total_subscribers > 0:
                mean_time = first_subs['Days_to_First_Sub'].mean()
                median_time = first_subs['Days_to_First_Sub'].median()
                min_time = first_subs['Days_to_First_Sub'].min()
                max_time = first_subs['Days_to_First_Sub'].max()
            else:
                mean_time = median_time = min_time = max_time = 0

            # --- NEW HELPER FUNCTION FOR TIME FORMATTING ---
            def format_duration(days):
                """
                If days >= 1, returns 'X.XX Days'.
                If days < 1, returns 'Xh Ym Zs'.
                """
                if days >= 1:
                    return f"{days:.2f} Days"
                else:
                    # Convert fraction of day to total seconds
                    total_seconds = int(days * 86400)

                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60

                    # Build string dynamically to avoid "0h 0m 5s" looking cluttered
                    parts = []
                    if hours > 0:
                        parts.append(f"{hours}h")
                    if minutes > 0:
                        parts.append(f"{minutes}m")
                    parts.append(f"{seconds}s")

                    return " ".join(parts) if parts else "0s"

            # ==============================================================================
            # 📈 GRAPH
            # ==============================================================================

            fig_dist = px.histogram(
                first_subs,
                x='Days_to_First_Sub',
                nbins=40,
                title="📊 Distribution: How long after Account Creation do users Subscribe?",
                labels={'Days_to_First_Sub': 'Days from Creation to First Sub'},
                color_discrete_sequence=['#e67e22']
            )

            fig_dist.update_layout(
                template="plotly_white",
                yaxis_title="Count of Users",
                xaxis_title="Days Taken",
                bargap=0.1
            )

            # ==============================================================================
            # 🖥️ UI COMPONENTS
            # ==============================================================================

            def create_kpi_card(title, value, sub_text, color_class):
                return dbc.Col(dbc.Card([
                    dbc.CardHeader(title),
                    dbc.CardBody([
                        html.H3(value, className=color_class),
                        html.Small(sub_text, className="text-muted")
                    ])
                ], className="text-center shadow-sm h-100"), width=True)

            # 1. KPI Cards Row (Using the new format_duration function)
            cards = dbc.Row([
                create_kpi_card("Total First Subs", f"{total_subscribers}", "Unique Users", "text-primary"),
                create_kpi_card("Mean Time", format_duration(mean_time), "Average wait", "text-info"),
                create_kpi_card("Median Time", format_duration(median_time), "Middle value", "text-warning"),
                create_kpi_card("Fastest Sub", format_duration(min_time), "Lowest Time", "text-success"),
                create_kpi_card("Slowest Sub", format_duration(max_time), "Highest Time", "text-danger"),
            ], className="mb-4")

            # 2. Detailed Table
            display_cols = ['User_ID', 'Company', 'customerCreatedTimeUTC', 'initialSubsStartDate', 'Days_to_First_Sub']
            if type_col:
                display_cols.insert(4, type_col)

            table_data = first_subs[display_cols].sort_values(by='Days_to_First_Sub', ascending=True).head(100)

            dt_columns = [
                {"name": "User ID", "id": "User_ID"},
                {"name": "Company", "id": "Company"},
                {"name": "Account Created", "id": "customerCreatedTimeUTC", "type": "datetime"},
                {"name": "First Sub Date", "id": "initialSubsStartDate", "type": "datetime"},
                {"name": "Days Taken", "id": "Days_to_First_Sub", "type": "numeric", "format": {"specifier": ".2f"}},
            ]
            if type_col:
                dt_columns.insert(4, {"name": "Sub Type", "id": type_col})

            table_section = dash_table.DataTable(
                data=table_data.to_dict('records'),
                columns=dt_columns,
                style_cell={'padding': '10px', 'textAlign': 'left'},
                style_header={'backgroundColor': '#d35400', 'color': 'white', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(253, 242, 233)'}],
                page_size=10,
                sort_action="native",
                filter_action="native"
            )

            return html.Div([
                cards,
                dbc.Row([
                    dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(figure=fig_dist)), className="shadow-sm mb-4"), width=12)
                ]),
                html.H4("📋 Fastest Conversions (Top 100)", className="mb-3 text-white"),
                table_section
            ])

        except Exception as e:
            return dbc.Alert([html.H4("Error processing data"), html.Pre(traceback.format_exc())], color="danger")