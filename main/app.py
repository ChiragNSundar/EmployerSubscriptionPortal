# dashboard/app.py

import pandas as pd
import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc

# --- IMPORT DATA LOADING ---
from Data.get_localsqldata import load_data

# --- IMPORT PAGES ---
from subscription_pages.daily_overview import layout as page1_layout, register_callbacks as register_page1_callbacks
from subscription_pages.monthly_overview import layout as page2_layout, register_callbacks as register_page2_callbacks
from subscription_pages.pie_chart import layout as page3_layout, register_callbacks as register_page3_callbacks
from subscription_pages.daily_revenue_bar_chart import layout as page4_layout, \
    register_callbacks as register_page4_callbacks
from subscription_pages.monthly_revenue_bar_chart import layout as page5_layout, \
    register_callbacks as register_page5_callbacks
from subscription_pages.daily_revenue_comparison import layout as page6_layout, \
    register_callbacks as register_page6_callbacks
from subscription_pages.monthly_revenue_comparison import layout as page7_layout, \
    register_callbacks as register_page7_callbacks

# --- INITIALIZE APP ---
# Added FONT_AWESOME to external_stylesheets for the icons
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
    title="Employer Subscription Dashboard"
)

# --- FETCH DATA ON STARTUP ---
print("🚀 Loading data from Local SQL...")
try:
    df = load_data()

    # CHECK 1: Ensure df is not None and not empty
    if df is not None and not df.empty:

        # CHECK 2: Handle Date Serialization
        if 'Date' in df.columns:
            df['Date'] = df['Date'].astype(str)

        # Optional: Convert other datetime columns to strings
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


# --- NAVBAR COMPONENT (Redesigned) ---
def create_navbar():
    return dbc.Navbar(
        dbc.Container([
            # Brand / Logo (Icon + Text)
            html.A(
                dbc.Row([
                    # Using a chart icon similar to the reference
                    dbc.Col(html.I(className="fas fa-chart-line fa-lg me-2", style={"color": "#00d2ff"})),
                    dbc.Col(dbc.NavbarBrand("Employer Subscription Dashboard", className="ms-2")),
                ], align="center", className="g-0"),
                href="/",
                style={"textDecoration": "none"},
            ),

            # Toggler for mobile responsiveness
            dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),

            # Collapsible Links
            dbc.Collapse(
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink("Daily Overview", href="/page-1")),
                    dbc.NavItem(dbc.NavLink("Monthly Overview", href="/page-2")),
                    dbc.NavItem(dbc.NavLink("Pie Chart", href="/page-3")),

                    # Dropdown for Revenue Analytics (Grouping pages 4, 5, 6, 7)
                    dbc.DropdownMenu(
                        children=[
                            dbc.DropdownMenuItem("Daily Revenue Bar", href="/page-4"),
                            dbc.DropdownMenuItem("Monthly Revenue Bar", href="/page-5"),
                            dbc.DropdownMenuItem(divider=True),
                            dbc.DropdownMenuItem("Daily Comparison", href="/page-6"),
                            dbc.DropdownMenuItem("Monthly Comparison", href="/page-7"),
                        ],
                        nav=True,
                        in_navbar=True,
                        label="Revenue Analytics",
                    ),
                ], className="ms-auto", navbar=True),
                id="navbar-collapse",
                navbar=True,
            ),
        ]),
        color="dark",
        dark=True,
        className="mb-4 sticky-top",  # Sticky top ensures it stays visible
        expand="lg"
    )


# --- APP LAYOUT ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='global-data-store', data=initial_data),  # Data is stored here

    # Navbar
    create_navbar(),

    # Page Content Container
    dbc.Container([
        html.Div(id='page-content')
    ], fluid=True)
])

# --- REGISTER PAGE CALLBACKS ---
register_page1_callbacks(app)
register_page2_callbacks(app)
register_page3_callbacks(app)
register_page4_callbacks(app)
register_page5_callbacks(app)
register_page6_callbacks(app)
register_page7_callbacks(app)


# --- NAVBAR TOGGLE CALLBACK ---
# This is required for the mobile menu to open/close
@callback(
    Output("navbar-collapse", "is_open"),
    [Input("navbar-toggler", "n_clicks")],
    [State("navbar-collapse", "is_open")],
)
def toggle_navbar_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


# --- ROUTING CALLBACK ---
@callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/page-1':
        return page1_layout
    elif pathname == '/page-2':
        return page2_layout
    elif pathname == '/page-3':
        return page3_layout
    elif pathname == '/page-4':
        return page4_layout
    elif pathname == '/page-5':
        return page5_layout
    elif pathname == '/page-6':
        return page6_layout
    elif pathname == '/page-7':
        return page7_layout
    else:
        # Default page
        return page1_layout


if __name__ == '__main__':
    app.run(port=8050, debug=True)