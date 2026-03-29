import datetime
from database import Database

def seed():
    db = Database()
    
    # 1. Market Rates
    db.update_market_rates(8250.0, 95.0)
    
    # 2. Example Active Loans
    loans = [
        {
            "receipt_no": 8801,
            "customer_name": "Ramesh Kumar",
            "metal_type": "Gold",
            "weight": 12.50,
            "principal": 50000,
            "rate": 2.0,
            "start_date": datetime.datetime(2025, 1, 23),
            "locker": "Shop Locker",
            "drawer": "A-1"
        },
        {
            "receipt_no": 8802,
            "customer_name": "Anitha S.",
            "metal_type": "Silver",
            "weight": 250.0,
            "principal": 15000,
            "rate": 3.0,
            "start_date": datetime.datetime(2025, 6, 10),
            "locker": "Home Locker",
            "drawer": "B-12"
        }
    ]
    
    for l in loans:
        if not db.get_loan_by_receipt(l['receipt_no']):
            db.add_loan(l)
            print(f"Added sample loan #{l['receipt_no']}")

if __name__ == "__main__":
    seed()
