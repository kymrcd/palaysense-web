import base64
import streamlit as st


def get_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def login_page():
    logo_base64 = get_base64("assets/logo.png")

    st.markdown(
        f"""
        <style>
        [data-testid="stSidebar"],
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"] {{
            display: none !important;
        }}

        [data-testid="stAppViewContainer"] {{
            background: linear-gradient(
                120deg,
                #062B16 0%,
                #1E4A1D 30%,
                #7D9817 68%,
                #F1D85C 100%
            );
        }}

        .stApp {{
            min-height: 100vh;
        }}

        .login-shell {{
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
            box-sizing: border-box;
        }}

        .st-key-login_card {{
            width: 470px;
            max-width: calc(100vw - 32px);
            background: #FDFDFD;
            border-radius: 12px;
            padding: 42px 48px 38px;
            box-shadow: 0 20px 45px rgba(0, 0, 0, 0.22);
            box-sizing: border-box;
        }}

        .login-logo {{
            display: block;
            width: 235px;
            max-width: 80%;
            margin: 0 auto 28px;
        }}

        div[data-testid="stTextInput"] label {{
            color: #222 !important;
            font-size: 14px !important;
            font-weight: 600 !important;
        }}

        div[data-testid="stTextInput"] input {{
            height: 52px !important;
            background-color: #ECECEC !important;
            border: 1px solid transparent !important;
            border-radius: 8px !important;
            color: #111827 !important;
            font-size: 15px !important;
            padding-left: 14px !important;
        }}

        div[data-testid="stTextInput"] input:focus {{
            border: 2px solid #79961C !important;
            box-shadow: none !important;
        }}

        .stButton > button {{
            width: 100% !important;
            height: 52px !important;
            margin-top: 12px !important;
            border: none !important;
            border-radius: 10px !important;
            background: linear-gradient(135deg, #6C8C1A 0%, #88A925 100%) !important;
            color: white !important;
            font-size: 18px !important;
            font-weight: 700 !important;
            letter-spacing: 0.5px !important;
            transition: 0.25s ease !important;
            box-shadow: 0 10px 20px rgba(108, 140, 26, 0.22);
        }}

        .stButton > button:hover {{
            transform: translateY(-2px);
            background: linear-gradient(135deg, #5F7C17 0%, #7F9F22 100%) !important;
        }}

        .forgot-password {{
            text-align: center;
            margin-top: 18px;
            color: #4B5563;
            font-size: 13px;
        }}

        .divider {{
            display: flex;
            align-items: center;
            margin: 22px 0 18px;
        }}

        .divider::before,
        .divider::after {{
            content: "";
            flex: 1;
            border-bottom: 1px solid #D1D5DB;
        }}

        .divider span {{
            margin: 0 12px;
            color: #6B7280;
            font-size: 13px;
        }}

        .back-link {{
            text-align: center;
            font-size: 14px;
            color: #55751B;
            font-weight: 600;
        }}

        @media (max-width: 520px) {{
            .st-key-login_card {{
                padding: 34px 24px 30px;
            }}
        }}
        </style>

        <div class="login-shell">
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="login_card"):
        st.markdown(
            f'<img class="login-logo" src="data:image/png;base64,{logo_base64}">',
            unsafe_allow_html=True,
        )

        username = st.text_input(
            "Username",
            placeholder="Enter your username",
            key="username",
        )

        password = st.text_input(
            "Password",
            placeholder="Enter your password",
            type="password",
            key="password",
        )

        login_clicked = st.button("LOG IN", key="login_btn")

        st.markdown(
            """
            <div class="forgot-password">Forgot Password?</div>

            <div class="divider">
                <span>or</span>
            </div>

            <div class="back-link">Back to Public Dashboard</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    if login_clicked:
        if username == "admin" and password == "1234":
            st.session_state.role = "lgu"
            st.session_state.page = "Overview"
            st.success("Login successful.")
            st.rerun()
        else:
            st.error("Invalid username or password.")