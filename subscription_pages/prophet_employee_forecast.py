import pandas as pd
import numpy as np
import plotly.graph_objs as go
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from prophet import Prophet  # <--- IMPORT PROPHET

# --- PROPHET EMPLOYEE FORECAST LAYOUT ---
prophet_employee_layout = dbc.Container([
    html.H3("AI Employee Subscription Forecasting (Prophet Volume)", className="my-4 text-center text-white"),

    # --- KPI Cards (Row 1: Total, New, Renewed) ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(id='prophet-emp-card-total-title', children="Total Activity", className="card-title text-muted"),
                    html.H4(id='prophet-emp-card-total-pred', children="0", className="text-primary fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=12, md=4),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(id='prophet-emp-card-new-title', children="New Employees", className="card-title text-muted"),
                    html.H4(id='prophet-emp-card-new-pred', children="0", className="text-success fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=12, md=4),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(id='prophet-emp-card-renewed-title', children="Renewed Employees",
                            className="card-title text-muted"),
                    html.H4(id='prophet-emp-card-renewed-pred', children="0", className="text-info fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=12, md=4),
    ]),

    # --- KPI Cards (Row 2: Upgraded, Trial, Cancelled) ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(id='prophet-emp-card-upgraded-title', children="Upgraded Employees",
                            className="card-title text-muted"),
                    html.H4(id='prophet-emp-card-upgraded-pred', children="0", className="text-warning fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=12, md=4),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(id='prophet-emp-card-trial-title', children="Trial Employees", className="card-title text-muted"),
                    html.H4(id='prophet-emp-card-trial-pred', children="0", className="text-secondary fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=12, md=4),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(id='prophet-emp-card-cancelled-title', children="Cancelled Employees",
                            className="card-title text-muted"),
                    html.H4(id='prophet-emp-card-cancelled-pred', children="0", className="text-danger fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=12, md=4),
    ], className="mb-2"),

    # --- FILTERS ROW (Date Range & Type) ---
    dbc.Row([
        # Filter 1: Date Range
        dbc.Col([
            html.Label("Filter History Date Range:", className="fw-bold"),
            html.Br(),
            dcc.DatePickerRange(
                id='prophet-emp-date-filter',
                display_format='YYYY-MM-DD',
                start_date=None,
                end_date=None,
                style={'zIndex': '2000', 'position': 'relative', 'width': '100%'}
            )
        ],
            width=12, md=6,
            className="mb-3",
            style={'zIndex': '1050', 'position': 'relative'}
        ),

        # Filter 2: Subscription Type
        dbc.Col([
            html.Label("Filter Subscription Types:", className="fw-bold"),
            dcc.Dropdown(
                id='prophet-emp-type-filter',
                options=[
                    {'label': 'New', 'value': 'new'},
                    {'label': 'Renewed', 'value': 'renewed'},
                    {'label': 'Upgraded', 'value': 'upgraded'},
                    {'label': 'Trial', 'value': 'trial'},
                    {'label': 'Cancelled', 'value': 'cancelled'}
                ],
                value=[],
                multi=True,
                placeholder="Select types (Default: All)",
                style={'zIndex': '2000', 'position': 'relative'}
            )
        ],
            width=12, md=6,
            className="mb-3",
            style={'zIndex': '1050', 'position': 'relative', 'overflow': 'visible'}
        ),
    ],
        className="mb-2 glass-container",
        style={'overflow': 'visible', 'position': 'relative', 'zIndex': '1050'}
    ),

    # --- Controls Row (Days & Button) ---
    dbc.Row([
        # --- COLUMN 1: DAYS INPUT ---
        dbc.Col([
            html.Label("Days to Predict:", className="fw-bold"),
            dbc.Input(id='prophet-emp-forecast-days', type='number', value=30, min=7, max=365, step=1)
        ], width=12, md=6, style={'zIndex': '1000', 'position': 'relative'}),

        # --- COLUMN 2: BUTTON ---
        dbc.Col([
            html.Br(),
            dbc.Button("Generate Prophet Forecast", id='btn-run-prophet-emp', color="primary", className="w-100")
        ], width=12, md=6, style={'zIndex': '1000', 'position': 'relative'}),

    ],
        className="mb-4 glass-container",
        style={'overflow': 'visible', 'position': 'relative', 'zIndex': '1000'}
    ),

    # --- GRAPH ROW ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Loading(
                        id="loading-prophet-emp",
                        type="default",
                        children=dcc.Graph(id='prophet-emp-graph', style={'height': '500px'})
                    )
                ])
            ],
                className="shadow-sm glass-container",
                style={'zIndex': '1', 'position': 'relative'}
            )
        ], width=12)
    ])
], fluid=True)


