import pandas as pd
import numpy as np
import plotly.graph_objs as go
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
# Import BOTH models
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

# --- 1. LAYOUT DEFINITION ---
layout = dbc.Container([
    html.H3("AI Forecasting: Trend vs. Seasonality", className="my-4 text-center"),

    # --- Controls Row ---
    dbc.Row([
        # Metric Selector
        dbc.Col([
            html.Label("Select Metric:", className="fw-bold"),
            dcc.Dropdown(
                id='forecast-metric',
                options=[
                    {'label': 'Subscription Volume (Count)', 'value': 'count'},
                    {'label': 'Revenue (€)', 'value': 'revenue'}
                ],
                value='count',
                clearable=False
            )
        ], width=12, md=3),

        # Model Selector (NEW)
        dbc.Col([
            html.Label("Select AI Model:", className="fw-bold"),
            dcc.Dropdown(
                id='forecast-model-type',
                options=[
                    {'label': 'Compare Both', 'value': 'both'},
                    {'label': 'Random Forest (Complex/Seasonal)', 'value': 'rf'},
                    {'label': 'Linear Regression (Simple Trend)', 'value': 'lr'}
                ],
                value='both',  # Default to showing both
                clearable=False
            )
        ], width=12, md=4),

        # Days Input
        dbc.Col([
            html.Label("Days to Predict:", className="fw-bold"),
            dbc.Input(id='forecast-days', type='number', value=30, min=7, max=365, step=1)
        ], width=12, md=3),

        # Run Button
        dbc.Col([
            html.Br(),
            dbc.Button("Run", id='btn-run-forecast', color="primary", className="w-100")
        ], width=12, md=2),

    ], className="mb-4 glass-container", style={'position': 'relative', 'zIndex': '1000'}),

    # --- Graph Row ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Loading(
                        id="loading-forecast",
                        type="default",
                        children=dcc.Graph(id='forecast-graph', style={'height': '600px'})
                    )
                ])
            ], className="shadow-sm glass-container")
        ], width=12)
    ])
], fluid=True)


