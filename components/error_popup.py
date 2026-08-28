# Contact directory shown inside the login error popup
CONTACTS = [
    {"name": "Kyla Mercado", "role": "Lead Developer", "email": "kfmercado23@bpsu.edu.ph"},
]

GENERIC_LOGIN_ERROR = "Invalid credentials. Please check your email and password."

# Errors that should trigger the generic popup (B: 3,4,5)
POPUP_ERROR_KEYS = [
    "EMAIL_NOT_FOUND",
    "INVALID_PASSWORD",
    "INVALID_LOGIN_CREDENTIALS",
]

# Also match the human-readable versions returned by pyrebase_sign_in
POPUP_ERROR_PHRASES = [
    "no account found",
    "incorrect password",
    "invalid login credentials",
]


def _should_show_popup(raw_error: str) -> bool:
    """Return True only for B (3,4,5) — wrong credentials."""
    if not raw_error:
        return False
    upper = raw_error.upper()
    lower = raw_error.lower()
    for k in POPUP_ERROR_KEYS:
        if k in upper:
            return True
    for p in POPUP_ERROR_PHRASES:
        if p in lower:
            return True
    return False


def get_error_popup_html(
    message: str = GENERIC_LOGIN_ERROR,
    contacts=None,
    duration_ms: int = 4500,
    logo_base64: str | None = None,
) -> str:
    """Return HTML for auto-dismiss error popup (Option B).

    Uses fixed overlay + white card, matches PalaySense branding.
    Auto-hides via CSS animation after duration_ms and JS fallback
    removes the node so it does not block interaction.
    """
    if contacts is None:
        contacts = CONTACTS

    # Build contacts HTML
    contacts_html = ""
    for c in contacts:
        name = c.get("name", "")
        role = c.get("role", "")
        email = c.get("email", "")
        contacts_html += f"""
        <div class="ps-error-contact">
            <div class="ps-error-contact-avatar">{name[:1].upper() if name else "?"}</div>
            <div class="ps-error-contact-info">
                <div class="ps-error-contact-name">{name}</div>
                <div class="ps-error-contact-role">{role}</div>
                <a class="ps-error-contact-email" href="mailto:{email}">{email}</a>
            </div>
        </div>
        """

    delay_s = duration_ms / 1000.0

    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    #ps-error-overlay {{
        position: fixed;
        inset: 0;
        z-index: 999999;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(6, 43, 22, 0.55);
        backdrop-filter: blur(4px);
        -webkit-backdrop-filter: blur(4px);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        animation: psErrorFadeIn 0.28s ease-out, psErrorHide 0.42s ease {delay_s:.2f}s forwards;
        padding: 16px;
        box-sizing: border-box;
        /* Ensure overlay never creates scroll */
        overflow: hidden;
    }}
    @keyframes psErrorFadeIn {{
        from {{ opacity: 0; }}
        to {{ opacity: 1; }}
    }}
    @keyframes psErrorHide {{
        to {{ opacity: 0; visibility: hidden; pointer-events: none; }}
    }}
    .ps-error-card {{
        background: #FFFFFF;
        border-radius: 20px;
        padding: 28px 28px 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.30), 0 8px 20px rgba(0,0,0,0.18);
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 14px;
        width: 380px;
        max-width: 92vw;
        text-align: center;
        position: relative;
        animation: psErrorSlideUp 0.38s cubic-bezier(0.16,1,0.3,1);
        border-top: 4px solid #EF4444;
    }}
    @keyframes psErrorSlideUp {{
        from {{ opacity: 0; transform: translateY(14px) scale(0.98); }}
        to {{ opacity: 1; transform: translateY(0) scale(1); }}
    }}
    .ps-error-close {{
        position: absolute;
        top: 10px;
        right: 10px;
        width: 28px;
        height: 28px;
        border-radius: 999px;
        border: 1px solid #E5E7EB;
        background: #F9FAFB;
        color: #6B7280;
        font-size: 16px;
        line-height: 1;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.18s ease;
    }}
    .ps-error-close:hover {{
        background: #F3F4F6;
        color: #111827;
        border-color: #D1D5DB;
    }}
    .ps-error-icon {{
        width: 56px;
        height: 56px;
        border-radius: 999px;
        background: #FEF2F2;
        border: 1.5px solid #FECACA;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 28px;
        color: #DC2626;
    }}
    .ps-error-title {{
        font-size: 16px;
        font-weight: 800;
        color: #991B1B;
        margin: 0;
        letter-spacing: -0.3px;
    }}
    .ps-error-message {{
        font-size: 13px;
        font-weight: 500;
        color: #4B5563;
        margin: 0;
        line-height: 1.5;
        max-width: 320px;
    }}
    .ps-error-divider {{
        width: 100%;
        height: 1px;
        background: #E5E7EB;
        margin: 4px 0 2px;
    }}
    .ps-error-directory-label {{
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #6C8C1A;
        margin: 0;
        align-self: flex-start;
        width: 100%;
        text-align: left;
    }}
    .ps-error-contacts {{
        width: 100%;
        display: flex;
        flex-direction: column;
        gap: 8px;
        align-items: stretch;
    }}
    .ps-error-contact {{
        display: flex;
        align-items: center;
        gap: 10px;
        background: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 10px 12px;
        text-align: left;
    }}
    .ps-error-contact-avatar {{
        width: 36px;
        height: 36px;
        border-radius: 999px;
        background: linear-gradient(135deg, #6C8C1A 0%, #88A925 100%);
        color: #FFFFFF;
        font-weight: 800;
        font-size: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }}
    .ps-error-contact-info {{
        display: flex;
        flex-direction: column;
        gap: 1px;
        overflow: hidden;
    }}
    .ps-error-contact-name {{
        font-size: 13px;
        font-weight: 700;
        color: #111827;
        line-height: 1.2;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .ps-error-contact-role {{
        font-size: 11px;
        font-weight: 600;
        color: #6B7280;
        line-height: 1.2;
    }}
    .ps-error-contact-email {{
        font-size: 11.5px;
        font-weight: 600;
        color: #55751B !important;
        text-decoration: none !important;
        word-break: break-all;
    }}
    .ps-error-contact-email:hover {{
        text-decoration: underline !important;
    }}
    .ps-error-timer {{
        font-size: 11px;
        font-weight: 600;
        color: #9CA3AF;
        margin: 2px 0 0 0;
    }}
    .ps-error-progress {{
        width: 100%;
        height: 4px;
        background: #E5E7EB;
        border-radius: 999px;
        overflow: hidden;
        margin-top: 2px;
    }}
    .ps-error-progress-bar {{
        height: 100%;
        width: 100%;
        background: linear-gradient(90deg, #EF4444, #F59E0B);
        border-radius: 999px;
        animation: psErrorProgress {delay_s:.2f}s linear forwards;
        transform-origin: left;
    }}
    @keyframes psErrorProgress {{
        from {{ transform: scaleX(1); }}
        to {{ transform: scaleX(0); }}
    }}
    .ps-error-dismiss {{
        width: 100%;
        height: 38px;
        border: 1px solid #D1D5DB;
        background: #FFFFFF;
        color: #374151;
        font-size: 13px;
        font-weight: 700;
        border-radius: 8px;
        cursor: pointer;
        margin-top: 4px;
        transition: all 0.18s ease;
    }}
    .ps-error-dismiss:hover {{
        background: #F9FAFB;
        border-color: #9CA3AF;
    }}
    </style>
    <div id="ps-error-overlay" role="alertdialog" aria-modal="true" aria-label="Login error">
        <div class="ps-error-card">
            <button class="ps-error-close" aria-label="Close" onclick="var e=document.getElementById('ps-error-overlay'); if(e){{e.style.transition='opacity 0.3s ease';e.style.opacity='0';e.style.pointerEvents='none';e.style.visibility='hidden';}}">×</button>
            <div class="ps-error-icon">!</div>
            <p class="ps-error-title">Login Failed</p>
            <p class="ps-error-message">{message}</p>
            <div class="ps-error-divider"></div>
            <p class="ps-error-directory-label">Need help? Contact us</p>
            <div class="ps-error-contacts">
                {contacts_html}
            </div>
            <p class="ps-error-timer">Auto-closing...</p>
            <div class="ps-error-progress"><div class="ps-error-progress-bar"></div></div>
            <button class="ps-error-dismiss" onclick="var e=document.getElementById('ps-error-overlay'); if(e){{e.style.transition='opacity 0.3s ease';e.style.opacity='0';e.style.pointerEvents='none';e.style.visibility='hidden';}}">Dismiss</button>
        </div>
    </div>
    """
