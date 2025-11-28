import pandas as pd
import plotly.graph_objects as go
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
    html.H3("Monthly Payment Comparison (Total vs Paid)", className="my-4 text-center"),

    # --- Row 0: Filters ---
    dbc.Row([
        # 1. Month Filter (Multi-Select)
        dbc.Col([
            html.Label("Select Month(s):", className="control-label"),
            dcc.Dropdown(
                id='cmp-month-dropdown',  # Unique ID
                options=[],
                multi=True,
                placeholder="Select Months...",
                className="mb-3"
            )
        ], width=12, md=4),

        # 2. Country Filter
        dbc.Col([
            html.Label("Select Country:", className="control-label"),
            dcc.Dropdown(
                id='cmp-month-country-dropdown',  # Unique ID
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
                id='cmp-month-type-dropdown',  # Unique ID
                options=[],
                multi=True,
                placeholder="All Types",
                className="mb-3"
            )
        ], width=12, md=4),

    ], className="mb-4 glass-container"),

    # --- Row 1: Placards (4 Cards) ---
    dbc.Row([
        dbc.Col(create_card("Total (Paid+Unpaid)", "cmp-month-card-total-all", color="dark"), width=6, md=3),
        dbc.Col(create_card("Total Paid Subs", "cmp-month-card-total-paid", color="success"), width=6, md=3),
        dbc.Col(create_card("Paid Percentage (%)", "cmp-month-card-paid-percent", color="info"), width=6, md=3),
        dbc.Col(create_card("Total Revenue (€)", "cmp-month-card-total-revenue", color="warning"), width=6, md=3),
    ], className="mb-2 justify-content-center"),

    # --- Row 2: Combined Graph ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                #dbc.CardHeader("Monthly Trend: Total vs Paid & Paid %"),
                dbc.CardBody([
                    dcc.Graph(id='cmp-month-bar-graph', style={'height': '500px'})  # Unique ID
                ])
            ], className="shadow-sm glass-container")
        ], width=12)
    ])
], fluid=True)


