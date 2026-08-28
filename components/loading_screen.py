import base64
import streamlit as st
import streamlit.components.v1 as components


def _get_logo_base64(path="assets/logo.png"):
    """Robust logo loader: tries relative path then absolute project-root path."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        pass
    # Fallback: resolve relative to this file (components/ -> project root / assets/logo.png)
    try:
        import pathlib
        root = pathlib.Path(__file__).resolve().parent.parent
        abs_path = root / "assets" / "logo.png"
        with open(abs_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""


# Page -> (title, subtitle) mapping for the global loader (Tagalog/English mix aligned with PalaySense branding)
PAGE_LOADING_MESSAGES = {
    "home": ("Loading PalaySense...", "Preparing your dashboard — please wait"),
    "overview": ("Loading Overview...", "Fetching provincial & municipal data"),
    "price_forecast": ("Loading Price Forecast...", "Analyzing palay price trends"),
    "yield_forecast": ("Loading Yield Forecast...", "Calculating yield projections"),
    "lgu_dashboard": ("Loading LGU Dashboard...", "Syncing latest records — please wait"),
    "login": ("Loading LGU Portal...", "Preparing secure login — please wait"),
}

# LGU sub-page specific messages (used when query_page == lgu_dashboard)
LGU_PAGE_LOADING_MESSAGES = {
    "overview": ("Loading Dashboard...", "Fetching farm overview — please wait"),
    "provincial": ("Loading Lalawigan...", "Loading provincial analytics"),
    "municipal": ("Loading Bayan...", "Loading municipal analytics"),
    "forecasting": ("Loading Hula ng Ani...", "Preparing yield & price forecasts"),
    "historical": ("Loading Pagkumpara...", "Preparing historical comparison"),
    "import_data": ("Loading Mag-import...", "Preparing dataset import"),
    "settings": ("Loading Settings...", "Loading preferences"),
}


def get_loading_html(
    message="Logging in...",
    submessage="Please wait while we verify your credentials",
    logo_base64=None,
):
    """Return HTML string for PalaySense full-screen loading overlay."""
    if logo_base64 is None:
        logo_base64 = _get_logo_base64()

    logo_html = (
        f'<img src="data:image/png;base64,{logo_base64}" class="ps-loading-logo" alt="PalaySense Logo" />'
        if logo_base64
        else '<div class="ps-loading-logo fallback"><i class="material-symbols-outlined" style="font-size:20px; vertical-align:middle; margin-right:6px; color:#1B5E20;">agriculture</i></div>'
    )

    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    .ps-loading-overlay {{
        position: fixed;
        inset: 0;
        z-index: 999999;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: linear-gradient(120deg, #062B16 0%, #1E4A1D 30%, #7D9817 68%, #F1D85C 100%);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        animation: psFadeIn 0.35s ease-out;
    }}
    @keyframes psFadeIn {{
        from {{ opacity: 0; }}
        to {{ opacity: 1; }}
    }}
    .ps-loading-card {{
        background: #FFFFFF;
        border-radius: 20px;
        padding: 36px 40px 32px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.30), 0 8px 20px rgba(0,0,0,0.18);
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 18px;
        min-width: 320px;
        max-width: 90vw;
        width: 360px;
        animation: psSlideUp 0.45s cubic-bezier(0.16,1,0.3,1);
    }}
    @keyframes psSlideUp {{
        from {{ opacity: 0; transform: translateY(16px) scale(0.98); }}
        to {{ opacity: 1; transform: translateY(0) scale(1); }}
    }}
    .ps-loading-logo {{
        width: 130px;
        max-width: 70vw;
        height: auto;
        object-fit: contain;
        animation: psPulse 1.8s ease-in-out infinite;
    }}
    .ps-loading-logo.fallback {{
        width: 90px;
        height: 90px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 48px;
        background: #F3F4F6;
        border-radius: 16px;
    }}
    @keyframes psPulse {{
        0%, 100% {{ transform: scale(1); opacity: 1; }}
        50% {{ transform: scale(1.04); opacity: 0.92; }}
    }}
    .ps-spinner {{
        width: 46px;
        height: 46px;
        border: 4px solid #E5E7EB;
        border-top-color: #6C8C1A;
        border-right-color: #88A925;
        border-radius: 50%;
        animation: psSpin 0.85s linear infinite;
    }}
    @keyframes psSpin {{
        to {{ transform: rotate(360deg); }}
    }}
    .ps-loading-title {{
        font-size: 16px;
        font-weight: 800;
        color: #123524;
        letter-spacing: -0.3px;
        margin: 0;
        text-align: center;
    }}
    .ps-loading-subtitle {{
        font-size: 12.5px;
        font-weight: 500;
        color: #6B7280;
        margin: -8px 0 0 0;
        text-align: center;
        line-height: 1.4;
    }}
    .ps-loading-dots {{
        display: inline-flex;
        gap: 4px;
        align-items: center;
        justify-content: center;
        margin-top: 2px;
    }}
    .ps-loading-dots span {{
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #6C8C1A;
        animation: psBounce 1.2s infinite ease-in-out both;
    }}
    .ps-loading-dots span:nth-child(1) {{ animation-delay: -0.32s; }}
    .ps-loading-dots span:nth-child(2) {{ animation-delay: -0.16s; }}
    @keyframes psBounce {{
        0%, 80%, 100% {{ transform: scale(0.65); opacity: 0.6; }}
        40% {{ transform: scale(1); opacity: 1; }}
    }}
    .ps-loading-progress {{
        width: 100%;
        height: 4px;
        background: #E5E7EB;
        border-radius: 999px;
        overflow: hidden;
        margin-top: 4px;
    }}
    .ps-loading-progress-bar {{
        height: 100%;
        width: 45%;
        background: linear-gradient(90deg, #6C8C1A, #88A925, #F1D85C);
        border-radius: 999px;
        animation: psProgress 1.1s ease-in-out infinite;
    }}
    @keyframes psProgress {{
        0% {{ transform: translateX(-100%); }}
        100% {{ transform: translateX(280%); }}
    }}
    </style>
    <div class="ps-loading-overlay">
        <div class="ps-loading-card">
            {logo_html}
            <div class="ps-spinner"></div>
            <p class="ps-loading-title">{message}</p>
            <p class="ps-loading-subtitle">{submessage}</p>
            <div class="ps-loading-dots"><span></span><span></span><span></span></div>
            <div class="ps-loading-progress"><div class="ps-loading-progress-bar"></div></div>
        </div>
    </div>
    """


