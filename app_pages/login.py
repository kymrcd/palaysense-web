import base64
import streamlit as st


# Function to convert your local image file to a base64 text string
def get_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def login_page():
    # 1. Fetch the logo image and turn it into text format
    logo_base64 = get_base64("assets/logo.png")

    # 2. Inject custom CSS styling to override Streamlit's default layout
    st.markdown(
        f"""
        <style>
        /* Hides all default Streamlit structural bars (Toolbar, footer, running symbol) */
        [data-testid="stSidebar"],
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"] {{
            display: none !important;
            visibility: hidden !important;
        }}

        /* Sets the modern green-to-yellow gradient background on the whole screen */
        [data-testid="stAppViewContainer"] {{
            background: linear-gradient(
                120deg,
                #062B16 0%,
                #1E4A1D 30%,
                #7D9817 68%,
                #F1D85C 100%
            ) !important;
            overflow: hidden !important; /* Disables outer body scrolling */
            height: 100vh !important;
        }}

        /* Stops inner layout containers from creating unwanted scrolling layers */
        .main, .stMain, [data-testid="ScrollToBottomContainer"] {{
            overflow: hidden !important;
            height: 100vh !important;
        }}

        /* Sinisigurado nitong walang white space sa tuktok para sumadsad ang inyong navigation bar */
        .stMainBlockContainer {{
            padding-top: 0rem !important; 
            margin-top: 0px !important;
            padding-bottom: 0rem !important;
            padding-left: 0rem !important;
            padding-right: 0rem !important;
            max-width: 100% !important;
            height: 100vh !important;
            box-sizing: border-box !important;
        }}

        /* 
           THE REAL PARENT CENTER FIX:
           Tinatalo nito ang built-in grids ni Streamlit sa likod ng layout niyo.
           Hinihila nito ang lahat ng laman sa ilalim ng navbar para pumuwesto sa saktong gitna ng screen display.
        */
        [data-testid="stVerticalBlockBorderWrapper"] {{
            display: flex !important;
            justify-content: center !important; /* Pumupuwersa sa pahalang na gitna */
            align-items: center !important;    /* Pumupuwersa sa patayong gitna */
            width: 100vw !important;
            height: calc(100vh - 80px) !important; /* Binabawasan ng sukat ng navbar sa taas */
            margin: 0 auto !important;
        }}

        [data-testid="stVerticalBlock"] {{
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            width: 100% !important;
        }}

        /* COMPACT SOLID WHITE CARD: Maliit at ligtas sa input functions niyo */
        .st-key-login_card {{
            width: 360px !important; 
            max-width: calc(100vw - 32px) !important; 
            background: #FDFDFD !important; 
            border-radius: 12px !important;
            padding: 24px 32px 20px !important; 
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.22) !important; 
            box-sizing: border-box !important;
            margin: 0 auto !important; /* Sinisiguradong walang kiling sa kaliwa o kanan */
        }}

        /* Resizes and centers the logo image inside the white card */
        .login-logo {{
            display: block;
            width: 160px; 
            max-width: 80%;
            margin: 0 auto 16px;
        }}

        /* Styles the "Username" and "Password" text labels */
        div[data-testid="stTextInput"] label {{
            color: #222 !important;
            font-size: 12px !important; 
            font-weight: 600 !important;
        }}

        /* COMPACT INPUT BOXES */
        div[data-testid="stTextInput"] input {{
            height: 40px !important; 
            background-color: #ECECEC !important;
            border: 1px solid transparent !important;
            border-radius: 6px !important;
            color: #111827 !important;
            font-size: 13px !important;
            padding-left: 12px !important;
        }}

        div[data-testid="stTextInput"] input:focus {{
            border: 2px solid #79961C !important;
            box-shadow: none !important;
        }}

        /* COMPACT LOG IN BUTTON */
        .stButton > button {{
            width: 100% !important;
            height: 42px !important; 
            margin-top: 8px !important;
            border: none !important;
            border-radius: 8px !important;
            background: linear-gradient(135deg, #6C8C1A 0%, #88A925 100%) !important;
            color: white !important;
            font-size: 15px !important;
            font-weight: 700 !important;
            letter-spacing: 0.5px !important;
            transition: 0.25s ease !important;
            box-shadow: 0 8px 16px rgba(108, 140, 26, 0.18);
        }}

        .stButton > button:hover {{
            transform: translateY(-1px);
            background: linear-gradient(135deg, #5F7C17 0%, #7F9F22 100%) !important;
        }}

        /* Styles for the helper text links under the login form */
        .forgot-password {{
            text-align: center;
            margin-top: 12px;
            color: #4B5563;
            font-size: 11px;
        }}

        /* COMPACT DIVIDER LINE */
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
            margin: 0 10px;
            color: #6B7280;
            font-size: 11px;
        }}

        .back-link {{
            text-align: center;
            font-size: 12px;
            color: #55751B;
            font-weight: 600;
        }}

        /* Adjusts internal padding for narrow screens like smartphones o maliit na monitor */
        @media (max-width: 768px) {{
            .st-key-login_card {{
                padding: 20px 24px 16px !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 3. Render native elements directly inside the container block
    with st.container(key="login_card"):
        # Injects the base64 logo string into an HTML image element
        st.markdown(
            f'<img class="login-logo" src="data:image/png;base64,{logo_base64}">',
            unsafe_allow_html=True,
        )

        # Standard Streamlit text boxes with keys tied to session management
        username = st.text_input(
            "Username",
            placeholder="Enter your username",
            key="username",
            label_visibility="visible"
        )

        password = st.text_input(
            "Password",
            placeholder="Enter your password",
            type="password",
            key="password",
            label_visibility="visible"
        )

        login_clicked = st.button("LOG IN", key="login_btn")

        # Visual subtext links
        st.markdown(
            """
            <div class="forgot-password">Forgot Password?</div>
            <div class="divider"><span>or</span></div>
            <div class="back-link">Back to Public Dashboard</div>
            """,
            unsafe_allow_html=True,
        )

    # 4. Processing logic for verification and page redirection
    if login_clicked:
        if username == "admin" and password == "1234":
            st.session_state.role = "lgu"
            st.session_state.page = "LGU Dashboard"
            st.success("Login successful.")
            st.rerun()
        else:
            st.error("Invalid username or password.")