# --- HELPER FUNCTION: PROPHET PREDICTION LOGIC ---
def get_prophet_employee_count(df_in, days_to_predict):
    df = df_in.copy()

    # 1. Clean Dates
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])

    if df.empty: return None

    # --- FIX: FIND GLOBAL MAX DATE ---
    global_max_date = df['Date'].max()

    types = ['new', 'renewed', 'upgraded', 'trial', 'cancelled']
    results = {}
    history_list = []
    future_dates = None

    for sub_type in types:
        type_df = df[df['Subscription_Type'] == sub_type].copy()

        # Group by Day (Count)
        daily_df = type_df.groupby(pd.Grouper(key='Date', freq='D')).size().reset_index(name='y')
        daily_df = daily_df.rename(columns={'Date': 'ds'})

        # --- FIX: ALIGN DATES ---
        if not daily_df.empty:
            full_range = pd.date_range(start=daily_df['ds'].min(), end=global_max_date, freq='D')
            daily_df = daily_df.set_index('ds').reindex(full_range, fill_value=0).reset_index().rename(columns={'index': 'ds'})

        daily_df_hist = daily_df.copy()
        daily_df_hist['Subscription_Type'] = sub_type
        history_list.append(daily_df_hist)

        if len(daily_df) < 5:
            results[sub_type] = np.zeros(int(days_to_predict))
            continue

        m = Prophet(daily_seasonality=True, yearly_seasonality=False, weekly_seasonality=True)
        m.fit(daily_df)

        future = m.make_future_dataframe(periods=int(days_to_predict))
        forecast = m.predict(future)

        future_forecast = forecast.tail(int(days_to_predict))
        preds = np.round(np.maximum(future_forecast['yhat'].values, 0)) # Round for employees

        results[sub_type] = preds

        if future_dates is None:
            future_dates = future_forecast['ds'].values

    if not history_list: return None
    full_hist_df = pd.concat(history_list)
    hist_pivot = full_hist_df.pivot(index='ds', columns='Subscription_Type', values='y').fillna(0)

    for col in types:
        if col not in hist_pivot.columns: hist_pivot[col] = 0

    hist_pivot['total'] = hist_pivot['new'] + hist_pivot['renewed'] + hist_pivot['upgraded'] + hist_pivot['trial'] + hist_pivot['cancelled']
    hist_df = hist_pivot.reset_index().rename(columns={'ds': 'Date'})

    preds_new = results.get('new', np.zeros(int(days_to_predict)))
    preds_renewed = results.get('renewed', np.zeros(int(days_to_predict)))
    preds_upgraded = results.get('upgraded', np.zeros(int(days_to_predict)))
    preds_trial = results.get('trial', np.zeros(int(days_to_predict)))
    preds_cancelled = results.get('cancelled', np.zeros(int(days_to_predict)))
    preds_total = preds_new + preds_renewed + preds_upgraded + preds_trial + preds_cancelled

    return {
        'sums': (sum(preds_total), sum(preds_new), sum(preds_renewed), sum(preds_upgraded), sum(preds_trial), sum(preds_cancelled)),
        'dates': future_dates,
        'preds': (preds_total, preds_new, preds_renewed, preds_upgraded, preds_trial, preds_cancelled),
        'history': hist_df
    }