# --- 2. CALLBACK REGISTRATION ---
def register_callbacks(app):
    @app.callback(
        Output('forecast-graph', 'figure'),
        [Input('btn-run-forecast', 'n_clicks')],
        [State('global-data-store', 'data'),
         State('forecast-metric', 'value'),
         State('forecast-days', 'value'),
         State('forecast-model-type', 'value')]  # Added Model State
    )
    def update_forecast(n_clicks, data, metric, days, model_type):
        if not data:
            return go.Figure().update_layout(title="No Data Available")
        if n_clicks is None:
            return go.Figure().update_layout(
                title="Click 'Run' to generate predictions",
                xaxis={'visible': False}, yaxis={'visible': False}
            )

        df = pd.DataFrame(data)

        # --- 2. DATA CLEANING (Standard) ---
        if 'dateUTC' in df.columns:
            df['dateUTC'] = pd.to_datetime(df['dateUTC'], errors='coerce')
        if 'lastPaymentReceivedOn' in df.columns:
            df['lastPaymentReceivedOn'] = pd.to_datetime(df['lastPaymentReceivedOn'], errors='coerce')

        valid_types = ['New', 'Renewed', 'Upgraded']
        if 'type' in df.columns and 'lastPaymentReceivedOn' in df.columns and 'dateUTC' in df.columns:
            mask = (df['type'].isin(valid_types) & (df['lastPaymentReceivedOn'] >= df['dateUTC']))
            df_filtered = df[mask].copy()
        else:
            df_filtered = df.copy()

        if 'dateUTC' in df_filtered.columns:
            df_filtered['Date'] = df_filtered['dateUTC']
        elif 'Date' in df_filtered.columns:
            df_filtered['Date'] = pd.to_datetime(df_filtered['Date'], errors='coerce')

        if 'lastAmountPaidEUR' in df_filtered.columns:
            df_filtered['Revenue'] = pd.to_numeric(df_filtered['lastAmountPaidEUR'], errors='coerce').fillna(0)
        else:
            df_filtered['Revenue'] = 0

        # --- 3. PREPARE DATA ---
        if metric == 'revenue':
            df_grouped = df_filtered.groupby(pd.Grouper(key='Date', freq='D'))['Revenue'].sum().reset_index()
            y_col = 'Revenue'
            title_text = f"Revenue Forecast ({days} Days)"
        else:
            df_grouped = df_filtered.groupby(pd.Grouper(key='Date', freq='D')).size().reset_index(name='count')
            y_col = 'count'
            title_text = f"Subscription Volume Forecast ({days} Days)"

        df_grouped = df_grouped.dropna()
        if df_grouped.empty:
            return go.Figure().update_layout(title="No data matches the Paid Subscription criteria")

        # --- PREPARE FUTURE DATES (Common for both models) ---
        last_date = df_grouped['Date'].max()
        future_dates = [last_date + pd.Timedelta(days=x) for x in range(1, int(days) + 1)]

        # Initialize Figure
        fig = go.Figure()

        # Add Actual History (Always shown)
        fig.add_trace(go.Scatter(
            x=df_grouped['Date'],
            y=df_grouped[y_col],
            mode='markers',
            name='Actual History',
            marker=dict(color='black', size=5, opacity=0.4)
        ))

        # ============================================================
        # MODEL 1: LINEAR REGRESSION (Simple Trend)
        # ============================================================
        if model_type in ['lr', 'both']:
            # 1. Feature Engineering (Ordinal Date)
            df_grouped['date_ordinal'] = df_grouped['Date'].map(pd.Timestamp.toordinal)

            X_lr = df_grouped[['date_ordinal']]
            y_lr = df_grouped[y_col]

            # 2. Train
            lr_model = LinearRegression()
            lr_model.fit(X_lr, y_lr)

            # 3. Predict
            future_ordinals_df = pd.DataFrame({'date_ordinal': [d.toordinal() for d in future_dates]})
            lr_predictions = lr_model.predict(future_ordinals_df)
            lr_predictions = [max(0, p) for p in lr_predictions]  # No negative

            # 4. Plot (Red Line)
            fig.add_trace(go.Scatter(
                x=future_dates,
                y=lr_predictions,
                mode='lines',
                name='Linear Trend',
                line=dict(color='#dc3545', width=3, dash='dot')  # Red Dotted
            ))

        # ============================================================
        # MODEL 2: RANDOM FOREST (Complex/Seasonal)
        # ============================================================
        if model_type in ['rf', 'both']:
            # 1. Feature Engineering (Seasonality)
            df_grouped['day_of_week'] = df_grouped['Date'].dt.dayofweek
            df_grouped['day_of_month'] = df_grouped['Date'].dt.day
            df_grouped['trend_index'] = np.arange(len(df_grouped))

            features_rf = ['day_of_week', 'day_of_month', 'trend_index']
            X_rf = df_grouped[features_rf]
            y_rf = df_grouped[y_col]

            # 2. Train
            rf_model = RandomForestRegressor(n_estimators=200, random_state=42)
            rf_model.fit(X_rf, y_rf)

            # 3. Predict
            future_rf_df = pd.DataFrame({'Date': future_dates})
            future_rf_df['day_of_week'] = future_rf_df['Date'].dt.dayofweek
            future_rf_df['day_of_month'] = future_rf_df['Date'].dt.day

            last_index = df_grouped['trend_index'].max()
            future_rf_df['trend_index'] = np.arange(last_index + 1, last_index + 1 + len(future_dates))

            rf_predictions = rf_model.predict(future_rf_df[features_rf])
            rf_predictions = [max(0, p) for p in rf_predictions]

            # 4. Plot (Blue Line)
            fig.add_trace(go.Scatter(
                x=future_dates,
                y=rf_predictions,
                mode='lines',
                name='AI Seasonal (RF)',
                line=dict(color='#0d6efd', width=3, dash='dash')  # Blue Dashed
            ))

        # --- FINAL LAYOUT ---
        fig.update_layout(
            title=title_text,
            xaxis_title="Date",
            yaxis_title=metric.capitalize(),
            template="plotly_white",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        return fig