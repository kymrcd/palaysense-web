import base64
import time
import streamlit as st
from components.loading_screen import show_loading_screen, get_loading_html
from components.error_popup import (
    get_error_popup_html,
    GENERIC_LOGIN_ERROR,
    _should_show_popup,
)

# Function to convert your local image file to a base64 text string
def get_base64(image_path):
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""


def login_page():
    # 0. Auto-expire error popup after 4.5s (so it does not reappear on next unrelated rerun)
    if st.session_state.get("show_login_error_popup"):
        err_time = st.session_state.get("login_error_time", 0)
        try:
            if time.time() - float(err_time) > 4.6:
                st.session_state.pop("show_login_error_popup", None)
                st.session_state.pop("login_error_time", None)
                st.session_state.pop("login_error_msg", None)
        except Exception:
            pass

    # Render popup overlay if active (Option B - CSS-only auto-hide, no JS removeChild to avoid React mismatch)
    if st.session_state.get("show_login_error_popup"):
        popup_msg = st.session_state.get("login_error_msg", GENERIC_LOGIN_ERROR)
        st.markdown(
            get_error_popup_html(message=popup_msg, duration_ms=4500),
            unsafe_allow_html=True,
        )

    # 1. Fetch logo
    logo_base64 = get_base64("assets/logo.png")

    # 2. Inject CSS targeted strictly at the Streamlit container (st-key-login_box)
    st.markdown(
        f"""
        <style>
        /* Tago ang default Streamlit headers / sidebars */
        [data-testid="stSidebar"],
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"] {{
            display: none !important;
            visibility: hidden !important;
        }}

        /* Full screen background gradient */
        [data-testid="stAppViewContainer"] {{
            background: linear-gradient(
                120deg,
                #062B16 0%,
                #1E4A1D 30%,
                #7D9817 68%,
                #F1D85C 100%
            ) !important;
            min-height: 100vh !important;
        }}

        /* Gitna sa buong screen */
        .main .block-container {{
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            min-height: 100vh !important;
            padding: 1rem !important;
            max-width: 100% !important;
        }}

        /* EKSATTONG SQUARE WHITE CARD (Kinukulong lahat sa loob) */
        [data-testid="stElementContainer"]:has(.st-key-login_box),
        div[class*="st-key-login_box"] {{
            background-color: #FFFFFF !important;
            border-radius: 16px !important;
            padding: 30px 32px 24px !important;
            box-shadow: 0 15px 35px rgba(0,0,0,0.25) !important;
            width: 380px !important;            /* Sakto ang lapad, hindi masyadong malapad */
            max-width: 90vw !important;
            margin: 0 auto !important;
            box-sizing: border-box !important;
        }}

        /* Logo styling sa loob ng card */
        .login-logo {{
            display: block;
            width: 130px; 
            max-width: 80%;
            margin: 0 auto 15px auto;
        }}

        /* Inputs sa loob ng card */
        div[data-testid="stTextInput"] label {{
            color: #222222 !important;
            font-size: 12px !important; 
            font-weight: 600 !important;
        }}

        div[data-testid="stTextInput"] input {{
            height: 38px !important; 
            background-color: #ECECEC !important;
            border: 1px solid transparent !important;
            border-radius: 6px !important;
            color: #111827 !important;
            font-size: 13px !important;
            padding-left: 10px !important;
        }}

        div[data-testid="stTextInput"] input:focus {{
            border: 2px solid #79961C !important;
            background-color: #FFFFFF !important;
            box-shadow: none !important;
        }}

        /* Field error wrapper adjustments inside login_box */
        div[class*="st-key-login_box"] .field-error {{
            margin-top: 4px !important;
        }}

        /* Log in button sa loob ng card */
        .stButton > button {{
            width: 100% !important;
            height: 40px !important; 
            margin-top: 8px !important;
            border: none !important;
            border-radius: 8px !important;
            background: linear-gradient(135deg, #6C8C1A 0%, #88A925 100%) !important;
            color: white !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            letter-spacing: 0.5px !important;
            box-shadow: 0 6px 14px rgba(108, 140, 26, 0.2);
        }}

        .stButton > button:hover {{
            background: linear-gradient(135deg, #5F7C17 0%, #7F9F22 100%) !important;
        }}

        /* Footer text sa loob ng card */
        .need-help {{
            text-align: center;
            margin-top: 12px;
            color: #4B5563;
            font-size: 11px;
        }}
        .need-help strong {{
            color: #55751B;
        }}

        .divider {{
            display: flex;
            align-items: center;
            margin: 12px 0 10px;
        }}

        .divider::before,
        .divider::after {{
            content: "";
            flex: 1;
            border-bottom: 1px solid #D1D5DB;
        }}

        .divider span {{
            margin: 0 8px;
            color: #6B7280;
            font-size: 11px;
        }}

        .back-link {{
            text-align: center;
            font-size: 11px;
        }}

        .back-link a {{
            color: #55751B !important;
            font-weight: 600 !important;
            text-decoration: none !important;
        }}

        /* Inline field error - malapit sa input box */
        .field-error {{
            color: #DC2626 !important;
            font-size: 11px !important;
            font-weight: 600 !important;
            margin: 4px 0 8px 2px !important;
            line-height: 1.3 !important;
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        .field-error::before {{
            content: "⚠";
            font-size: 11px;
        }}
        /* Red border - pure CSS, no JS/iframe (when any field-error exists inside login_box, both inputs get red) */
        div[class*="st-key-login_box"]:has(.field-error) div[data-testid="stTextInput"] input {{
            border: 1.5px solid #EF4444 !important;
            background-color: #FEF2F2 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 2b. Auto-clear individual field errors when user has corrected them (so red border via :has disappears)
    _stored_field_errors = st.session_state.get("login_field_errors", {})
    if _stored_field_errors:
        _cur_u = str(st.session_state.get("username", "")).strip()
        _cur_p = str(st.session_state.get("password", "")).strip()
        _needs_update = False
        if _stored_field_errors.get("username") and _cur_u:
            _stored_field_errors.pop("username", None)
            _needs_update = True
        if _stored_field_errors.get("password") and _cur_p:
            _stored_field_errors.pop("password", None)
            _needs_update = True
        if not _stored_field_errors:
            st.session_state.pop("login_field_errors", None)
        elif _needs_update:
            st.session_state["login_field_errors"] = _stored_field_errors

    field_errors = st.session_state.get("login_field_errors", {})

    # 3. Gamit ang Streamlit Container na may key para siguradong NAKALOOB LAHAT
    with st.container(key="login_box"):
        # Logo Image
        logo_html = f'<img class="login-logo" src="data:image/png;base64,{logo_base64}">' if logo_base64 else '<div class="login-logo" style="text-align:center;"><i class="material-symbols-outlined" style="font-size:2rem; color:#1B5E20; vertical-align:middle;">agriculture</i></div>'
        st.markdown(logo_html, unsafe_allow_html=True)

        # Text Inputs (Lahat 'to ay nasa LOOB na ng white box)
        username = st.text_input(
            "Username",
            placeholder="Enter your username",
            key="username",
            label_visibility="visible"
        )
        # Inline error malapit sa username input
        if field_errors.get("username"):
            st.markdown(f'<div class="field-error">{field_errors["username"]}</div>', unsafe_allow_html=True)

        password = st.text_input(
            "Password",
            placeholder="Enter your password",
            type="password",
            key="password",
            label_visibility="visible"
        )
        # Inline error malapit sa password input
        if field_errors.get("password"):
            st.markdown(f'<div class="field-error">{field_errors["password"]}</div>', unsafe_allow_html=True)

        # Login Button (Full width sa loob ng box)
        login_clicked = st.button("LOG IN", key="login_btn", use_container_width=True)

        # Links sa ilalim - Forgot Password removed, replaced with Need help?
        st.markdown(
            """
            <div class="need-help">Need help? <strong>Contact support via login error popup</strong></div>
            <div class="divider"><span>or</span></div>
            <div class="back-link"><a href="?page=home" target="_self">Back to Public Dashboard</a></div>
            """,
            unsafe_allow_html=True,
        )

    # 4. Authentication Logic — with full-screen loading overlay
    if login_clicked:
        # Clear previous field errors on new attempt
        st.session_state.pop("login_field_errors", None)
        # Also clear any lingering popup state on new click (will be re-set if needed)
        st.session_state.pop("show_login_error_popup", None)
        st.session_state.pop("login_error_time", None)

        # A: Blank fields -> inline error malapit sa input (hindi popup)
        username_stripped = (username or "").strip()
        password_stripped = (password or "").strip()
        field_err = {}
        if not username_stripped:
            field_err["username"] = "Username is required."
        if not password_stripped:
            field_err["password"] = "Password is required."
        if field_err:
            st.session_state["login_field_errors"] = field_err
            st.rerun()
        else:
            try:
                from utils.firebase_config import pyrebase_sign_in, set_session_user

                # Show PalaySense loading screen while authenticating
                loading_placeholder = st.empty()
                loading_placeholder.markdown(
                    get_loading_html(
                        message="Logging in...",
                        submessage="Verifying your credentials — please wait",
                        logo_base64=logo_base64,
                    ),
                    unsafe_allow_html=True,
                )
                # Small UX delay so animation is visible even on fast networks
                time.sleep(0.85)

                result = pyrebase_sign_in(username, password)

                if isinstance(result, dict) and "error" not in result:
                    # Keep loading visible briefly, then show redirect state
                    loading_placeholder.markdown(
                        get_loading_html(
                            message="Login successful!",
                            submessage="Redirecting to LGU Dashboard...",
                            logo_base64=logo_base64,
                        ),
                        unsafe_allow_html=True,
                    )
                    set_session_user(result)
                    st.session_state["login_success"] = True
                    time.sleep(1.1)
                    loading_placeholder.empty()
                    st.query_params["page"] = "lgu_dashboard"
                    st.rerun()
                elif isinstance(result, dict) and "error" in result:
                    loading_placeholder.empty()
                    raw_err = str(result.get("error", ""))
                    # B lang ang popup (3,4,5) -> generic message + 4.5s auto-dismiss
                    if _should_show_popup(raw_err):
                        st.session_state["show_login_error_popup"] = True
                        st.session_state["login_error_msg"] = GENERIC_LOGIN_ERROR
                        st.session_state["login_error_time"] = time.time()
                        # Clear any field errors so red border doesn't persist
                        st.session_state.pop("login_field_errors", None)
                        st.rerun()
                    else:
                        # Other firebase errors (USER_DISABLED, TOO_MANY, etc.) stay as inline st.error
                        st.error(result["error"])
                else:
                    loading_placeholder.empty()
                    st.error("Invalid response received from authentication service.")
            except Exception as e:
                # Ensure overlay is cleared on exception
                try:
                    loading_placeholder.empty()
                except Exception:
                    pass
                st.error(f"Authentication error: {str(e)}")


if __name__ == "__main__":
    login_page()