# --- CALLBACKS ---
def register_prophet_employee_callbacks(app):
    @app.callback(
        [Output('prophet-emp-card-total-pred', 'children'),
         Output('prophet-emp-card-new-pred', 'children'),
         Output('prophet-emp-card-renewed-pred', 'children'),
         Output('prophet-emp-card-upgraded-pred', 'children'),
         Output('prophet-emp-card-trial-pred', 'children'),
         Output('prophet-emp-card-cancelled-pred', 'children'),
         Output('prophet-emp-graph', 'figure'),
         Output('prophet-emp-card-total-title', 'children'),
         Output('prophet-emp-card-new-title', 'children'),
         Output('prophet-emp-card-renewed-title', 'children'),
         Output('prophet-emp-card-upgraded-title', 'children'),
         Output('prophet-emp-card-trial-title', 'children'),
         Output('prophet-emp-card-cancelled-title', 'children')],
        [Input('btn-run-prophet-emp', 'n_clicks')],
        [State('global-data-store', 'data'),
         State('prophet-emp-forecast-days', 'value'),
         State('prophet-emp-date-filter', 'start_date'),
         State('prophet-emp-date-filter', 'end_date'),
         State('prophet-emp-type-filter', 'value')]
    )
    def update_prophet_employee_forecast(n_clicks, data, days, start_date, end_date, selected_types):
        # Default Empty State
        empty_res = ("-", "-", "-", "-", "-", "-", go.Figure().update_layout(title="No Data"),
                     "Total", "New", "Renewed", "Upgraded", "Trial", "Cancelled")

        if not data: return empty_res
        if n_clicks is None:
            return "0", "0", "0", "0", "0", "0", go.Figure().update_layout(
                title="Click 'Generate Forecast' to see predictions",
                xaxis={'visible': False}, yaxis={'visible': False}
            ), "Total", "New", "Renewed", "Upgraded", "Trial", "Cancelled"

        df = pd.DataFrame(data)

        # --- 1. DATA CLEANING ---
        if 'lastPaymentReceivedOn' in df.columns:
            df['Date'] = pd.to_datetime(df['lastPaymentReceivedOn'], errors='coerce')
        elif 'dateUTC' in df.columns:
            df['Date'] = pd.to_datetime(df['dateUTC'], errors='coerce')
        elif 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        else:
            return empty_res

        if 'Subscription_Type' in df.columns:
            df['Subscription_Type'] = df['Subscription_Type'].astype(str)
        elif 'type' in df.columns:
            df['Subscription_Type'] = df['type'].astype(str)
        else:
            return empty_res

        # --- 2. BASIC FILTERING ---
        df['Subscription_Type'] = df['Subscription_Type'].str.lower().str.strip()
        df['Subscription_Type'] = df['Subscription_Type'].replace(
            {'canceled': 'cancelled', 'cancellation': 'cancelled'})

        valid_types = ['new', 'renewed', 'upgraded', 'trial', 'cancelled']
        mask_type = df['Subscription_Type'].isin(valid_types)
        mask_date = df['Date'].notna()

        df_clean = df[mask_type & mask_date].copy()

        # --- 3. APPLY USER FILTERS ---
        if start_date and end_date:
            df_clean = df_clean[(df_clean['Date'] >= start_date) & (df_clean['Date'] <= end_date)]

        if selected_types and len(selected_types) > 0:
            df_clean = df_clean[df_clean['Subscription_Type'].isin(selected_types)]

        # --- 4. RUN PROPHET PREDICTION ---
        result = get_prophet_employee_count(df_clean, days)

        if not result:
            return empty_res

        (s_tot, s_new, s_ren, s_upg, s_tri, s_can) = result['sums']
        f_dates = result['dates']
        (p_tot, p_new, p_ren, p_upg, p_tri, p_can) = result['preds']
        hist_df = result['history']

        def fmt(val):
            return f"{int(val):,}"

        # --- 5. GENERATE GRAPH ---
        fig = go.Figure()

        # Helper to add traces (Ghost Traces Logic)
        def add_traces(hist_col, pred_vals, name, color, is_main_line=False):
            line_width = 3 if is_main_line else 0
            show_legend = True if is_main_line else False

            # History Trace
            fig.add_trace(go.Scatter(
                x=hist_df['Date'],
                y=hist_df[hist_col],
                mode='lines',
                name=f"{name} (Actual)",
                line=dict(color=color, width=line_width),
                showlegend=show_legend,
                hoverinfo='x+name+y'
            ))

            # Prediction Trace
            fig.add_trace(go.Scatter(
                x=f_dates,
                y=pred_vals,
                mode='lines',
                name=f"{name} (Pred)",
                line=dict(color='red', width=line_width, dash='dash'),
                showlegend=show_legend,
                hoverinfo='x+name+y'
            ))

            # Connector Trace
            if is_main_line and len(pred_vals) > 0:
                fig.add_trace(go.Scatter(
                    x=[hist_df['Date'].iloc[-1], f_dates[0]],
                    y=[hist_df[hist_col].iloc[-1], pred_vals[0]],
                    mode='lines',
                    showlegend=False,
                    line=dict(color=color, width=line_width, dash='dash'),
                    hoverinfo='skip'
                ))

        # --- ADD TRACES ---
        add_traces('total', p_tot, "Total", "#0d6efd", is_main_line=True)
        add_traces('new', p_new, "New", "#198754", is_main_line=False)
        add_traces('renewed', p_ren, "Renewed", "#0dcaf0", is_main_line=False)
        add_traces('upgraded', p_upg, "Upgraded", "#ffc107", is_main_line=False)
        add_traces('trial', p_tri, "Trial", "#6f42c1", is_main_line=False)
        add_traces('cancelled', p_can, "Cancelled", "#dc3545", is_main_line=False)

        # --- UPDATE LAYOUT ---
        fig.update_layout(
            title=f"Daily Employee Subscription Forecast (Prophet Volume)",
            xaxis_title="Date",
            yaxis_title="Number of Employees",
            template="plotly_white",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        fig.update_xaxes(hoverformat='%b %d, %Y')

        t_suffix = f"(Next {days} Days)"

        return (fmt(s_tot), fmt(s_new), fmt(s_ren), fmt(s_upg), fmt(s_tri), fmt(s_can), fig,
                f"Total {t_suffix}", f"New {t_suffix}", f"Renewed {t_suffix}",
                f"Upgraded {t_suffix}", f"Trial {t_suffix}", f"Cancelled {t_suffix}")