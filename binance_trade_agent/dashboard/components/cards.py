"""
Reusable Card Components for Dash Dashboard
Phase 1: Design System Foundation

Card Types:
- KPI Cards: Fixed height, large number, tiny label, icon + tag
- Content Cards: Title, optional subtitle & filter area, then content
- Alert Cards: Stronger accent border/background, icon, short body text
- Status Pills: Connected/Degraded/Disconnected states
"""

from dash import html
import dash_bootstrap_components as dbc
from typing import Optional, List, Union


def create_kpi_card(
    label: str,
    value: str,
    delta: Optional[str] = None,
    delta_type: str = "neutral",
    icon: Optional[str] = None,
    tag: Optional[str] = None,
    status: str = "primary",
    help_text: Optional[str] = None,
) -> html.Div:
    """Create a KPI Card component

    Args:
        label: Card label/title (uppercase, small text)
        value: Main metric value to display (large, prominent)
        delta: Optional delta/change value (e.g., "+5.2%")
        delta_type: 'positive', 'negative', or 'neutral'
        icon: Optional emoji icon to display with label
        tag: Optional tag text (e.g., "Real-time", "24h")
        status: Status type ('primary', 'success', 'danger', 'warning', 'info')
        help_text: Optional help tooltip text

    Returns:
        html.Div: Styled KPI card
    """

    # Build header with label, icon, and optional tag
    header_content = [
        html.Span(
            [
                label,
                html.Span(f" {icon}", style={"marginLeft": "4px"}) if icon else None,
            ],
            className="kpi-card__label",
        ),
    ]

    if tag:
        header_content.append(html.Span(tag, className="kpi-card__tag"))

    # Build delta display
    delta_element = None
    if delta:
        delta_element = html.Div(
            delta,
            className=f"kpi-card__delta {delta_type}",
        )

    card = html.Div(
        [
            html.Div(header_content, className="kpi-card__header"),
            html.Div(value, className="kpi-card__value"),
            delta_element,
        ],
        className=f"kpi-card {status}",
    )

    # Wrap with tooltip if help_text provided
    if help_text:
        return html.Div(
            [
                card,
                dbc.Tooltip(help_text, target=card, placement="top"),
            ]
        )

    return card


def create_content_card(
    title: str,
    children: Union[html.Div, List],
    subtitle: Optional[str] = None,
    icon: Optional[str] = None,
    filters: Optional[List] = None,
    footer: Optional[str] = None,
    body_class: str = "",
) -> html.Div:
    """Create a Content Card component

    Args:
        title: Card title
        children: Card body content
        subtitle: Optional subtitle text
        icon: Optional emoji icon for title
        filters: Optional list of filter components for header
        footer: Optional footer text
        body_class: Additional CSS class for body ('compact', 'no-padding')

    Returns:
        html.Div: Styled content card
    """

    # Build header
    title_content = []
    if icon:
        title_content.append(html.Span(icon))
    title_content.append(title)

    header_left = html.Div(
        [
            html.H5(title_content, className="content-card__title"),
            html.P(subtitle, className="content-card__subtitle") if subtitle else None,
        ]
    )

    header_right = None
    if filters:
        header_right = html.Div(filters, className="content-card__filters")

    header = html.Div(
        [header_left, header_right] if header_right else [header_left],
        className="content-card__header",
    )

    # Build body
    body_className = "content-card__body"
    if body_class == "compact":
        body_className = "content-card__body content-card__body--compact"
    elif body_class == "no-padding":
        body_className = "content-card__body content-card__body--no-padding"

    body = html.Div(children, className=body_className)

    # Build footer if provided
    footer_element = None
    if footer:
        footer_element = html.Div(footer, className="content-card__footer")

    return html.Div(
        [header, body, footer_element] if footer_element else [header, body],
        className="content-card",
    )


def create_alert_card(
    title: str,
    message: str,
    icon: str = "ℹ️",
    status: str = "info",
) -> html.Div:
    """Create an Alert Card component

    Args:
        title: Alert title
        message: Alert message/description
        icon: Emoji icon to display
        status: Status type ('success', 'danger', 'warning', 'info')

    Returns:
        html.Div: Styled alert card
    """

    return html.Div(
        [
            html.Div(icon, className="alert-card__icon"),
            html.Div(
                [
                    html.H6(title, className="alert-card__title"),
                    html.P(message, className="alert-card__message"),
                ],
                className="alert-card__content",
            ),
        ],
        className=f"alert-card {status}",
    )


def create_status_pill(
    label: str,
    status: str = "active",
) -> html.Span:
    """Create a Status Pill component

    Args:
        label: Status label text
        status: Status type ('connected', 'degraded', 'disconnected', 'active', 'inactive')

    Returns:
        html.Span: Styled status pill
    """

    return html.Span(label, className=f"status-pill {status}")


def create_signal_badge(
    signal: str,
) -> html.Div:
    """Create a Signal Badge component

    Args:
        signal: Signal type ('BUY', 'SELL', 'NEUTRAL')

    Returns:
        html.Div: Styled signal badge
    """

    signal_upper = signal.upper()
    signal_class = {
        "BUY": "buy",
        "SELL": "sell",
        "NEUTRAL": "neutral",
    }.get(signal_upper, "neutral")

    return html.Div(signal_upper, className=f"signal-badge {signal_class}")


def create_confidence_bar(
    confidence: float,
    signal_type: str = "neutral",
) -> html.Div:
    """Create a Confidence Bar component

    Args:
        confidence: Confidence value (0-100)
        signal_type: Type of signal ('bullish', 'bearish', 'neutral')

    Returns:
        html.Div: Styled confidence bar
    """

    return html.Div(
        [
            html.Div(
                style={"width": f"{min(max(confidence, 0), 100)}%"},
                className=f"confidence-bar__fill {signal_type}",
            )
        ],
        className="confidence-bar",
    )


def create_skeleton_loader(
    variant: str = "card",
    width: Optional[str] = None,
    height: Optional[str] = None,
) -> html.Div:
    """Create a Skeleton Loader component

    Args:
        variant: Type of skeleton ('card', 'text', 'value')
        width: Optional width override
        height: Optional height override

    Returns:
        html.Div: Animated skeleton loader
    """

    class_name = f"skeleton skeleton-{variant}"
    style = {}
    if width:
        style["width"] = width
    if height:
        style["height"] = height

    return html.Div(className=class_name, style=style if style else None)


def create_empty_state(
    icon: str = "📭",
    title: str = "No data available",
    message: str = "There's nothing to display at the moment.",
) -> html.Div:
    """Create an Empty State component

    Args:
        icon: Emoji icon to display
        title: Empty state title
        message: Empty state description

    Returns:
        html.Div: Styled empty state
    """

    return html.Div(
        [
            html.Div(icon, className="empty-state__icon"),
            html.H5(title, className="empty-state__title"),
            html.P(message, className="empty-state__message"),
        ],
        className="empty-state",
    )
