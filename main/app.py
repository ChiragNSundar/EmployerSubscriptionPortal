# job_portal_dashboard/app.py

import pandas as pd
import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc

# --- IMPORT DATA LOADING ---
from Data.get_localsqldata import load_data

# --- IMPORT PAGES ---
from subscription_pages.daily_overview import layout as page1_layout, register_callbacks as register_page1_callbacks
from subscription_pages.monthly_overview import layout as page2_layout, register_callbacks as register_page2_callbacks
# ... (keep other page imports as they were) ...

# --- INITIALIZE APP ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

# --- FETCH DATA ON STARTUP ---
print("🚀 Loading data from Local SQL...")
try:
    df = load_data()

    # CHECK 1: Ensure df is not None and not empty
    if df is not None and not df.empty:

        # CHECK 2: Handle Date Serialization (Use the correct column name 'Date')
        if 'Date' in df.columns:
            df['Date'] = df['Date'].astype(str)

        # Optional: Convert other datetime columns to strings to prevent JSON errors
        # (Pandas datetimes cannot be stored in dcc.Store directly)
        for col in df.select_dtypes(include=['datetime64']).columns:
            df[col] = df[col].astype(str)

        initial_data = df.to_dict('records')
        print(f"✅ Data loaded successfully: {len(df)} rows.")
    else:
        initial_data = []
        print("⚠️ Data is empty or None.")

except Exception as e:
    print(f"❌ Error loading initial data: {e}")
    initial_data = []


# --- NAVBAR COMPONENT ---
def create_navbar():
    return dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Daily Overview", href="/page-1")),
            dbc.NavItem(dbc.NavLink("Monthly Overview", href="/page-2")),
            # ... (keep your other links) ...
        ],
        brand="Employer Subscription Dashboard",
        brand_href="/",
        color="dark",
        dark=True,
        className="mb-4"
    )


# --- APP LAYOUT ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='global-data-store', data=initial_data),  # Data is stored here
    create_navbar(),
    html.Div(id='page-content')
])

# --- REGISTER CALLBACKS ---
register_page1_callbacks(app)
register_page2_callbacks(app)


# ... (register other pages) ...

# --- ROUTING CALLBACK ---
@callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/page-1':
        return page1_layout
    # ... (handle other pages) ...
    elif pathname == '/page-2':
        return page2_layout
    else:
        return page1_layout


if __name__ == '__main__':
    app.run(port=8050, debug=True)