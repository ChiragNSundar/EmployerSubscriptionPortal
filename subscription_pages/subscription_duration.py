from dash import html, dcc, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import traceback
from datetime import datetime, timezone

# --- LAYOUT ---
layout = html.Div([
    html.H2("⏳ Subscription Duration Analysis", className="mb-4 text-center text-white"),

    # --- FILTER SECTION (Compact & Centered) ---
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col(html.Label("📅 Duration Range (Days):", className="fw-bold mt-1"), width="auto"),

                # Min Input
                dbc.Col([
                    dbc.InputGroup([
                        dbc.InputGroupText("Min"),
                        dbc.Input(id="min-duration", type="number", value=0, min=0, debounce=True)
                    ])
                ], width=3),

                # Max Input
                dbc.Col([
                    dbc.InputGroup([
                        dbc.InputGroupText("Max"),
                        dbc.Input(id="max-duration", type="number", value=2000, min=0, debounce=True)
                    ])
                ], width=3),

                dbc.Col(html.Small("Type values and press Enter", className="text-muted mt-2"), width="auto")
            ], align="center", justify="center")
        ])
    ], className="mb-4 shadow-sm mx-auto w-75"),  # w-75 makes it 75% width, mx-auto centers it

    # --- CONTENT SECTION ---
    html.Div(id="duration-content")
])


