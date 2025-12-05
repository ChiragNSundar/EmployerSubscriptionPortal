import pandas as pd
import numpy as np
import plotly.graph_objs as go
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from prophet import Prophet

# =============================================================================
# 1. LAYOUT DEFINITION
# =============================================================================
prophet_layout = dbc.Container([
    html.H3("AI Revenue Forecasting (Outliers Removed)", className="my-4 text-center text-white"),

    # ---------------------------------------------------------------------
    # FUTURE FORECAST DASHBOARD
    # ---------------------------------------------------------------------
    html.Br(),

    # --- KPI Cards Row ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(id='prophet-card-total-title', children="Total Revenue Predicted",
                            className="card-title text-muted"),
                    html.H4(id='prophet-card-total-pred', children="€0.00", className="text-primary fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=6, md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(id='prophet-card-new-title', children="New Revenue Predicted",
                            className="card-title text-muted"),
                    html.H4(id='prophet-card-new-pred', children="€0.00", className="text-success fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=6, md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(id='prophet-card-renewed-title', children="Renewed Revenue Predicted",
                            className="card-title text-muted"),
                    html.H4(id='prophet-card-renewed-pred', children="€0.00", className="text-info fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=6, md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(id='prophet-card-upgraded-title', children="Upgraded Revenue Predicted",
                            className="card-title text-muted"),
                    html.H4(id='prophet-card-upgraded-pred', children="€0.00", className="text-warning fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=6, md=3),
    ], className="mb-2"),

    # --- Controls Row ---
    dbc.Row([
        dbc.Col([
            html.Label("Days to Predict:", className="fw-bold text-white"),
            dbc.Input(id='prophet-forecast-days', type='number', value=30, min=7, max=365, step=1)
        ], width=12, md=6, style={'zIndex': '1000', 'position': 'relative'}),

        dbc.Col([
            html.Br(),
            dbc.Button("Generate Future Forecast", id='btn-run-prophet', color="primary", className="w-100")
        ], width=12, md=6, style={'zIndex': '1000', 'position': 'relative'}),

    ], className="mb-4 glass-container",
        style={'overflow': 'visible', 'position': 'relative', 'zIndex': '1000'}),

    # --- Graph Row ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Loading(
                        id="loading-prophet",
                        type="default",
                        children=dcc.Graph(id='prophet-graph', style={'height': '500px'})
                    )
                ])
            ], className="shadow-sm glass-container", style={'zIndex': '1', 'position': 'relative'})
        ], width=12)
    ])

], fluid=True)


# =============================================================================
# 2. HELPER FUNCTIONS
# =============================================================================

# --- OUTLIER REMOVAL (IQR METHOD) ---
def remove_outliers_iqr(df):
    """
    Removes rows where Revenue is an outlier using the Interquartile Range (IQR) method.
    Only applies if dataset has enough points (>20).
    """
    if len(df) < 20:
        return df

    Q1 = df['Revenue'].quantile(0.25)
    Q3 = df['Revenue'].quantile(0.75)
    IQR = Q3 - Q1

    # Define bounds (1.5 is standard)
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    # Filter
    df_clean = df[(df['Revenue'] >= lower_bound) & (df['Revenue'] <= upper_bound)]
    return df_clean


# --- FUTURE PREDICTION LOGIC ---
def get_prophet_revenue_prediction(df_in, days_to_predict):
    df = df_in.copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    if df.empty: return None

    # --- STEP 1: REMOVE OUTLIERS ---
    # We remove outliers from the raw transactions BEFORE aggregating daily sums
    df = remove_outliers_iqr(df)

    global_max_date = df['Date'].max()
    types = ['new', 'renewed', 'upgraded']
    results = {}
    history_list = []
    future_dates = None

    for sub_type in types:
        type_df = df[df['Subscription_Type'] == sub_type].copy()

        # Aggregate Daily
        daily_df = type_df.groupby(pd.Grouper(key='Date', freq='D'))['Revenue'].sum().reset_index()
        daily_df = daily_df.rename(columns={'Date': 'ds', 'Revenue': 'y'})

        if not daily_df.empty:
            full_range = pd.date_range(start=daily_df['ds'].min(), end=global_max_date, freq='D')
            daily_df = daily_df.set_index('ds').reindex(full_range, fill_value=0).reset_index().rename(
                columns={'index': 'ds'})

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
        preds = np.maximum(future_forecast['yhat'].values, 0)
        results[sub_type] = preds

        if future_dates is None:
            future_dates = future_forecast['ds'].values

    if not history_list: return None
    full_hist_df = pd.concat(history_list)
    hist_pivot = full_hist_df.pivot(index='ds', columns='Subscription_Type', values='y').fillna(0)

    for col in types:
        if col not in hist_pivot.columns: hist_pivot[col] = 0

    hist_pivot['total'] = hist_pivot['new'] + hist_pivot['renewed'] + hist_pivot['upgraded']
    hist_df = hist_pivot.reset_index().rename(columns={'ds': 'Date'})

    preds_new = results.get('new', np.zeros(int(days_to_predict)))
    preds_renewed = results.get('renewed', np.zeros(int(days_to_predict)))
    preds_upgraded = results.get('upgraded', np.zeros(int(days_to_predict)))
    preds_total = preds_new + preds_renewed + preds_upgraded

    return {
        'sums': (sum(preds_total), sum(preds_new), sum(preds_renewed), sum(preds_upgraded)),
        'dates': future_dates,
        'preds': (preds_total, preds_new, preds_renewed, preds_upgraded),
        'history': hist_df
    }


