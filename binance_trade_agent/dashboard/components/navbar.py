"""
Navigation bar component for Dash dashboard
"""

import dash_bootstrap_components as dbc
from dash import html, dcc


def create_navbar(pages: dict) -> dbc.Navbar:
    """Create the main navigation bar
    
    Args:
        pages: Dictionary of page routes and metadata
        
    Returns:
        dbc.Navbar: Bootstrap navbar component
    """
    
    # Create nav links from pages
    nav_links = []
    for path, page_info in pages.items():
        nav_links.append(
            dbc.NavLink(
                [
                    html.Span(page_info['icon'], style={'marginRight': '0.5rem'}),
                    page_info['name']
                ],
                href=path,
                active="exact",
                style={
                    'color': '#f4f2ee',
                    'fontWeight': '500',
                    'margin': '0 0.5rem'
                }
            )
        )
    
    navbar = dbc.Navbar(
        dbc.Container([
            # Brand/Logo
            dbc.NavbarBrand(
                [
                    html.Span("📈 ", style={'marginRight': '0.5rem', 'fontSize': '1.25rem'}),
                    "Trading Agent"
                ],
                href="/",
                style={
                    'color': '#ff914d',
                    'fontWeight': 'bold',
                    'fontSize': '1.3rem'
                }
            ),
            
            # Navigation toggle for mobile
            dbc.NavbarToggler(id="navbar-toggler"),
            
            # Collapsible navbar content
            dbc.Collapse(
                dbc.Nav(
                    nav_links,
                    className="ms-auto",
                    navbar=True,
                    pills=True
                ),
                id="navbar-collapse",
                navbar=True,
            ),
        ], fluid=True),
        color="#23242a",
        dark=True,
        sticky="top",
        style={
            'borderBottom': '1px solid rgba(255, 145, 77, 0.2)',
            'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.3)',
            'backgroundColor': '#23242a'
        }
    )
    
    return navbar


def create_metric_card(
    label: str,
    value: str,
    delta: str = None,
    icon: str = None,
    status: str = "primary",
    help_text: str = None
) -> dbc.Card:
    """Create a metric card component
    
    Args:
        label: Card label/title
        value: Main metric value to display
        delta: Optional delta/change value (e.g., "+5.2%")
        icon: Optional emoji icon
        status: Status type ('primary', 'success', 'danger', 'warning', 'info')
        help_text: Optional help tooltip text
        
    Returns:
        dbc.Card: Styled metric card
    """
    
    # Status color mapping
    status_colors = {
        'primary': '#ff914d',
        'success': '#27ae60',
        'danger': '#e74c3c',
        'warning': '#f39c12',
        'info': '#3498db'
    }
    
    border_color = status_colors.get(status, '#ff914d')
    
    # Build card body content
    card_content = [
        html.Div([
            html.Span(label, style={
                'fontSize': '0.875rem',
                'color': '#b8b4b0',
                'fontWeight': '500',
                'textTransform': 'uppercase',
                'letterSpacing': '0.5px',
                'marginRight': '0.25rem'
            }),
            html.Span(icon, style={'marginLeft': '0.25rem'}) if icon else None
        ], className="metric-label"),
        
        html.Div(value, style={
            'fontSize': '1.75rem',
            'fontWeight': '700',
            'color': '#f4f2ee',
            'lineHeight': '1.2',
            'marginTop': '0.25rem'
        }),
    ]
    
    # Add delta if provided
    if delta:
        delta_color = '#27ae60' if '+' in delta or delta.startswith('>') else '#e74c3c' if '-' in delta or delta.startswith('<') else '#f4f2ee'
        card_content.append(
            html.Div(delta, style={
                'fontSize': '0.875rem',
                'color': delta_color,
                'fontWeight': '500',
                'marginTop': '0.5rem'
            })
        )
    
    card = dbc.Card(
        dbc.CardBody(card_content),
        style={
            'border': f'1px solid rgba(255, 145, 77, 0.2)',
            'borderLeft': f'3px solid {border_color}',
            'backgroundColor': '#23242a',
            'minHeight': '120px',
            'display': 'flex',
            'flexDirection': 'column',
            'justifyContent': 'center',
            'boxShadow': '0 2px 8px rgba(0, 0, 0, 0.2)',
            'transition': 'all 0.2s ease',
            'cursor': 'pointer'
        }
    )
    
    # Wrap with tooltip if help_text provided
    if help_text:
        return dbc.Tooltip(
            card,
            help_text,
            placement="top"
        )
    
    return card
