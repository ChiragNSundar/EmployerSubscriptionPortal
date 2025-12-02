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
    html.H3("Package Subscription Analysis", className="my-4 text-center"),

    # --- Row 0: Filters ---
    # FIX APPLIED: Added style={'position': 'relative', 'zIndex': '1000'} to prevent clipping
    dbc.Row([
        # 1. Date Range Filter
        dbc.Col([
            html.Label("Select Date Range:", className="control-label"),
            html.Div(
                dcc.DatePickerRange(
                    id='date-picker-range-pkg',
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
            html.Label("Select Country:", className="control-label"),
            dcc.Dropdown(
                id='country-dropdown-pkg',
                options=[],
                multi=True,
                placeholder="All Countries",
                className="mb-3"
            )
        ], width=12, md=4),

        # 3. Type Filter
        dbc.Col([
            html.Label("Select Subscription Type:", className="control-label"),
            dcc.Dropdown(
                id='type-dropdown-pkg',
                options=[],
                multi=True,
                placeholder="All Types",
                className="mb-3"
            )
        ], width=12, md=4),

    ], className="mb-4 glass-container", style={'position': 'relative', 'zIndex': '1000'}),

    # --- Row 1: Placards (Total + Packages) ---
    dbc.Row([
        # Total Users
        dbc.Col(create_card("Total Subscribers", "card-total-pkg", color="dark"), width=12, md=3),

        # Specific Package Cards
        # Using 'warning' (yellow/gold) for Premium
        dbc.Col(create_card("Premium Users", "card-premium", color="warning"), width=12, md=3),
        # Using 'primary' (blue) for Professional
        dbc.Col(create_card("Professional Users", "card-professional", color="primary"), width=12, md=3),
        # Using 'secondary' (grey) or 'info' (teal) for Standard
        dbc.Col(create_card("Standard Users", "card-standard", color="info"), width=12, md=3),
    ], className="mb-2"),

    # --- Row 2: Donut Chart ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    # Donut Chart Container
                    dcc.Graph(id='package-donut-chart', style={'height': '600px'})
                ])
            ], className="shadow-sm glass-container")
        ], width=12)
    ])
], fluid=True)


# --- 2. CALLBACK REGISTRATION ---
def register_callbacks(app):
    # --- Callback A: Populate Dropdown Options ---
    @app.callback(
        [Output('country-dropdown-pkg', 'options'),
         Output('type-dropdown-pkg', 'options')],
        Input('global-data-store', 'data')
    )
    def update_pkg_filter_options(data):
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
            Output('card-total-pkg', 'children'),
            Output('card-premium', 'children'),
            Output('card-professional', 'children'),
            Output('card-standard', 'children'),
            Output('package-donut-chart', 'figure')
        ],
        [
            Input('global-data-store', 'data'),
            Input('date-picker-range-pkg', 'start_date'),
            Input('date-picker-range-pkg', 'end_date'),
            Input('country-dropdown-pkg', 'value'),
            Input('type-dropdown-pkg', 'value')
        ]
    )
    def update_package_overview(data, start_date, end_date, selected_countries, selected_types):
        # 1. Handle Empty Data
        if not data:
            empty_fig = px.pie(title="No Data Available")
            return "0", "0", "0", "0", empty_fig

        df = pd.DataFrame(data)

        # 2. Pre-process Date
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

        # 3. Pre-process Package Name (Normalize to lowercase for counting)
        if 'Package_Name' in df.columns:
            # Fill NaNs with 'Unknown' and convert to lowercase
            df['pkg_norm'] = df['Package_Name'].fillna('Unknown').astype(str).str.lower()
        else:
            df['pkg_norm'] = "unknown"
            df['Package_Name'] = "Unknown"

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
            if 'Subscription_Type' in df.columns:
                df = df[df['Subscription_Type'].isin(selected_types)]

        # --- 5. CALCULATE PLACARDS ---
        total_count = len(df)

        # Count occurrences of specific packages
        counts = df['pkg_norm'].value_counts()

        # Get counts safely (defaults to 0 if not found)
        # Note: We use lowercase keys because we normalized 'pkg_norm' above
        count_premium = counts.get('premium', 0)
        count_professional = counts.get('professional', 0)
        count_standard = counts.get('standard', 0)

        # --- 6. GENERATE DONUT CHART ---

        if df.empty:
            fig = px.pie(title="No Data Found for Selected Filters")
        else:
            # Group by Package Name for the chart
            # We use the original column (or a capitalized version) for better display labels
            df_grouped = df.groupby('Package_Name').size().reset_index(name='count')

            # Create Donut Chart (hole=0.5 makes it a donut)
            fig = px.pie(
                df_grouped,
                values='count',
                names='Package_Name',
                title='Subscribers by Package',
                template="plotly_white",
                hole=0.5,  # <--- THIS MAKES IT A DONUT CHART
                color_discrete_map={
                    'Premium': '#ffc107', 'premium': '#ffc107',  # Gold/Yellow
                    'Professional': '#0d6efd', 'professional': '#0d6efd',  # Blue
                    'Standard': '#0dcaf0', 'standard': '#0dcaf0'  # Cyan/Info
                }
            )

            fig.update_traces(textposition='inside', textinfo='percent+label')

            fig.update_layout(
                legend_title="Package Name",
                margin=dict(t=40, b=20, l=0, r=0),
                hovermode="closest"
            )

        return (
            f"{total_count:,}",
            f"{count_premium:,}",
            f"{count_professional:,}",
            f"{count_standard:,}",
            fig
        )