def show_loading_screen(message="Logging in...", submessage="Please wait while we verify your credentials"):
    """Render full-screen loading overlay via st.markdown (blocking until cleared by caller)."""
    logo = _get_logo_base64()
    html = get_loading_html(message=message, submessage=submessage, logo_base64=logo)
    st.markdown(html, unsafe_allow_html=True)


def show_login_loading():
    """Convenience wrapper for login flow."""
    show_loading_screen(
        message="Logging in...",
        submessage="Verifying your credentials — please wait",
    )


# ------------------------------------------------------------------
# Global auto-dismiss loader — used on EVERY page load (assets/logo.png)
# ------------------------------------------------------------------

def get_global_loading_html(
    message="Loading PalaySense...",
    submessage="Please wait while we prepare your dashboard",
    logo_base64=None,
    duration_ms=1400,
):
    """Return HTML for a full-screen PalaySense loader that auto-dismisses via CSS.

    The overlay sits at ``z-index: 999999`` and uses the logo from
    ``assets/logo.png`` (base64-embedded). After ``duration_ms`` the overlay
    fades out (0.45s) and disables pointer-events so the page becomes interactive
    without requiring JS. A JS fallback (injected via ``show_global_loading``)
    also removes the DOM node for completeness.

    Args:
        message: Bold title inside the white card.
        submessage: Smaller subtitle inside the card.
        logo_base64: Pre-encoded logo; if None the file is read lazily.
        duration_ms: How long the loader stays fully visible before fading.
    """
    if logo_base64 is None:
        logo_base64 = _get_logo_base64()

    logo_html = (
        f'<img src="data:image/png;base64,{logo_base64}" class="ps-global-logo" alt="PalaySense Logo" />'
        if logo_base64
        else '<div class="ps-global-logo fallback"><i class="material-symbols-outlined" style="font-size:28px; color:#1B5E20;">agriculture</i></div>'
    )

    # Delay in seconds for the fade-out animation (visible duration -> then fade)
    delay_s = duration_ms / 1000.0

    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    #ps-global-loader {{
        position: fixed;
        inset: 0;
        z-index: 999999;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: linear-gradient(120deg, #062B16 0%, #1E4A1D 30%, #7D9817 68%, #F1D85C 100%);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        animation: psGlobalFadeIn 0.30s ease-out, psGlobalHide 0.45s ease {delay_s:.2f}s forwards;
    }}
    @keyframes psGlobalFadeIn {{
        from {{ opacity: 0; }}
        to {{ opacity: 1; }}
    }}
    @keyframes psGlobalHide {{
        to {{ opacity: 0; visibility: hidden; pointer-events: none; }}
    }}
    .ps-global-card {{
        background: #FFFFFF;
        border-radius: 20px;
        padding: 36px 40px 28px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.30), 0 8px 20px rgba(0,0,0,0.18);
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
        min-width: 320px;
        max-width: 90vw;
        width: 360px;
        animation: psGlobalSlideUp 0.45s cubic-bezier(0.16,1,0.3,1);
    }}
    @keyframes psGlobalSlideUp {{
        from {{ opacity: 0; transform: translateY(16px) scale(0.98); }}
        to {{ opacity: 1; transform: translateY(0) scale(1); }}
    }}
    .ps-global-logo {{
        width: 135px;
        max-width: 70vw;
        height: auto;
        object-fit: contain;
        animation: psGlobalPulse 1.8s ease-in-out infinite;
    }}
    .ps-global-logo.fallback {{
        width: 90px;
        height: 90px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #F3F4F6;
        border-radius: 16px;
    }}
    @keyframes psGlobalPulse {{
        0%, 100% {{ transform: scale(1); opacity: 1; }}
        50% {{ transform: scale(1.04); opacity: 0.92; }}
    }}
    .ps-global-spinner {{
        width: 44px;
        height: 44px;
        border: 4px solid #E5E7EB;
        border-top-color: #6C8C1A;
        border-right-color: #88A925;
        border-radius: 50%;
        animation: psGlobalSpin 0.85s linear infinite;
    }}
    @keyframes psGlobalSpin {{ to {{ transform: rotate(360deg); }} }}
    .ps-global-title {{
        font-size: 15.5px;
        font-weight: 800;
        color: #123524;
        letter-spacing: -0.3px;
        margin: 0;
        text-align: center;
    }}
    .ps-global-subtitle {{
        font-size: 12.5px;
        font-weight: 500;
        color: #6B7280;
        margin: -6px 0 0 0;
        text-align: center;
        line-height: 1.45;
    }}
    .ps-global-dots {{
        display: inline-flex;
        gap: 5px;
        align-items: center;
        justify-content: center;
        margin-top: 2px;
    }}
    .ps-global-dots span {{
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #6C8C1A;
        animation: psGlobalBounce 1.2s infinite ease-in-out both;
    }}
    .ps-global-dots span:nth-child(1) {{ animation-delay: -0.32s; }}
    .ps-global-dots span:nth-child(2) {{ animation-delay: -0.16s; }}
    @keyframes psGlobalBounce {{
        0%, 80%, 100% {{ transform: scale(0.65); opacity: 0.6; }}
        40% {{ transform: scale(1); opacity: 1; }}
    }}
    .ps-global-progress {{
        width: 100%;
        height: 4px;
        background: #E5E7EB;
        border-radius: 999px;
        overflow: hidden;
        margin-top: 2px;
    }}
    .ps-global-progress-bar {{
        height: 100%;
        width: 45%;
        background: linear-gradient(90deg, #6C8C1A, #88A925, #F1D85C);
        border-radius: 999px;
        animation: psGlobalProgress 1.1s ease-in-out infinite;
    }}
    @keyframes psGlobalProgress {{
        0% {{ transform: translateX(-100%); }}
        100% {{ transform: translateX(280%); }}
    }}
    .ps-global-badge {{
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #6C8C1A;
        background: #F0F7E6;
        border: 1px solid #D9E8C0;
        padding: 4px 10px;
        border-radius: 999px;
    }}
    </style>
    <div id="ps-global-loader" aria-live="polite" aria-busy="true">
        <div class="ps-global-card">
            {logo_html}
            <div class="ps-global-badge">PalaySense</div>
            <div class="ps-global-spinner" role="status" aria-label="Loading"></div>
            <p class="ps-global-title">{message}</p>
            <p class="ps-global-subtitle">{submessage}</p>
            <div class="ps-global-dots"><span></span><span></span><span></span></div>
            <div class="ps-global-progress"><div class="ps-global-progress-bar"></div></div>
        </div>
    </div>
    """


def show_global_loading(
    message="Loading PalaySense...",
    submessage="Please wait while we prepare your dashboard",
    duration_ms=1400,
    logo_base64=None,
):
    """Render the global auto-dismiss loading overlay.

    Injects the overlay via ``st.markdown`` (CSS auto-hide) and a zero-height
    ``components.html`` iframe that runs JS to remove the node after
    ``duration_ms + 500ms`` — guaranteeing no leftover overlay blocks interaction
    even if CSS animation is interrupted.

    Call this once at the top of ``app.py`` before routing so it appears on
    EVERY page/navigation (home, overview, price_forecast, yield_forecast,
    lgu_dashboard, etc.) using the logo in ``assets/logo.png``.
    """
    if logo_base64 is None:
        logo_base64 = _get_logo_base64()
    html = get_global_loading_html(
        message=message, submessage=submessage, logo_base64=logo_base64, duration_ms=duration_ms
    )
    st.markdown(html, unsafe_allow_html=True)
    # JS fallback — runs inside iframe, reaches parent document
    # Use duration_ms + fade (450ms) + small buffer
    total_ms = int(duration_ms + 650)
    js = f"""
    <script>
    (function() {{
        var delay = {total_ms};
        setTimeout(function() {{
            try {{
                var doc = window.parent && window.parent.document;
                if (!doc) return;
                var el = doc.getElementById('ps-global-loader');
                if (el) {{
                    el.style.transition = 'opacity 0.35s ease';
                    el.style.opacity = '0';
                    el.style.pointerEvents = 'none';
                    setTimeout(function() {{
                        try {{ if (el && el.parentNode) el.parentNode.removeChild(el); }} catch(e) {{}}
                    }}, 400);
                }}
            }} catch(e) {{}}
        }}, delay);
    }})();
    </script>
    """
    try:
        components.html(js, height=0, width=0)
    except Exception:
        pass


def show_page_loading(page_key: str, duration_ms=1400):
    """Convenience: pick message by page key and render global loader (non-blocking, CSS auto-hide).

    For ``lgu_dashboard`` the active LGU sub-page (``st.session_state['lgu_page']``)
    is used to show a more specific message (Buong Dashboard / Lalawigan / Bayan / Hula ng Ani...).

    Returns True if a loader was shown.
    """
    # LGU dashboard sub-page granularity — gives the user context on every sidebar click
    if page_key == "lgu_dashboard":
        try:
            lgu_key = st.session_state.get("lgu_page", "overview")
            msg = LGU_PAGE_LOADING_MESSAGES.get(lgu_key)
            if msg is not None:
                title, subtitle = msg
                show_global_loading(message=title, submessage=subtitle, duration_ms=duration_ms)
                return True
        except Exception:
            pass
    msg = PAGE_LOADING_MESSAGES.get(page_key)
    if msg is None:
        # Fallback generic
        msg = ("Loading PalaySense...", "Please wait — loading your page")
    title, subtitle = msg
    show_global_loading(message=title, submessage=subtitle, duration_ms=duration_ms)
    return True


# ------------------------------------------------------------------
# Blocking variant — guarantees visibility via placeholder + sleep
# Used for page navigation / logout where CSS auto-hide alone is not
# reliably perceived (Streamlit's rerun hides the overlay too fast).
# ------------------------------------------------------------------
def show_blocking_global_loading(
    message="Loading PalaySense...",
    submessage="Please wait while we prepare your dashboard",
    duration_sec=1.15,
    logo_base64=None,
):
    """Blocking loader: renders overlay in a placeholder, sleeps, then clears.

    This is the most reliable pattern in Streamlit (same as login flow) —
    the overlay is visibly present for exactly ``duration_sec`` seconds.
    """
    import time
    if logo_base64 is None:
        logo_base64 = _get_logo_base64()
    # get_global_loading_html with a long CSS duration so it doesn't auto-hide before sleep ends
    duration_ms = int(duration_sec * 1000) + 500
    html = get_global_loading_html(
        message=message, submessage=submessage, logo_base64=logo_base64, duration_ms=duration_ms
    )
    placeholder = st.empty()
    placeholder.markdown(html, unsafe_allow_html=True)
    time.sleep(duration_sec)
    try:
        placeholder.empty()
    except Exception:
        pass


def show_blocking_page_loading(page_key: str, duration_sec=1.15, subpage_key: str | None = None):
    """Blocking variant of ``show_page_loading`` — picks title per page/subpage and blocks."""
    # LGU sub-page granularity
    if page_key == "lgu_dashboard":
        try:
            lgu_key = subpage_key if subpage_key is not None else st.session_state.get("lgu_page", "overview")
            msg = LGU_PAGE_LOADING_MESSAGES.get(lgu_key)
            if msg is not None:
                title, subtitle = msg
                show_blocking_global_loading(message=title, submessage=subtitle, duration_sec=duration_sec)
                return True
        except Exception:
            pass
    msg = PAGE_LOADING_MESSAGES.get(page_key)
    if msg is None:
        msg = ("Loading PalaySense...", "Please wait — loading your page")
    title, subtitle = msg
    show_blocking_global_loading(message=title, submessage=subtitle, duration_sec=duration_sec)
    return True


def show_logout_loading(duration_sec=1.15):
    """Dedicated blocking loader for logout transition (shows on source before redirect)."""
    show_blocking_global_loading(
        message="Logging out...",
        submessage="Clearing your session — please wait",
        duration_sec=duration_sec,
    )