# =============================================================================
# 3. CALLBACK REGISTRATION
# =============================================================================
def register_prophet_callbacks(app):
    # --- CALLBACK: FUTURE FORECAST ---
    @app.callback(
        [Output('prophet-card-total-pred', 'children'),
         Output('prophet-card-new-pred', 'children'),
         Output('prophet-card-renewed-pred', 'children'),
         Output('prophet-card-upgraded-pred', 'children'),
         Output('prophet-graph', 'figure'),
         Output('prophet-card-total-title', 'children'),
         Output('prophet-card-new-title', 'children'),
         Output('prophet-card-renewed-title', 'children'),
         Output('prophet-card-upgraded-title', 'children')],
        [Input('btn-run-prophet', 'n_clicks')],
        [State('global-data-store', 'data'),
         State('prophet-forecast-days', 'value')]
    )
    def update_prophet_forecast(n_clicks, data, days):
        empty_res = ("-", "-", "-", "-", go.Figure().update_layout(title="No Data"),
                     "Total Revenue", "New Revenue", "Renewed Revenue", "Upgraded Revenue")

        if not data: return empty_res
        if n_clicks is None:
            return "€0.00", "€0.00", "€0.00", "€0.00", go.Figure().update_layout(
                title="Click 'Generate Future Forecast' to see predictions",
                xaxis={'visible': False}, yaxis={'visible': False}
            ), "Total Revenue", "New Revenue", "Renewed Revenue", "Upgraded Revenue"

        df = pd.DataFrame(data)

        # Data Cleaning
        if 'lastPaymentReceivedOn' in df.columns:
            df['Date'] = pd.to_datetime(df['lastPaymentReceivedOn'], errors='coerce')
        elif 'dateUTC' in df.columns:
            df['Date'] = pd.to_datetime(df['dateUTC'], errors='coerce')
        elif 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        else:
            return empty_res

        if 'lastAmountPaidEUR' in df.columns:
            df['Revenue'] = pd.to_numeric(df['lastAmountPaidEUR'], errors='coerce').fillna(0)
        elif 'Revenue' in df.columns:
            df['Revenue'] = pd.to_numeric(df['Revenue'], errors='coerce').fillna(0)
        else:
            df['Revenue'] = 0

        if 'Subscription_Type' in df.columns:
            df['Subscription_Type'] = df['Subscription_Type'].astype(str)
        elif 'type' in df.columns:
            df['Subscription_Type'] = df['type'].astype(str)
        else:
            return empty_res

        # Filtering
        df['Subscription_Type'] = df['Subscription_Type'].str.lower().str.strip()
        valid_types = ['new', 'renewed', 'upgraded']
        mask_type = df['Subscription_Type'].isin(valid_types)
        mask_date = df['Date'].notna()
        df_clean = df[mask_type & mask_date].copy()

        # Run Prediction (Outliers are removed inside the function)
        result = get_prophet_revenue_prediction(df_clean, days)

        if not result: return empty_res

        (sum_total, sum_new, sum_renewed, sum_upgraded) = result['sums']
        f_dates = result['dates']
        (p_total, p_new, p_renewed, p_upgraded) = result['preds']
        hist_df = result['history']

        def fmt(val):
            return f"€{val:,.2f}"

        # Generate Graph
        fig = go.Figure()

        def add_traces(hist_col, pred_vals, name, color, is_total=False):
            opacity = 1 if is_total else 0
            show_legend = True if is_total else False
            pred_color = "#dc3545" if is_total else color

            fig.add_trace(go.Scatter(
                x=hist_df['Date'], y=hist_df[hist_col], mode='lines', name=f"{name} (Actual)",
                line=dict(color=color, width=3), opacity=opacity, showlegend=show_legend, hoverinfo='x+y+name'
            ))

            fig.add_trace(go.Scatter(
                x=f_dates, y=pred_vals, mode='lines', name=f"{name} (Predicted)",
                line=dict(color=pred_color, width=3, dash='dash'), opacity=opacity, showlegend=show_legend,
                hoverinfo='x+y+name'
            ))

            if len(pred_vals) > 0:
                fig.add_trace(go.Scatter(
                    x=[hist_df['Date'].iloc[-1], f_dates[0]],
                    y=[hist_df[hist_col].iloc[-1], pred_vals[0]],
                    mode='lines', showlegend=False,
                    line=dict(color=pred_color, width=3, dash='dash'), opacity=opacity, hoverinfo='skip'
                ))

        add_traces('total', p_total, "Total", "#0d6efd", is_total=True)
        add_traces('new', p_new, "New", "#198754", is_total=False)
        add_traces('renewed', p_renewed, "Renewed", "#0dcaf0", is_total=False)
        add_traces('upgraded', p_upgraded, "Upgraded", "#ffc107", is_total=False)

        fig.update_layout(
            title=f"Daily Revenue Forecast (Prophet) - {days} Days",
            xaxis_title="Date", yaxis_title="Revenue (€)",
            template="plotly_white", hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        title_suffix = f"(Next {days} Days)"
        return (fmt(sum_total), fmt(sum_new), fmt(sum_renewed), fmt(sum_upgraded), fig,
                f"Total Revenue {title_suffix}", f"New Revenue {title_suffix}",
                f"Renewed Revenue {title_suffix}", f"Upgraded Revenue {title_suffix}")