# --- 2. CALLBACK REGISTRATION ---
def register_callbacks(app):
    # --- Callback A: Populate Dropdown Options ---
    @app.callback(
        [Output('cmp-month-dropdown', 'options'),
         Output('cmp-month-country-dropdown', 'options'),
         Output('cmp-month-type-dropdown', 'options')],
        Input('global-data-store', 'data')
    )
    def update_cmp_month_filter_options(data):
        if not data:
            return [], [], []

        df = pd.DataFrame(data)

        # 1. Month Options
        month_opts = []
        if 'Date' in df.columns:
            # Convert to datetime
            temp_dates = pd.to_datetime(df['Date'], errors='coerce').dropna()
            # Create DataFrame to sort
            dates_df = pd.DataFrame({'date': temp_dates})
            dates_df['label'] = dates_df['date'].dt.strftime('%b %Y')  # Jan 2023
            dates_df['value'] = dates_df['date'].dt.strftime('%Y-%m')  # 2023-01

            # Get unique, sort descending
            unique_months = dates_df[['label', 'value']].drop_duplicates().sort_values('value', ascending=False)
            month_opts = unique_months.to_dict('records')

        # 2. Country Options
        country_opts = []
        if 'Location' in df.columns:
            countries = sorted(df['Location'].dropna().unique().astype(str))
            country_opts = [{'label': c, 'value': c} for c in countries]

        # 3. Type Options
        type_opts = []
        if 'Subscription_Type' in df.columns:
            all_types = sorted(df['Subscription_Type'].dropna().unique().astype(str))
            type_opts = [{'label': t.title(), 'value': t} for t in all_types]

        return month_opts, country_opts, type_opts

    # --- Callback B: Update Dashboard ---
    @app.callback(
        [
            Output('cmp-month-card-total-all', 'children'),
            Output('cmp-month-card-total-paid', 'children'),
            Output('cmp-month-card-paid-percent', 'children'),
            Output('cmp-month-card-total-revenue', 'children'),
            Output('cmp-month-bar-graph', 'figure')
        ],
        [
            Input('global-data-store', 'data'),
            Input('cmp-month-dropdown', 'value'),
            Input('cmp-month-country-dropdown', 'value'),
            Input('cmp-month-type-dropdown', 'value')
        ]
    )
    def update_cmp_month_overview(data, selected_months, selected_countries, selected_types):
        # 1. Handle Empty Data
        empty_fig = go.Figure()
        empty_fig.update_layout(title="No Data Available")
        if not data:
            return "0", "0", "0%", "€ 0", empty_fig

        df = pd.DataFrame(data)

        # 2. Data Pre-processing
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

        if 'lastPaymentReceivedOn' in df.columns:
            df['lastPaymentReceivedOn'] = pd.to_datetime(df['lastPaymentReceivedOn'], errors='coerce')
        else:
            df['lastPaymentReceivedOn'] = pd.NaT

        if 'lastAmountPaidEUR' in df.columns:
            df['lastAmountPaidEUR'] = pd.to_numeric(df['lastAmountPaidEUR'], errors='coerce').fillna(0)
        else:
            df['lastAmountPaidEUR'] = 0

        if 'Subscription_Type' in df.columns:
            df['type_norm'] = df['Subscription_Type'].astype(str).str.lower()
        else:
            df['type_norm'] = "unknown"

        # --- 3. DETERMINE PAID STATUS ---
        paid_types = ['new', 'renewed', 'upgraded']

        is_paid_type = df['type_norm'].isin(paid_types)
        has_valid_payment = (df['lastPaymentReceivedOn'] >= df['Date']).fillna(False)

        df['is_paid'] = is_paid_type & has_valid_payment

        # --- 4. APPLY FILTERS ---

        # Month Filter
        if selected_months:
            df['month_str'] = df['Date'].dt.strftime('%Y-%m')
            df = df[df['month_str'].isin(selected_months)]

        # Country Filter
        if selected_countries:
            if 'Location' in df.columns:
                df = df[df['Location'].isin(selected_countries)]

        # Type Filter
        if selected_types:
            df = df[df['Subscription_Type'].isin(selected_types)]

        # --- 5. CALCULATE PLACARDS ---
        total_all = len(df)
        total_paid = df['is_paid'].sum()
        total_revenue = df.loc[df['is_paid'], 'lastAmountPaidEUR'].sum()

        if total_all > 0:
            paid_percent = (total_paid / total_all) * 100
        else:
            paid_percent = 0

        # --- 6. GENERATE GRAPH ---
        if df.empty:
            fig = go.Figure()
            fig.update_layout(title="No Data Found for Selected Filters")
        else:
            # Create Month-Year column for grouping (First day of month)
            df['month_start'] = df['Date'].dt.to_period('M').dt.to_timestamp()

            # Group by Month
            df_grouped = df.groupby('month_start').agg(
                Total_Count=('is_paid', 'count'),
                Paid_Count=('is_paid', 'sum')
            ).reset_index()

            # Sort by date
            df_grouped = df_grouped.sort_values('month_start')

            df_grouped['Paid_Percentage'] = (df_grouped['Paid_Count'] / df_grouped['Total_Count']) * 100

            # Text labels for scatter
            df_grouped['Percent_Text'] = df_grouped['Paid_Percentage'].apply(lambda x: f"{x:.0f}%" if x > 0 else "")

            fig = go.Figure()

            # Bar: Total (Dark Blue)
            fig.add_trace(go.Bar(
                x=df_grouped['month_start'],
                y=df_grouped['Total_Count'],
                name='Total Subs',
                marker_color='#2c3e50',  # Dark Blue
                opacity=0.7,
                yaxis='y1'
            ))

            # Bar: Paid (Teal)
            fig.add_trace(go.Bar(
                x=df_grouped['month_start'],
                y=df_grouped['Paid_Count'],
                name='Paid Subs',
                marker_color='#20c997',  # Teal
                yaxis='y1'
            ))

            # Line: Percentage (Pink/Red with Text)
            fig.add_trace(go.Scatter(
                x=df_grouped['month_start'],
                y=df_grouped['Paid_Percentage'],
                name='Paid %',
                mode='lines+markers+text',
                text=df_grouped['Percent_Text'],
                textposition='top center',
                textfont=dict(color='#d63384', size=10, weight='bold'),
                line=dict(color='#d63384', width=3),
                marker=dict(size=8, color='#d63384'),
                yaxis='y2'
            ))

            fig.update_layout(
                title="Monthly Subscriptions: Total vs Paid",
                xaxis_title="Month",
                yaxis=dict(title="Count", side="left"),
                yaxis2=dict(
                    title="Paid %",
                    side="right",
                    overlaying="y",
                    range=[0, 115],
                    showgrid=False
                ),
                barmode='group',
                legend=dict(x=0.01, y=1.1, orientation='h'),
                template="plotly_white",
                hovermode="x unified"
            )

            # Format X-Axis for Months
            fig.update_xaxes(
                dtick="M1",
                tickformat="%b %Y",
                title_text="Month"
            )

        # Format Strings
        revenue_str = f"€ {total_revenue:,.2f}"
        percent_str = f"{paid_percent:.1f}%"

        return (
            f"{total_all:,}",
            f"{total_paid:,}",
            percent_str,
            revenue_str,
            fig
        )