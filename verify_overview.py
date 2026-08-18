import sys
import traceback

results = []
try:
    import streamlit, pandas, plotly
    results.append(f"deps ok: streamlit={streamlit.__version__} pandas={pandas.__version__} plotly={plotly.__version__}")
except Exception as e:
    results.append(f"deps FAIL: {e!r}")

# Test theme module (pure helpers, only needs streamlit stub)
try:
    import streamlit as st
    import app_pages.lgu_dashboard.theme as theme
    results.append("theme import ok")
    results.append(f"  has market_price_card: {hasattr(theme, 'market_price_card')}")
    results.append(f"  has kpi_card: {hasattr(theme, 'kpi_card')}")

    # Test market_price_card pure function
    up = theme.market_price_card("Regular", 25.5, 5.2)
    down = theme.market_price_card("Fancy", 25.5, -3.1)
    flat = theme.market_price_card("Fancy", 25.5, 0.0)
    none = theme.market_price_card("Fancy", 25.5, None)
    results.append(f"  up card has ps-up: {'ps-up' in up}")
    results.append(f"  down card has ps-down: {'ps-down' in down}")
    results.append(f"  flat card has ps-flat: {'ps-flat' in flat}")
    results.append(f"  none card has ps-flat: {'ps-flat' in none}")
    results.append(f"  price formatted: {'25.50' in up}")
except Exception as e:
    results.append("theme import FAIL: " + repr(e))
    traceback.print_exc()

# Test overview module using a fake streamlit to avoid requiring full runtime
try:
    import app_pages.lgu_dashboard.overview as ov
    results.append("overview import ok")
    results.append(f"  has render: {hasattr(ov, 'render')}")
    results.append(f"  has _supply_status_display: {hasattr(ov, '_supply_status_display')}")

    # Test _supply_status_display mapping
    results.append(f"  Surplus -> {ov._supply_status_display('Surplus')}")
    results.append(f"  Balanced -> {ov._supply_status_display('Balanced')}")
    results.append(f"  Deficit -> {ov._supply_status_display('Deficit')}")
    results.append(f"  No data -> {ov._supply_status_display('No data')}")
except Exception as e:
    results.append("overview import FAIL: " + repr(e))
    traceback.print_exc()

with open("verify_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))
print("WROTE verify_result.txt")
print("\n".join(results))
