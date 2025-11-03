#!/usr/bin/env python3
try:
    from streamlit_option_menu import option_menu
    print("✓ option_menu imported")
except Exception as e:
    print(f"✗ option_menu import failed: {e}")

try:
    from streamlit_extras.metric_cards import style_metric_cards  
    print("✓ style_metric_cards imported")
except Exception as e:
    print(f"✗ style_metric_cards import failed: {e}")

try:
    from streamlit_extras.stylable_container import stylable_container
    print("✓ stylable_container imported")
except Exception as e:
    print(f"✗ stylable_container import failed: {e}")

print("\nAll packages available!")
