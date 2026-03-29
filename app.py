import streamlit as st
import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import plotly.express as px
from fpdf import FPDF
import io
from database import Database

# Page Configuration
st.set_page_config(page_title="Vallalar Jewel Loan", page_icon="💎", layout="wide")

# Custom CSS for Premium & Futuristic Look
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #121212 0%, #1a1a1a 100%);
        color: #e0e0e0;
    }
    .stHeader {
        background: linear-gradient(90deg, #d4af37, #b8860b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        font-family: 'Segoe UI', Roboto, sans-serif;
        font-weight: 800;
        font-size: 3.5rem !important;
        margin-bottom: 0px;
        letter-spacing: 2px;
    }
    .invocation {
        text-align: center;
        color: #d4af37;
        font-style: italic;
        font-size: 1.2rem;
        margin-top: 0px;
        margin-bottom: 40px;
        text-shadow: 0 0 10px rgba(212, 175, 55, 0.3);
    }
    .card {
        background: rgba(255, 255, 255, 0.05);
        padding: 25px;
        border-radius: 20px;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        transition: 0.3s ease-in-out;
    }
    .card:hover {
        transform: translateY(-5px);
        border-color: #d4af37;
    }
    .stButton>button {
        background: linear-gradient(90deg, #d4af37, #b8860b);
        color: white;
        border-radius: 12px;
        padding: 12px 28px;
        font-weight: 700;
        border: none;
        box-shadow: 0 4px 15px rgba(212, 175, 55, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# Initialize Database
@st.cache_resource
def get_db_v7():
    return Database()

db = get_db_v7()

def perform_auto_backup():
    """Silently saves the database to the Desktop/backup/excel folder."""
    import os
    import pandas as pd
    import io
    from datetime import datetime
    
    # 1. Path Setup
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    backup_base = os.path.join(desktop_path, "backup")
    
    # Check if we are on a system with a Desktop folder (likely local PC)
    if not os.path.exists(desktop_path):
        return False, "Skipping local backup (No Desktop folder found - Cloud/Server Environment)"

    backup_dir = os.path.join(backup_base, "excel")
    try:
        os.makedirs(backup_dir, exist_ok=True)
    except Exception:
        return False, "No permission to write to Desktop or folder inaccessible."
    today_str = datetime.now().strftime('%d_%m_%Y')
    target_file = os.path.join(backup_dir, f"{today_str}.xlsx")
    
    # 2. Check if already backed up today
    if os.path.exists(target_file):
        return False, "Backup already exists for today."
        
    try:
        # 3. Fetch Data
        all_loans = list(db.loans.find())
        all_trans = list(db.transactions.find())
        
        if not all_loans:
            return False, "No data to back up."
            
        # 4. Process DataFrames
        df_loans = pd.DataFrame(all_loans)
        df_trans = pd.DataFrame(all_trans) if all_trans else pd.DataFrame()
        
        for df in [df_loans, df_trans]:
            if not df.empty and '_id' in df.columns:
                df['_id'] = df['_id'].astype(str)
            if not df.empty and 'loan_id' in df.columns:
                df['loan_id'] = df['loan_id'].astype(str)
        
        # 5. Save Locally
        with pd.ExcelWriter(target_file, engine='openpyxl') as writer:
            df_loans.to_excel(writer, index=False, sheet_name="Loans")
            if not df_trans.empty:
                df_trans.to_excel(writer, index=False, sheet_name="Transactions")
        
        return True, f"Automated backup saved to Desktop: {today_str}.xlsx"
    except Exception as e:
        return False, f"Automated backup failed: {str(e)}"

# Login & Session Management
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'role' not in st.session_state:
    st.session_state.role = None
if 'page' not in st.session_state:
    st.session_state.page = "Dashboard"

def login_page():
    st.markdown("<div style='max-width:400px; margin:auto;'>", unsafe_allow_html=True)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🔐 System Login")
    with st.form("login"):
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Access System", use_container_width=True):
            user_data = db.authenticate_user(user, pwd)
            if user_data:
                st.session_state.authenticated = True
                st.session_state.username = user_data['username']
                st.session_state.role = user_data.get('role', 'user')
                
                # Activity Tracking
                log_id = db.log_login(user_data['username'])
                st.session_state.log_id = log_id
                
                # TRIGGER AUTO BACKUP ON LOGIN
                success, msg = perform_auto_backup()
                if success:
                    st.toast(f"✅ {msg}")
                
                st.success(f"Welcome, {user_data['username']}!")
                st.rerun()
            else:
                st.error("Invalid credentials.")
    st.markdown("</div></div>", unsafe_allow_html=True)

if not st.session_state.authenticated:
    login_page()
    st.stop()

# Business Header
st.markdown("<h1 class='stHeader'>Vallalar Jewel Loan</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#888; margin-top:-10px; font-weight:bold;'>PAWN BROKER & MONEY LENDER</p>", unsafe_allow_html=True)
st.markdown("<p class='invocation'>\"Arulmigu Sri Angalaparameswari Thunai\"</p>", unsafe_allow_html=True)

# Helper: Duration Calc
def calculate_duration_months(start_date, end_date):
    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
    return months

# Helper: Receipt HTML Generator (For UI Display)
def generate_receipt_html(loan_data, calculation_data):
    issue_date = datetime.date.today().strftime('%d/%m/%Y')
    interest_lines = f"<tr><td>Interest ({calculation_data['months']}m @ {calculation_data['rate']}%):</td><td style='text-align:right;'>₹{calculation_data['interest']:,.2f}</td></tr>" if calculation_data.get('months') else ""
    deductions = f"<tr style='color:red;'><td>Fees/Deductions:</td><td style='text-align:right;'>-₹{calculation_data['deductions']:,.2f}</td></tr>" if calculation_data.get('deductions') else ""
    
    table_content = f"""
        <tr><td>Principal:</td><td style="text-align:right;">₹{loan_data['principal']:,.2f}</td></tr>
        {interest_lines}
        {deductions}
        <tr style="border-top:1px solid #d4af37; font-weight:bold;">
            <td>{calculation_data['total_label']}:</td>
            <td style="text-align:right;">₹{calculation_data['total']:,.2f}</td>
        </tr>
    """
    
    # Store a local copy ONLY if running on a machine with a Desktop
    import os
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.path.exists(desktop_path):
        local_bill_path = os.path.join(desktop_path, "backup", "bill", f"Receipt_{loan_data['receipt_no']}_{loan_data['customer_name'].replace(' ', '_')}.html")
        try:
            os.makedirs(os.path.dirname(local_bill_path), exist_ok=True)
            with open(local_bill_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        except Exception:
            pass # Silently skip on Cloud/Permissions issue
        
    return html_content


# Helper: PDF Generator (Using fpdf2)
def generate_pdf_receipt(loan_data, calculation_data):
    pdf = FPDF(format='A5')
    pdf.add_page()
    # ... (rest of PDF logic continues)


# Helper: PDF Generator (Using fpdf2)
def generate_pdf_receipt(loan_data, calculation_data):
    pdf = FPDF(format='A5')
    pdf.add_page()
    
    # Header
    pdf.set_font("Helvetica", 'B', 16)
    pdf.set_text_color(184, 134, 11)
    pdf.cell(0, 10, "VALLALAR JEWEL LOAN", ln=True, align='C')
    
    pdf.set_font("Helvetica", '', 9)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 5, "Pawn Broker & Money Lender", ln=True, align='C')
    pdf.set_font("Helvetica", 'I', 8)
    pdf.cell(0, 5, '"Arulmigu Sri Angalaparameswari Thunai"', ln=True, align='C')
    
    pdf.line(10, 32, 138, 32)
    pdf.ln(8)
    
    # Body Info Table
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(64, 8, f"Receipt No: #{loan_data['receipt_no']}", border=0)
    pdf.set_font("Helvetica", '', 9)
    now_str = datetime.datetime.now().strftime('%d/%m/%Y %I:%M %p')
    pdf.cell(64, 8, f"Date/Time: {now_str}", border=0, ln=1, align='R')
    
    pdf.ln(2)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 8, f"Customer: {loan_data['customer_name']}", border='B', ln=1)
    pdf.ln(2)
    
    # Financial Data Table
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(90, 10, "Description", border=1, fill=True)
    pdf.cell(38, 10, "Amount (Rs.)", border=1, fill=True, ln=1, align='C')
    
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(90, 10, f"Principal Value ({loan_data['weight']}g {loan_data['metal_type']})", border=1)
    pdf.cell(38, 10, f"{loan_data['principal']:,.2f}", border=1, ln=1, align='R')
    
    if calculation_data.get('months'):
        pdf.cell(90, 10, f"Interest ({calculation_data['months']}m @ {calculation_data['rate']}%)", border=1)
        pdf.cell(38, 10, f"{calculation_data['interest']:,.2f}", border=1, ln=1, align='R')
    
    if calculation_data.get('deductions'):
        pdf.set_text_color(200, 0, 0)
        pdf.cell(90, 10, "Fees / Charges", border=1)
        pdf.cell(38, 10, f"-{calculation_data['deductions']:,.2f}", border=1, ln=1, align='R')
        pdf.set_text_color(0, 0, 0)
    
    pdf.set_font("Helvetica", 'B', 11)
    pdf.set_fill_color(255, 248, 220)
    pdf.cell(90, 12, calculation_data['total_label'], border=1, fill=True)
    pdf.cell(38, 12, f"{calculation_data['total']:,.2f}", border=1, fill=True, ln=1, align='R')
    
    # Signatures
    pdf.ln(15)
    pdf.set_font("Helvetica", 'I', 8)
    pdf.cell(64, 10, "Customer Signature", ln=0)
    pdf.cell(64, 10, "Authorized Signatory", ln=1, align='R')
    
    pdf.set_font("Helvetica", '', 7)
    pdf_content = pdf.output()
    # Store a local copy ONLY if running on a machine with a Desktop
    import os
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.path.exists(desktop_path):
        local_pdf_path = os.path.join(desktop_path, "backup", "bill", f"Receipt_{loan_data['receipt_no']}.pdf")
        try:
            os.makedirs(os.path.dirname(local_pdf_path), exist_ok=True)
            with open(local_pdf_path, "wb") as f:
                f.write(bytes(pdf_content))
        except Exception:
            pass
        
    return bytes(pdf_content)

# Sidebar
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.username}")
    st.markdown(f"Role: **{st.session_state.role.title()}**")
    st.divider()
    
    st.markdown("### 💎 Navigation")
    menu_options = ["Dashboard", "New Loan", "Active Section", "History", "Backup"]
    if st.session_state.role == "admin":
        menu_options.append("User Management")
    
    selected_page = st.selectbox("Go To", menu_options, index=menu_options.index(st.session_state.page) if st.session_state.page in menu_options else 0)
    st.session_state.page = selected_page
    
    st.divider()
    if st.button("Logout", use_container_width=True):
        db.log_logout(st.session_state.get('log_id'))
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.role = None
        st.session_state.log_id = None
        st.rerun()

# Dashboard Page
if st.session_state.page == "Dashboard":
    # 📡 AUTO-SYNC DASHBOARD ON LOAD (Using Cache for speed)
    @st.cache_data(ttl=3600)  # Refresh every hour
    def get_dash_rates():
        y_rates = db.fetch_yfinance_rates()
        history = db.get_yfinance_history(period="1mo")
        xr = db.get_live_exchange_rate()
        return y_rates, history, xr

    col_title, col_refresh = st.columns([4, 1])
    with col_title:
        st.write("### 🌐 Market Intelligence Dashboard")
    with col_refresh:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with st.spinner("⏳ Teleporting latest market data..."):
        y_rates, history_data, ex_rate_inr = get_dash_rates()
    
    # 📡 AUTO-SYNC DASHBOARD ON LOAD
    @st.cache_data(ttl=3600)
    def get_live_dash():
        return db.fetch_web_rates()

    with st.spinner("🚀 Streaming Live Chennai Market..."):
        r = get_live_dash()
    
    db_rates = db.get_market_rates() or {}
    disp_24 = r.get('gold_24k') if (r and r.get('gold_24k')) else db_rates.get('gold_24k', 14902.0)
    disp_22 = r.get('gold_22k') if (r and r.get('gold_22k')) else db_rates.get('gold_22k', 13660.0)
    disp_s = r.get('silver') if (r and r.get('silver')) else db_rates.get('silver', 95.0)

    # Definitive type check for string formatting safety
    try: disp_24 = float(disp_24 or 14902.0)
    except: disp_24 = 14902.0
    try: disp_22 = float(disp_22 or 13660.0)
    except: disp_22 = 13660.0
    try: disp_s = float(disp_s or 95.0)
    except: disp_s = 95.0

    loans = db.get_active_loans()
    total_p = sum(l['principal'] for l in loans)
    
    # Futuristic Metrics Section
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"<div class='card'><p style='color:#888;'>GOLD 24K (Chennai)</p><h2>₹{disp_24:,.2f}</h2><p style='color:#0f0;'>⚡ Market Live</p></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='card'><p style='color:#888;'>GOLD 22K (Chennai)</p><h2>₹{disp_22:,.2f}</h2><p style='color:#0f0;'>⚡ Market Live</p></div>", unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div class='card'><p style='color:#888;'>SILVER (Per Gram)</p><h2>₹{disp_s:,.2f}</h2><p style='color:#0f0;'>⚡ Market Live</p></div>", unsafe_allow_html=True)
    with m4:
        st.markdown(f"<div class='card'><p style='color:#888;'>ACTIVE PORTFOLIO</p><h2>₹{total_p/100000:,.1f}L</h2><p style='color:#d4af37;'>{len(loans)} Active Loans</p></div>", unsafe_allow_html=True)
    
    st.write("---")
    
    # Futuristic Plotly Chart with Real Data
    st.write("### 💎 Worldwide Metal Trends (Last 30 Days - INR)")
    if history_data:
        hist_df = pd.DataFrame(history_data)
        # Convert prices in history to INR for display
        hist_df['gold'] *= ex_rate_inr
        hist_df['silver'] *= ex_rate_inr
        
        fig = px.area(hist_df, x="date", y=["gold", "silver"], 
                      title="Asset Performance Dashboard", 
                      color_discrete_sequence=["#d4af37", "#b0c4de"],
                      template="plotly_dark")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                         xaxis_title="Timeline", yaxis_title="Price per Gram (₹)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📊 Fetching history... (Wait a moment or check connection)")
    
    # Quick Buttons with Functionality
    st.write("### ⚡ Quick Navigation")
    q1, q2 = st.columns(2)
    with q1:
        if st.button("➕ New Loan Placement", use_container_width=True):
            st.session_state.page = "New Loan"
            st.rerun()
    with q2:
        if st.button("🔎 Active Records", use_container_width=True):
            st.session_state.page = "Active Section"
            st.rerun()

# New Loan Page
elif st.session_state.page == "New Loan":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Placement of New Asset Loan")
    
    # Auto Generation Logic
    next_receipt = db.get_next_receipt_no()
    current_time = datetime.datetime.now()
    
    with st.form("new_loan", clear_on_submit=True):
        f1, f2 = st.columns(2)
        with f1:
            receipt_no = st.text_input("Receipt Number", value=next_receipt, help="Auto-filled as DateMonthYear + 001")
            customer = st.text_input("Customer Name (Full)", placeholder="Enter Name")
            metal = st.selectbox("Metal Selection", ["Gold", "Silver"])
            weight = st.number_input("Net Weight (g)", min_value=0.01, step=0.01)
        with f2:
            principal = st.number_input("Principal (₹)", min_value=1)
            def_rate = 2.0 if metal == "Gold" else 3.0
            rate = st.number_input("Monthly Int %", value=def_rate, step=0.1)
            loan_date = st.date_input("Loan Date", value=current_time.date())
            
        st.write("---")
        l1, l2 = st.columns(2)
        with l1: locker = st.selectbox("Storage Locker", ["Shop", "Home", "Tiruvannamalai", "Sankarapuram"])
        with l2: drawer = st.text_input("Drawer/Cabinet No", placeholder="e.g. S-2")
        
        if st.form_submit_button("Finalize & Store Record", use_container_width=True):
            if customer and principal > 0:
                data = {
                    "receipt_no": receipt_no, "customer_name": customer, "metal_type": metal,
                    "weight": weight, "principal": principal, "rate": rate,
                    "start_date": datetime.datetime.combine(loan_date, datetime.time.min),
                    "locker": locker, "drawer": drawer
                }
                db.add_loan(data)
                st.success(f"Success! Record #{next_receipt} established.")
                st.balloons()
            else: st.error("Please provide Name and Principal.")
    st.markdown("</div>", unsafe_allow_html=True)

# Active Section Page
elif st.session_state.page == "Active Section":
    st.subheader("💎 Active Asset Portfolio")
    loans = db.get_active_loans()
    if not loans: st.info("No active records.")
    else:
        df = pd.DataFrame(loans)
        st.dataframe(df[['receipt_no', 'customer_name', 'principal', 'metal_type', 'weight', 'start_date']], use_container_width=True)
        st.divider()
        
        # Receipt Download & Calculation Block
        loan_options = {l['receipt_no']: f"#{l['receipt_no']} - {l['customer_name']}" for l in loans}
        sel_rec = st.selectbox("🔍 Select User / Receipt for Management", 
                             options=list(loan_options.keys()), 
                             format_func=lambda x: loan_options[x],
                             help="You can search by Receipt Number or Customer Name")
        target = db.get_loan_by_receipt(sel_rec)
        
        if target:
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                as_of = st.date_input("Calculation Target Date", value=datetime.date.today())
                months = calculate_duration_months(target['start_date'].date(), as_of)
                
                # Auto-Adjust Rule
                s_rate = float(target['rate'])
                if months > 24: s_rate = 3.0
                elif months > 12: s_rate = 2.5
                
                final_r = st.number_input("Monthly Rate (%)", value=s_rate, step=0.1)
                int_amt = target['principal'] * (final_r / 100) * months
                
                st.write("---")
                ops = ["Full Settlement", "Renewal (Int Only)", "Re-loan (Top-up)"]
                mode = st.radio("Resolution Operation", ops)
                
                receipt_data = {}
                
                if mode == "Full Settlement":
                    total_p = target['principal'] + int_amt
                    st.info(f"Customer to Pay: ₹{total_p:,.2f}")
                    receipt_data = {"months": months, "rate": final_r, "interest": int_amt, "total": total_p, "total_label": "Final Settlement", "deductions": 0}
                    if st.button("Confirm Full Settlement", type="primary", use_container_width=True):
                        db.close_loan(target['_id'], {"paid": total_p, "interest": int_amt})
                        st.success("Loan closed successfully.")
                        st.rerun()

                elif mode == "Renewal (Int Only)":
                    st.info(f"Customer to Pay Interest: ₹{int_amt:,.2f}")
                    receipt_data = {"months": months, "rate": final_r, "interest": int_amt, "total": int_amt, "total_label": "Renewal Receipt", "deductions": 0}
                    if st.button("Confirm Renewal Payment", type="primary", use_container_width=True):
                        db.interest_only_payment(target['_id'], {"int": int_amt})
                        st.success("Interest recorded and loan renewed.")
                        st.rerun()

                elif mode == "Re-loan (Top-up)":
                    new_p = st.number_input("New Principal (₹)", value=float(target['principal'] + 5000), step=500.0)
                    
                    # Logic: New P - Old P - Interest - Chit Fee (5/1000) - 1st Month Int
                    chit_fee = (new_p / 1000) * 5
                    first_m_int = new_p * (final_r / 100)
                    total_deductions = target['principal'] + int_amt + chit_fee + first_m_int
                    payout = new_p - total_deductions
                    
                    st.write(f"**Deductions Breakdown:**")
                    st.write(f"- Old Loan: ₹{target['principal']:,.0f}")
                    st.write(f"- Pending Int: ₹{int_amt:,.0f}")
                    st.write(f"- Chit Fee: ₹{chit_fee:,.0f}")
                    st.write(f"- 1st Month Int (New): ₹{first_m_int:,.0f}")
                    st.divider()
                    
                    if payout >= 0:
                        st.success(f"**Payout to Customer: ₹{payout:,.2f}**")
                    else:
                        st.error(f"**Customer must Pay: ₹{abs(payout):,.2f}**")
                    
                    receipt_data = {"months": months, "rate": final_r, "interest": int_amt, "total": payout, "total_label": "Top-up Payout", "deductions": chit_fee + first_m_int}
                    
                    if st.button("Process Re-loan", type="primary", use_container_width=True):
                        # Create new loan first
                        new_receipt = db.get_next_receipt_no()
                        new_loan_data = target.copy()
                        del new_loan_data['_id']
                        new_loan_data.update({
                            "receipt_no": new_receipt,
                            "principal": new_p,
                            "rate": final_r,
                            "start_date": datetime.datetime.now()
                        })
                        db.re_loan(target['_id'], new_loan_data, payout)
                        st.success(f"Re-loan processed. New Receipt: {new_receipt}")
                        st.rerun()

                st.write("---")
                if st.button("🗑️ Void/Delete This Record", type="secondary", use_container_width=True):
                    db.delete_loan(target['_id'])
                    st.warning("Record deleted from system.")
                    st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)
                
            with c2:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.write("#### 📩 Export Documents")
                
                # PDF Download
                pdf_bytes = generate_pdf_receipt(target, receipt_data)
                st.download_button("📄 Download Official PDF Receipt",
                                  data=pdf_bytes,
                                  file_name=f"Receipt_{target['receipt_no']}.pdf",
                                  mime="application/pdf",
                                  use_container_width=True)
                
                # HTML Download (Optional, keeping as secondary)
                receipt_html = generate_receipt_html(target, receipt_data)
                st.download_button("📩 Download User Receipt (HTML)", 
                                  data=receipt_html, 
                                  file_name=f"Receipt_{target['receipt_no']}_{target['customer_name']}.html",
                                  mime="text/html",
                                  use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

# History Page
elif st.session_state.page == "History":
    st.subheader("📜 Historical Settlements")
    st.write("Records of loans fully settled or re-loaned.")
    
    closed_loans = db.get_closed_loans()
    if not closed_loans:
        st.info("No settled records found yet.")
    else:
        # Prepare table for display
        hist_data = []
        for l in closed_loans:
            hist_data.append({
                "Receipt": l['receipt_no'],
                "Customer": l['customer_name'],
                "Asset": f"{l['weight']}g {l['metal_type']}",
                "Principal": l['principal'],
                "Settled On": l.get('closed_at').strftime("%d/%m/%Y %I:%M %p") if l.get('closed_at') else "N/A",
                "Status": l['status'].title()
            })
        
        df_hist = pd.DataFrame(hist_data)
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
        
        # Details Drilldown
        st.write("---")
        hist_options = {l['Receipt']: f"{l['Receipt']} | 👤 {l['Customer']}" for _, l in df_hist.iterrows()}
        sel_hist = st.selectbox("🔎 Look up Specific Case Details", 
                               options=list(hist_options.keys()), 
                               format_func=lambda x: hist_options[x],
                               help="Search by Receipt or Customer Name")
        target_h = db.get_loan_by_receipt(sel_hist)
        
        if target_h:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.write(f"**Customer:** {target_h['customer_name']}")
                st.write(f"**Loan Date:** {target_h['start_date'].strftime('%d/%m/%Y')}")
                st.write(f"**Closure Date:** {target_h.get('closed_at').strftime('%d/%m/%Y %I:%M %p') if target_h.get('closed_at') else 'N/A'}")
                st.write(f"**Principal:** ₹{target_h['principal']:,.2f}")
                st.markdown("</div>", unsafe_allow_html=True)
            with c2:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.write(f"**Asset:** {target_h['weight']}g {target_h['metal_type']}")
                st.write(f"**Location:** {target_h['locker']} - {target_h['drawer']}")
                st.write(f"**Final Status:** {target_h['status'].upper()}")
                st.markdown("</div>", unsafe_allow_html=True)


# Backup Page
elif st.session_state.page == "Backup":
    st.subheader("🛡️ Data Backup & Export")
    st.write("Download your entire database as a professional Excel document for offline record-keeping.")
    
    with st.container():
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.write("#### 📤 System Data Export (Excel)")
        
        if st.button("📊 Extract Complete Business Data", use_container_width=True):
            # 1. Fetch All Data from Collections
            all_loans = list(db.loans.find())
            all_trans = list(db.transactions.find())
            all_rates = list(db.market_rates.find())
            
            if not all_loans:
                st.warning("No data found to back up.")
            else:
                with st.spinner("Compiling database into Excel format..."):
                    import io
                    
                    # Prepare DataFrames
                    df_loans = pd.DataFrame(all_loans)
                    df_trans = pd.DataFrame(all_trans)
                    df_rates = pd.DataFrame(all_rates)
                    
                    # Clean the data (convert ObjectIds to strings for Excel)
                    for df in [df_loans, df_trans, df_rates]:
                        if not df.empty and '_id' in df.columns:
                            df['_id'] = df['_id'].astype(str)
                        if not df.empty and 'loan_id' in df.columns:
                            df['loan_id'] = df['loan_id'].astype(str)
                    
                    # Buffer for Excel file
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_loans.to_excel(writer, index=False, sheet_name="Loans_Master_Record")
                        if not df_trans.empty:
                            df_trans.to_excel(writer, index=False, sheet_name="Transaction_Logs")
                        if not df_rates.empty:
                            df_rates.to_excel(writer, index=False, sheet_name="Market_Rate_History")
                    
                    processed_data = output.getvalue()
                    
                    st.success("✅ Business data compilation complete!")
                    st.download_button(
                        label="📥 Download System Backup (Excel)",
                        data=processed_data,
                        file_name=f"Vallalar_Jewel_Backup_{datetime.datetime.now().strftime('%d_%m_%Y')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.info("💡 Tip: Download this file daily to maintain an offline copy of your business assets.")

# User Management Page
elif st.session_state.page == "User Management" and st.session_state.role == "admin":
    st.subheader("👥 System User Management")
    
    tab1, tab2, tab3 = st.tabs(["Create New User", "Existing Users", "Activity Logs"])
    
    with tab1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        with st.form("new_user"):
            new_u = st.text_input("Username")
            new_p = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", ["user", "admin"])
            if st.form_submit_button("Register User", use_container_width=True):
                if new_u and new_p:
                    success, msg = db.create_user(new_u, new_p, new_role)
                    if success: st.success(msg)
                    else: st.error(msg)
                else: st.error("Please fill all fields.")
        st.markdown("</div>", unsafe_allow_html=True)
        
    with tab2:
        users = db.get_all_users()
        if not users:
            st.info("No users found.")
        else:
            for u in users:
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1: st.write(f"**👤 {u['username']}** ({u['role']})")
                with c2: st.caption(f"Joined: {u['created_at'].strftime('%d/%m/%Y')}")
                with c3:
                    if st.button(f"🗑️ Delete", key=f"del_{u['username']}"):
                        success, res = db.delete_user(u['_id'])
                        if success: st.success(res); st.rerun()
                        else: st.error(res)
                st.divider()
                
    with tab3:
        logs = db.get_user_activity()
        if logs:
            df_logs = pd.DataFrame(logs)
            df_logs['login_at'] = pd.to_datetime(df_logs['login_at']).dt.strftime('%d/%m/%Y %I:%M %p')
            df_logs['logout_at'] = pd.to_datetime(df_logs['logout_at']).dt.strftime('%d/%m/%Y %I:%M %p').fillna("Active/Unknown")
            st.table(df_logs[['username', 'login_at', 'logout_at']])
        else:
            st.info("No activity recorded yet.")
