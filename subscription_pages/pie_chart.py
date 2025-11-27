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
    html.H3("Location Analysis Dashboard", className="my-4 text-center"),

    # --- Row 0: Filters ---
    dbc.Row([
        # 1. Date Range Filter (Replaces Month Dropdown)
        dbc.Col([
            html.Label("Select Date Range:", className="fw-bold"),
            html.Div(
                dcc.DatePickerRange(
                    id='date-picker-range-loc',  # Unique ID
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
                id='country-dropdown-loc',
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
                id='type-dropdown-loc',
                options=[],
                multi=True,
                placeholder="All Types",
                className="mb-3"
            )
        ], width=12, md=4),

    ], className="mb-4 p-3 bg-light rounded shadow-sm"),

    # --- Row 1: Placards ---
    dbc.Row([
        dbc.Col(create_card("Total Records", "card-total-l", color="dark"), width=12, md=4, lg=2),
        dbc.Col(create_card("New", "card-new-l", color="success"), width=6, md=4, lg=2),
        dbc.Col(create_card("Trial", "card-trial-l", color="info"), width=6, md=4, lg=2),
        dbc.Col(create_card("Renewed", "card-renewed-l", color="primary"), width=6, md=4, lg=2),
        dbc.Col(create_card("Upgraded", "card-upgraded-l", color="warning"), width=6, md=4, lg=2),
        dbc.Col(create_card("Cancelled", "card-cancelled-l", color="danger"), width=6, md=4, lg=2),
    ], className="mb-2"),

    # --- Row 2: Pie Chart ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Total Subscriptions by Country"),
                dbc.CardBody([
                    dcc.Graph(id='country-pie-chart', style={'height': '500px'})
                ])
            ], className="shadow-sm")
        ], width=12)
    ])
], fluid=True)


# --- 2. CALLBACK REGISTRATION ---
def register_callbacks(app):
    # --- Callback A: Populate Dropdown Options ---
    @app.callback(
        [Output('country-dropdown-loc', 'options'),
         Output('type-dropdown-loc', 'options')],
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
            Output('card-total-l', 'children'),
            Output('card-new-l', 'children'),
            Output('card-trial-l', 'children'),
            Output('card-renewed-l', 'children'),
            Output('card-upgraded-l', 'children'),
            Output('card-cancelled-l', 'children'),
            Output('country-pie-chart', 'figure')
        ],
        [
            Input('global-data-store', 'data'),
            Input('date-picker-range-loc', 'start_date'),
            Input('date-picker-range-loc', 'end_date'),
            Input('country-dropdown-loc', 'value'),
            Input('type-dropdown-loc', 'value')
        ]
    )
    def update_location_overview(data, start_date, end_date, selected_countries, selected_types):
        # 1. Handle Empty Data
        if not data:
            empty_fig = px.pie(title="No Data Available")
            return "0", "0", "0", "0", "0", "0", empty_fig

        df = pd.DataFrame(data)

        # 2. Pre-process Date
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

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

        # --- 6. GENERATE PIE CHART ---

        if df.empty:
            fig = px.pie(title="No Data Found for Selected Filters")
        else:
            # Group by Location (Country)
            if 'Location' in df.columns:
                # Fill NaN locations with "Unknown" to ensure they show up
                df['Location'] = df['Location'].fillna('Unknown')

                # Count rows per country
                df_grouped = df.groupby('Location').size().reset_index(name='count')

                # Create Pie Chart
                fig = px.pie(
                    df_grouped,
                    values='count',
                    names='Location',
                    title='Distribution by Country',
                    template="plotly_white",
                    hole=0  # Makes it a Donut chart (optional, set to 0 for full pie)
                )

                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(legend_title="Country")
            else:
                fig = px.pie(title="Location Data Missing")

        return (
            f"{total_count:,}",
            f"{count_new:,}",
            f"{count_trial:,}",
            f"{count_renewed:,}",
            f"{count_upgraded:,}",
            f"{count_cancelled:,}",
            fig
        )