import base64
import streamlit as st


def _get_logo_base64(path="assets/logo.png"):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""


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
    """Render full-screen loading overlay via st.markdown."""
    logo = _get_logo_base64()
    html = get_loading_html(message=message, submessage=submessage, logo_base64=logo)
    st.markdown(html, unsafe_allow_html=True)


def show_login_loading():
    """Convenience wrapper for login flow."""
    show_loading_screen(
        message="Logging in...",
        submessage="Verifying your credentials — please wait",
    )