# --- LOGIC & CALLBACKS ---
def register_callbacks(app):
    @app.callback(
        Output("duration-content", "children"),
        [Input("global-data-store", "data"),
         Input("min-duration", "value"),
         Input("max-duration", "value")]
    )
    def update_duration_page(data, min_days, max_days):
        if not data:
            return dbc.Alert("Global Data Store is empty.", color="warning")

        try:
            # 1. Load Data
            df = pd.DataFrame(data)

            # 2. Check Columns
            required_cols = ['initialSubsStartDate', 'subscriptionCanceledAt', 'User_ID', 'Company']
            missing_cols = [col for col in required_cols if col not in df.columns]

            if 'initialSubsStartDate' not in df.columns:
                return dbc.Alert(f"Data missing required columns: {missing_cols}", color="danger")

            # 3. Date Conversion
            df['initialSubsStartDate'] = pd.to_datetime(df['initialSubsStartDate'], errors='coerce', utc=True)
            if 'subscriptionCanceledAt' in df.columns:
                df['subscriptionCanceledAt'] = pd.to_datetime(df['subscriptionCanceledAt'], errors='coerce', utc=True)
            else:
                df['subscriptionCanceledAt'] = pd.NaT

            # ==============================================================================
            # 🧹 DATA CLEANING & DURATION CALCULATION
            # ==============================================================================

            df_dur = df.dropna(subset=['initialSubsStartDate']).copy()
            df_dur = df_dur.sort_values(by='initialSubsStartDate', ascending=False)
            df_dur = df_dur.drop_duplicates(subset=['User_ID'], keep='first').copy()

            now_utc = pd.Timestamp.now(timezone.utc)

            def calculate_duration(row):
                start = row['initialSubsStartDate']
                end = row['subscriptionCanceledAt']

                if pd.notnull(end):
                    duration = (end - start).total_seconds() / 86400
                    status = "Cancelled"
                else:
                    duration = (now_utc - start).total_seconds() / 86400
                    status = "Active"

                return pd.Series([duration, status])

            df_dur[['Duration_Days', 'Status']] = df_dur.apply(calculate_duration, axis=1)
            df_dur['Duration_Days'] = df_dur['Duration_Days'].apply(lambda x: x if x >= 0 else 0)

            # ==============================================================================
            # 🔍 FILTER LOGIC (RANGE)
            # ==============================================================================

            # Handle empty inputs (defaults)
            start_range = float(min_days) if min_days is not None else 0
            end_range = float(max_days) if max_days is not None else 99999

            # Apply Filter
            df_filtered = df_dur[
                (df_dur['Duration_Days'] >= start_range) &
                (df_dur['Duration_Days'] <= end_range)
                ].copy()

            # ==============================================================================
            # 🧮 STATISTICS
            # ==============================================================================

            total_subscribers = len(df_filtered)

            if total_subscribers > 0:
                mean_dur = df_filtered['Duration_Days'].mean()
                median_dur = df_filtered['Duration_Days'].median()
                min_dur = df_filtered['Duration_Days'].min()
                max_dur = df_filtered['Duration_Days'].max()
            else:
                mean_dur = median_dur = min_dur = max_dur = 0

            # Helper for formatting
            def format_duration(days):
                if days >= 1:
                    return f"{days:.2f} Days"
                else:
                    total_seconds = int(days * 86400)
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    return f"{hours}h {minutes}m"

            # ==============================================================================
            # 📈 GRAPH
            # ==============================================================================

            fig_hist = px.histogram(
                df_filtered,
                x='Duration_Days',
                color='Status',
                nbins=40,
                title=f"📊 Duration Distribution ({start_range} - {end_range} Days)",
                labels={'Duration_Days': 'Days Subscribed'},
                color_discrete_map={'Active': '#2ecc71', 'Cancelled': '#e74c3c'}
            )

            fig_hist.update_layout(
                template="plotly_white",
                yaxis_title="Count of Users",
                xaxis_title="Duration (Days)",
                bargap=0.1
            )

            # ==============================================================================
            # 🖥️ UI COMPONENTS
            # ==============================================================================

            def create_card(title, value, sub_text, color_class):
                return dbc.Col(dbc.Card([
                    dbc.CardHeader(title),
                    dbc.CardBody([
                        html.H3(value, className=color_class),
                        html.Small(sub_text, className="text-muted")
                    ])
                ], className="text-center shadow-sm h-100"), width=True)

            cards = dbc.Row([
                create_card("Total Users", f"{total_subscribers}", f"Range: {start_range}-{end_range}", "text-primary"),
                create_card("Mean Duration", format_duration(mean_dur), "Average", "text-info"),
                create_card("Median Duration", format_duration(median_dur), "Middle Value", "text-warning"),
                create_card("Shortest", format_duration(min_dur), "Min in Range", "text-danger"),
                create_card("Longest", format_duration(max_dur), "Max in Range", "text-success"),
            ], className="mb-4")

            # Table Data
            table_cols = ['User_ID', 'Company', 'initialSubsStartDate', 'subscriptionCanceledAt', 'Status',
                          'Duration_Days']
            table_data = df_filtered[table_cols].sort_values(by='Duration_Days', ascending=False).head(100)

            table_section = dash_table.DataTable(
                data=table_data.to_dict('records'),
                columns=[
                    {"name": "User ID", "id": "User_ID"},
                    {"name": "Company", "id": "Company"},
                    {"name": "Start Date", "id": "initialSubsStartDate", "type": "datetime"},
                    {"name": "End Date", "id": "subscriptionCanceledAt", "type": "datetime"},
                    {"name": "Status", "id": "Status"},
                    {"name": "Duration", "id": "Duration_Days", "type": "numeric", "format": {"specifier": ".2f"}},
                ],
                style_cell={'padding': '10px', 'textAlign': 'left'},
                style_header={'backgroundColor': '#8e44ad', 'color': 'white', 'fontWeight': 'bold'},
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(245, 240, 250)'},
                    {'if': {'filter_query': '{Status} eq "Active"'}, 'color': '#27ae60', 'fontWeight': 'bold'},
                    {'if': {'filter_query': '{Status} eq "Cancelled"'}, 'color': '#c0392b'}
                ],
                page_size=10,
                sort_action="native",
                filter_action="native"
            )

            return html.Div([
                cards,
                dbc.Row([
                    dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(figure=fig_hist)), className="shadow-sm mb-4"), width=12)
                ]),
                html.H4(f"📋 Top 100 Durations ({start_range} - {end_range} Days)", className="mb-3 text-white"),
                table_section
            ])

        except Exception as e:
            return dbc.Alert([html.H4("Error processing data"), html.Pre(traceback.format_exc())], color="danger")