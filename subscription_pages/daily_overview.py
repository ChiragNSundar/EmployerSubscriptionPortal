import pandas as pd
import plotly.express as px
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc


# --- 1. LAYOUT DEFINITION ---
def create_card(title, card_id, color="primary"):
    """Helper function to create a styled summary card."""
    return dbc.Card(
        dbc.CardBody([
            html.H5(title, className="card-title", style={'fontSize': '1rem', 'opacity': '0.8'}),
            html.H2("0", id=card_id, className="card-text", style={'fontWeight': 'bold'})
        ]),
        color=color,
        inverse=True,
        className="mb-4 shadow-sm"
    )


layout = dbc.Container([
    html.H3("Daily Overview Dashboard", className="my-4 text-center"),

    # --- Row 0: Filters ---
    dbc.Row([
        # 1. Date Range Picker
        dbc.Col([
            html.Label("Select Date Range:", className="fw-bold"),
            html.Div(
                dcc.DatePickerRange(
                    id='date-picker-range',
                    display_format='YYYY-MM-DD',
                    start_date=None,
                    end_date=None,
                    clearable=True,
                    style={'width': '100%'}
                ),
                className="mb-3"
            )
        ], width=12, md=4),

        # 2. Country Filter
        dbc.Col([
            html.Label("Select Country:", className="fw-bold"),
            dcc.Dropdown(
                id='country-dropdown',
                options=[],
                multi=True,
                placeholder="All Countries",
                className="mb-3"
            )
        ], width=12, md=4),

        # 3. Type Filter
        dbc.Col([
            html.Label("Select Subscription Type:", className="fw-bold"),
            dcc.Dropdown(
                id='type-dropdown',
                options=[],
                multi=True,
                placeholder="All Types",
                className="mb-3"
            )
        ], width=12, md=4),

    ], className="mb-4 p-3 bg-light rounded shadow-sm"),

    # --- Row 1: Placards ---
    dbc.Row([
        dbc.Col(create_card("Total Records", "card-total", color="dark"), width=12, md=4, lg=2),
        dbc.Col(create_card("New", "card-new", color="success"), width=6, md=4, lg=2),
        dbc.Col(create_card("Trial", "card-trial", color="info"), width=6, md=4, lg=2),
        dbc.Col(create_card("Renewed", "card-renewed", color="primary"), width=6, md=4, lg=2),
        dbc.Col(create_card("Upgraded", "card-upgraded", color="warning"), width=6, md=4, lg=2),
        dbc.Col(create_card("Cancelled", "card-cancelled", color="danger"), width=6, md=4, lg=2),
    ], className="mb-2"),

    # --- Row 2: Bar Graph ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Daily Trend by Subscription Type"),
                dbc.CardBody([
                    dcc.Graph(id='daily-type-bar-graph', style={'height': '500px'})
                ])
            ], className="shadow-sm")
        ], width=12)
    ])
], fluid=True)


