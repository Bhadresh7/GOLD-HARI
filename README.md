# Vallalar Jewel Loan Management System

A digital billing and interest calculation system for **Vallalar Jewel Loan and Pawn Broker**.

## Features
- **Dashboard**: Real-time market rates (Gold/Silver) and portfolio overview.
- **Loan Placement**: Professional entry for Gold/Silver loans with locker tracking.
- **Interest Calculator**: Automatically scales rates (2% to 3%) based on loan duration.
- **Payment Types**:
  - Full Closure (Principal + Interest)
  - Interest-Only (Loan stays active)
  - **Re-loaning (Top-up)**: Automated calculation of new payouts with Chit Fee (₹5/1k) and first-month interest deductions.
- **Inventory**: Track Shop Locker, Home Locker, and branch offices.
- **Digital Receipts**: Beautifully formatted receipts for every transaction.
- **Exports**: Export active ledgers to Excel.

## Tech Stack
- **Frontend**: Streamlit (Python)
- **Database**: MongoDB
- **Logic**: Custom date-based interest algorithms

## Setup Instructions
1. Ensure MongoDB is running on `localhost:27017` (or update URI in `database.py`).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   streamlit run app.py
   ```

## Invocation
"Arulmigu Sri Angalaparameswari Thunai"
