import pandas as pd
import numpy as np
import plotly.graph_objs as go
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from sklearn.linear_model import LinearRegression

# --- 1. LAYOUT DEFINITION ---
layout = dbc.Container([
    html.H3("AI Forecasting: Future Trends", className="my-4 text-center"),

    # --- Controls Row ---
    dbc.Row([
        # Metric Selector
        dbc.Col([
            html.Label("Select Metric to Predict:", className="fw-bold"),
            dcc.Dropdown(
                id='forecast-metric',
                options=[
                    {'label': 'Subscription Volume (Count)', 'value': 'count'},
                    {'label': 'Revenue (€)', 'value': 'revenue'}
                ],
                value='count',
                clearable=False
            )
        ], width=12, md=4),

        # Forecast Horizon Input
        dbc.Col([
            html.Label("Days to Predict:", className="fw-bold"),
            dbc.Input(id='forecast-days', type='number', value=30, min=7, max=365, step=1)
        ], width=12, md=3),

        # Run Button
        dbc.Col([
            html.Br(),
            dbc.Button("Run Forecast", id='btn-run-forecast', color="primary", className="w-100")
        ], width=12, md=2),

    ], className="mb-4 glass-container", style={'position': 'relative', 'zIndex': '1000'}),

    # --- Graph Row ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    # Loading Spinner because ML takes a few seconds
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
         State('forecast-days', 'value')]
    )
    def update_forecast(n_clicks, data, metric, days):
        # 1. Handle Empty Data or Initial Load
        if not data:
            return go.Figure().update_layout(title="No Data Available")
        if n_clicks is None:
            return go.Figure().update_layout(
                title="Click 'Run Forecast' to generate predictions",
                xaxis={'visible': False}, yaxis={'visible': False}
            )

        df = pd.DataFrame(data)

        # --- 2. DATA CLEANING & MAPPING ---

        # A. Convert Date Columns to DateTime objects
        if 'dateUTC' in df.columns:
            df['dateUTC'] = pd.to_datetime(df['dateUTC'], errors='coerce')

        if 'lastPaymentReceivedOn' in df.columns:
            df['lastPaymentReceivedOn'] = pd.to_datetime(df['lastPaymentReceivedOn'], errors='coerce')

        # B. Apply SQL Logic Filtering
        # SQL: WHERE type IN ('New', 'Renewed', 'Upgraded') AND lastPaymentReceivedOn >= dateUTC
        valid_types = ['New', 'Renewed', 'Upgraded']

        # Ensure columns exist before filtering
        if 'type' in df.columns and 'lastPaymentReceivedOn' in df.columns and 'dateUTC' in df.columns:
            mask = (
                    df['type'].isin(valid_types) &
                    (df['lastPaymentReceivedOn'] >= df['dateUTC'])
            )
            df_filtered = df[mask].copy()
        else:
            # Fallback: If columns missing, use raw data (or handle error)
            df_filtered = df.copy()

        # C. Apply Column Mapping & Revenue Definition
        if 'dateUTC' in df_filtered.columns:
            df_filtered['Date'] = df_filtered['dateUTC']
        elif 'Date' in df_filtered.columns:
            df_filtered['Date'] = pd.to_datetime(df_filtered['Date'], errors='coerce')

        # Revenue Logic: Use lastAmountPaidEUR
        if 'lastAmountPaidEUR' in df_filtered.columns:
            df_filtered['Revenue'] = pd.to_numeric(df_filtered['lastAmountPaidEUR'], errors='coerce').fillna(0)
        else:
            df_filtered['Revenue'] = 0

        # --- 3. PREPARE DATA FOR REGRESSION ---

        # Group by Day
        if metric == 'revenue':
            df_grouped = df_filtered.groupby(pd.Grouper(key='Date', freq='D'))['Revenue'].sum().reset_index()
            y_col = 'Revenue'
            title_text = f"Revenue Forecast (Based on Paid Subscriptions) - {days} Days"
        else:
            df_grouped = df_filtered.groupby(pd.Grouper(key='Date', freq='D')).size().reset_index(name='count')
            y_col = 'count'
            title_text = f"Subscription Volume Forecast (Paid Only) - {days} Days"

        # Remove empty rows
        df_grouped = df_grouped.dropna()

        if df_grouped.empty:
            return go.Figure().update_layout(title="No data matches the Paid Subscription criteria")

        # --- 4. FEATURE ENGINEERING ---

        # Convert Date to Ordinal (Integer) so the model can understand it
        df_grouped['date_ordinal'] = df_grouped['Date'].map(pd.Timestamp.toordinal)

        X = df_grouped[['date_ordinal']]
        y = df_grouped[y_col]

        # --- 5. TRAIN MODEL ---
        model = LinearRegression()
        model.fit(X, y)

        # --- 6. PREDICT FUTURE (FIXED) ---
        last_date = df_grouped['Date'].max()
        future_dates = [last_date + pd.Timedelta(days=x) for x in range(1, int(days) + 1)]

        # FIX: Create a DataFrame with the SAME column name as X ('date_ordinal')
        # This prevents the "X does not have valid feature names" warning
        future_ordinals_df = pd.DataFrame({
            'date_ordinal': [d.toordinal() for d in future_dates]
        })

        predictions = model.predict(future_ordinals_df)

        # Business Logic: No negative predictions
        predictions = [max(0, p) for p in predictions]
        print(type(predictions))

        forecast_df = pd.DataFrame({
            'Date': future_dates,
            'Prediction': predictions
        })

        # --- 7. PLOT ---
        fig = go.Figure()

        # Actual Data
        fig.add_trace(go.Scatter(
            x=df_grouped['Date'],
            y=df_grouped[y_col],
            mode='markers',
            name='Actual History',
            marker=dict(color='black', size=5, opacity=0.5)
        ))

        # Prediction Line
        fig.add_trace(go.Scatter(
            x=forecast_df['Date'],
            y=forecast_df['Prediction'],
            mode='lines',
            name='Trend Prediction',
            line=dict(color='#0d6efd', width=3, dash='dash')
        ))

        fig.update_layout(
            title=title_text,
            xaxis_title="Date",
            yaxis_title=metric.capitalize(),
            template="plotly_white",
            hovermode="x unified"
        )

        return fig