# --- 2. CALLBACK REGISTRATION ---
def register_callbacks(app):
    # --- Callback A: Populate Dropdown Options ---
    @app.callback(
        [Output('country-dropdown', 'options'),
         Output('type-dropdown', 'options')],
        Input('global-data-store', 'data')
    )
    def update_filter_options(data):
        if not data:
            return [], []

        df = pd.DataFrame(data)

        # 1. Country Options
        country_opts = []
        if 'Location' in df.columns:
            countries = sorted(df['Location'].dropna().unique().astype(str))
            country_opts = [{'label': c, 'value': c} for c in countries]

        # 2. Type Options
        type_opts = []
        if 'Subscription_Type' in df.columns:
            types = sorted(df['Subscription_Type'].dropna().astype(str).unique())
            type_opts = [{'label': t.title(), 'value': t} for t in types]

        return country_opts, type_opts

    # --- Callback B: Update Dashboard ---
    @app.callback(
        [
            Output('card-total', 'children'),
            Output('card-new', 'children'),
            Output('card-trial', 'children'),
            Output('card-renewed', 'children'),
            Output('card-upgraded', 'children'),
            Output('card-cancelled', 'children'),
            Output('daily-type-bar-graph', 'figure')
        ],
        [
            Input('global-data-store', 'data'),
            Input('date-picker-range', 'start_date'),
            Input('date-picker-range', 'end_date'),
            Input('country-dropdown', 'value'),
            Input('type-dropdown', 'value')
        ]
    )
    def update_daily_overview(data, start_date, end_date, selected_countries, selected_types):
        # 1. Handle Empty Data
        if not data:
            empty_fig = px.bar(title="No Data Available")
            return "0", "0", "0", "0", "0", "0", empty_fig

        df = pd.DataFrame(data)

        # 2. Pre-process Date
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df['date_only'] = df['Date'].dt.date
        else:
            df['date_only'] = None

        # 3. Pre-process Type
        if 'Subscription_Type' in df.columns:
            df['type_norm'] = df['Subscription_Type'].astype(str).str.lower()
        else:
            df['type_norm'] = "unknown"
            df['Subscription_Type'] = "Unknown"

        # --- 4. APPLY FILTERS ---

        # A. Date Filter
        if start_date:
            df = df[df['Date'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['Date'] <= pd.to_datetime(end_date)]

        # B. Country Filter
        if selected_countries:
            if 'Location' in df.columns:
                df = df[df['Location'].isin(selected_countries)]

        # C. Type Filter
        if selected_types:
            df = df[df['Subscription_Type'].isin(selected_types)]

        # --- 5. CALCULATE PLACARDS ---
        total_count = len(df)
        counts = df['type_norm'].value_counts()

        count_new = counts.get('new', 0)
        count_trial = counts.get('trial', 0)
        count_renewed = counts.get('renewed', 0)
        count_upgraded = counts.get('upgraded', 0)
        count_cancelled = counts.get('cancelled', 0)

        # --- 6. GENERATE GRAPH ---

        if df.empty:
            fig = px.bar(title="No Data Found for Selected Filters")
        else:
            # A. Group Data
            df_grouped = df.groupby(['date_only', 'Subscription_Type']).size().reset_index(name='count')

            # B. Fix "Skipped Dates" (Fill Gaps)
            min_d = pd.to_datetime(start_date).date() if start_date else df['date_only'].min()
            max_d = pd.to_datetime(end_date).date() if end_date else df['date_only'].max()

            if min_d and max_d:
                full_date_range = pd.date_range(start=min_d, end=max_d, freq='D').date
                unique_types = selected_types if selected_types else df['Subscription_Type'].unique()
                multi_idx = pd.MultiIndex.from_product([full_date_range, unique_types],
                                                       names=['date_only', 'Subscription_Type'])
                df_grouped = df_grouped.set_index(['date_only', 'Subscription_Type']).reindex(multi_idx,
                                                                                              fill_value=0).reset_index()

            # C. Create Plot
            fig = px.bar(
                df_grouped,
                x='date_only',
                y='count',
                color='Subscription_Type',
                barmode='group',
                title="Daily Subscriptions by Type",
                labels={'date_only': 'Day', 'count': 'Total Subscriptions', 'Subscription_Type': 'Status'},
                template="plotly_white",
                color_discrete_map={
                    'new': '#198754', 'New': '#198754',
                    'trial': '#0dcaf0', 'Trial': '#0dcaf0',
                    'renewed': '#0d6efd', 'Renewed': '#0d6efd',
                    'upgraded': '#ffc107', 'Upgraded': '#ffc107',
                    'cancelled': '#dc3545', 'Cancelled': '#dc3545'
                }
            )

            # D. Force X-Axis to show ONLY THE DAY (dd)
            fig.update_xaxes(
                dtick="D1",  # Tick every 1 day
                tickformat="%d",  # <--- SHOWS ONLY DAY (e.g., 01, 15, 30)
                title_text="Day of Month"
            )

            fig.update_layout(
                yaxis_title="Count",
                legend_title="Subscription Type",
                hovermode="x unified"
            )

        return (
            f"{total_count:,}",
            f"{count_new:,}",
            f"{count_trial:,}",
            f"{count_renewed:,}",
            f"{count_upgraded:,}",
            f"{count_cancelled:,}",
            fig
        )