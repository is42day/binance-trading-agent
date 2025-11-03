#!/usr/bin/env python3
from binance_trade_agent import web_ui
import inspect

lines = inspect.getsource(web_ui.main)
print("Lines in main:", len(lines.split('\n')))
print("Has option_menu:", 'option_menu' in lines)
print("Has style_metric_cards:", 'style_metric_cards' in lines)
print("Has stylable_container:", 'stylable_container' in lines)
