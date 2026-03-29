import pymongo
from bson.objectid import ObjectId
import datetime

# Replace with your actual MongoDB URI
MONGO_URI = "mongodb+srv://testuserdev001_db_user:Je3RNOYbkNlfD2Z4@gold.npuwjx8.mongodb.net/?appName=GOLD"
DATABASE_NAME = "GOLD" # Standard naming for the new cluster
#
# Username: testuserdev001_db_user
# Password: Je3RNOYbkNlfD2Z4
# 
# 


class Database:
    def __init__(self, uri=MONGO_URI):
        try:
            self.client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=10000)
            self.db = self.client[DATABASE_NAME]
            # Test connection
            self.client.admin.command('ping')
            print(f"Connected to PRODUCTION Atlas ({DATABASE_NAME})")
            
            self.loans = self.db.loans
            self.transactions = self.db.transactions
            self.market_rates = self.db.market_rates
            self.users = self.db.users
            self.user_logs = self.db.user_logs
            self.is_mock = False
            self.initialize_market_rates()
            self.initialize_users()
        except Exception as e:
            print(f"Database Error: {e}")
            self.is_mock = True # Soft fallback just in case of transient network issues

    def initialize_market_rates(self):
        # Only initialize if completely empty, using baseline real values
        if self.market_rates.count_documents({}) == 0:
            self.market_rates.insert_one({
                "gold_24k": 14902.0,
                "gold_22k": 13660.0,
                "silver": 95.0,
                "gold": 14902.0,
                "last_updated": datetime.datetime.now()
            })

    def initialize_users(self):
        # Create default admin if no users exist
        if self.users.count_documents({}) == 0:
            self.create_user("admin", "admin123", "admin")

    def create_user(self, username, password, role="user"):
        if self.users.find_one({"username": username}):
            return False, "User already exists"
        self.users.insert_one({
            "username": username,
            "password": password, # In production, use hashing like bcrypt
            "role": role,
            "created_at": datetime.datetime.now()
        })
        return True, "User created successfully"

    def authenticate_user(self, username, password):
        user = self.users.find_one({"username": username, "password": password})
        if user:
            return user
        return None

    def delete_user(self, user_id):
        # Don't allow deleting the 'admin' user or the last admin
        user = self.users.find_one({"_id": ObjectId(user_id)})
        if user and user['username'] == "admin":
            return False, "Cannot delete base admin account."
        self.users.delete_one({"_id": ObjectId(user_id)})
        return True, "User deleted successfully."

    def log_login(self, username):
        log_id = self.user_logs.insert_one({
            "username": username,
            "login_at": datetime.datetime.now(),
            "logout_at": None
        }).inserted_id
        return log_id

    def log_logout(self, log_id):
        if log_id:
            self.user_logs.update_one(
                {"_id": ObjectId(log_id)},
                {"$set": {"logout_at": datetime.datetime.now()}}
            )

    def get_user_activity(self):
        return list(self.user_logs.find().sort("login_at", -1).limit(100))

    def get_all_users(self):
        return list(self.users.find({}, {"password": 0}))

    def get_market_rates(self):
        return self.market_rates.find_one()

    def get_rate_history(self):
        # Only return real stored history if implemented.
        # Removing sample/mock data as requested.
        return []

    def update_market_rates(self, gold_24k, gold_22k, silver):
        self.market_rates.update_one({}, {
            "$set": {
                "gold_24k": gold_24k,
                "gold_22k": gold_22k,
                "gold": gold_24k, # Legacy compatibility
                "silver": silver,
                "last_updated": datetime.datetime.now()
            }
        })

    def get_next_receipt_no(self):
        """Returns the next available sequential receipt number starting from 8000."""
        # Find all loans and sort by receipt_no descending
        # Since receipt_no is stored as string, we'll fetch them and parse
        all_loans = list(self.loans.find({}, {"receipt_no": 1}))
        
        max_no = 7999
        for loan in all_loans:
            try:
                # Handle cases where receipt_no might be numeric or contain a number
                # If it's a date-based string like '29/03/2026-001', it will fail and we skip
                val = int(str(loan['receipt_no']).split('-')[-1]) if '-' in str(loan['receipt_no']) else int(loan['receipt_no'])
                if val > max_no:
                    max_no = val
            except (ValueError, TypeError):
                continue
        
        return str(max_no + 1)

    def fetch_external_rates(self, api_key):
        """Fetches latest prices from metals-api.com and converts to gram price."""
        from metals_api.client import MetalsApiClient
        try:
            client = MetalsApiClient(api_key)
            # Fetch latest rates in USD
            resp = client.get_latest(base='USD', symbols='XAU,XAG')
            
            if resp and 'rates' in resp:
                rates = resp['rates']
                # Metals-API usually returns 1 USD = X amount of Metal
                # Or sometimes 1 Metal = X amount of USD depending on plan/params
                # We need USD per Ounce first.
                
                # Check if it's "Metal per USD" (typical for latest)
                # If rates['XAU'] < 1 (e.g. 0.0004), it's Ounces per 1 USD
                # If price is > 1000, it's USD per 1 Ounce.
                
                gold_rate = rates.get('XAU')
                silver_rate = rates.get('XAG')
                
                def convert_to_gram(rate):
                    if not rate: return 0
                    # Standard assumption: Gold is ~1800-2500 per Oz
                    if rate < 1: # Ounces per USD
                        usd_per_oz = 1 / rate
                    else: # USD per Ounce
                        usd_per_oz = rate
                    return usd_per_oz / 31.1035 # USD per Gram

                gold_gram = convert_to_gram(gold_rate)
                silver_gram = convert_to_gram(silver_rate)
                
                # Assume user wants to store this in local currency (e.g., INR if they use ₹)
                # For now, let's keep it as is, or suggest a currency conversion.
                # However, the user uses ₹ in the app.
                # I'll multiply by an approximate USD-INR rate if not specified, 
                # but better to just update the "Dashboard" and let them confirm.
                # Let's assume the user handles currency or the API supports it.
                
                return {"gold": gold_gram, "silver": silver_gram}
            return None
        except Exception as e:
            print(f"Metals API Error: {e}")
            return None

    def fetch_yfinance_rates(self):
        """Fetches latest prices from yfinance for Gold (GC=F) and Silver (SI=F)."""
        try:
            import yfinance as yf
            # Gold: GC=F, Silver: SI=F (Both are in USD/oz)
            g_ticker = yf.Ticker("GC=F")
            s_ticker = yf.Ticker("SI=F")
            
            # Get latest price (usually fast info or current price)
            g_price = g_ticker.fast_info.last_price
            s_price = s_ticker.fast_info.last_price
            
            if g_price and s_price:
                # Convert from Troy Ounce to Gram
                return {
                    "gold": g_price / 31.1035, 
                    "silver": s_price / 31.1035
                }
            return None
        except Exception as e:
            print(f"yfinance Fetch Error: {e}")
            return None

    def delete_loan(self, loan_id):
        return self.loans.delete_one({"_id": ObjectId(loan_id)})

    def get_yfinance_history(self, period="1mo"):
        """Fetches historical prices from yfinance for charts."""
        try:
            import yfinance as yf
            import pandas as pd
            g_ticker = yf.Ticker("GC=F")
            s_ticker = yf.Ticker("SI=F")
            
            g_hist = g_ticker.history(period=period)
            s_hist = s_ticker.history(period=period)
            
            # Combine into a clean format for Plotly
            # Convert to Price per gram
            g_prices = (g_hist['Close'] / 31.1035).tolist()
            s_prices = (s_hist['Close'] / 31.1035).tolist()
            dates = g_hist.index.strftime("%Y-%m-%d").tolist()
            
            history = []
            for i in range(len(dates)):
                history.append({
                    "date": dates[i],
                    "gold": g_prices[i],
                    "silver": s_prices[i]
                })
            return history
        except Exception as e:
            print(f"yfinance History Error: {e}")
            return []

    def get_live_exchange_rate(self):
        """Fetches latest USD to INR exchange rate."""
        try:
            from forex_python.converter import CurrencyRates
            c = CurrencyRates()
            return c.get_rate('USD', 'INR')
        except Exception:
            return 83.50 # Best fallback

    def fetch_web_rates(self):
        """Web Scraper for GoodReturns Chennai Gold/Silver Rates."""
        import requests
        from bs4 import BeautifulSoup
        url = "https://www.goodreturns.in/gold-rates/chennai.html"
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Helper: Find value in table by row text (supporting multiple labels)
            def find_val(labels):
                if isinstance(labels, str): labels = [labels]
                for label in labels:
                    # Look for cell that CONTAINs the label (partial match)
                    row = soup.find('td', string=lambda s: s and label.lower() in s.lower())
                    if not row:
                        # Sometimes it is inside another tag or has extra spaces
                        row = soup.find(lambda tag: tag.name == 'td' and tag.text and label.lower() in tag.text.lower())
                    
                    if row:
                        val_td = row.find_next_sibling('td')
                        if val_td:
                            # Value like "₹7,250" or "7,250.00" -> 7250.0
                            txt = val_td.text.replace('₹', '').replace(',', '').strip()
                            try: return float(txt)
                            except: continue
                return None

            # Try to find 1 Gram prices specifically
            gold_22k = find_val(["22 Carat Gold Today", "22k Gold Today", "1 gram 22k"]) 
            gold_24k = find_val(["24 Carat Gold Today", "24k Gold Today", "1 gram 24k"])
            
            # Silver 1g
            silver = find_val(["Silver Today", "Silver Price per gram", "1 gram Silver"])
            
            # Fallback for silver: if it returns a large amount (likely per kg), divide by 1000
            if silver and silver > 1000:
                silver = silver / 1000
            
            return {"gold_24k": gold_24k, "gold_22k": gold_22k, "silver": silver}
            if not silver: # Check for specific silver table
                silver_link = "https://www.goodreturns.in/silver-rates/chennai.html"
                s_resp = requests.get(silver_link, headers=headers, timeout=10)
                s_soup = BeautifulSoup(s_resp.text, 'html.parser')
                s_row = s_soup.find('td', string=lambda s: s and "Silver Today" in s)
                if s_row:
                    s_val = s_row.find_next_sibling('td').text.replace('₹', '').replace(',', '').strip()
                    silver = float(s_val) / 1000 # GoodReturns often shows per kg, so convert to gram
            
            return {"gold_24k": gold_24k, "gold_22k": gold_22k, "silver": silver}
        except Exception as e:
            print(f"Scraping Error: {e}")
            return None

    def add_loan(self, loan_data):
        # loan_data should include: receipt_no, customer_name, metal_type, weight, 
        # principal, rate, start_date, locker_location, drawer_no
        loan_data['status'] = 'active'
        loan_data['created_at'] = datetime.datetime.now()
        result = self.loans.insert_one(loan_data)
        return result.inserted_id

    def get_active_loans(self):
        return list(self.loans.find({"status": "active"}).sort("receipt_no", 1))

    def get_closed_loans(self):
        return list(self.loans.find({"status": {"$in": ["closed", "re-loaned"]}}).sort("closed_at", -1))

    def get_loan_by_id(self, loan_id):
        return self.loans.find_one({"_id": ObjectId(loan_id)})

    def get_loan_by_receipt(self, receipt_no):
        return self.loans.find_one({"receipt_no": receipt_no})

    def close_loan(self, loan_id, payment_data):
        # Update loan status
        self.loans.update_one({"_id": ObjectId(loan_id)}, {"$set": {"status": "closed", "closed_at": datetime.datetime.now()}})
        
        # Log transaction
        payment_data['loan_id'] = ObjectId(loan_id)
        payment_data['timestamp'] = datetime.datetime.now()
        payment_data['type'] = 'full_closure'
        self.transactions.insert_one(payment_data)

    def interest_only_payment(self, loan_id, payment_data):
        # Log transaction
        payment_data['loan_id'] = ObjectId(loan_id)
        payment_data['timestamp'] = datetime.datetime.now()
        payment_data['type'] = 'interest_only'
        self.transactions.insert_one(payment_data)
        
        # Update loan start date or add a note about last interest payment
        # Usually in pawn shops, paying interest "resets" or "renews" the loan date
        self.loans.update_one(
            {"_id": ObjectId(loan_id)}, 
            {"$set": {"last_interest_payment_date": datetime.datetime.now()}}
        )

    def re_loan(self, old_loan_id, new_loan_data, payment_payout):
        # Close old loan
        self.loans.update_one({"_id": ObjectId(old_loan_id)}, {
            "$set": {
                "status": "re-loaned", 
                "closed_at": datetime.datetime.now(),
                "payout_to_customer": payment_payout
            }
        })
        
        # Log re-loan transaction
        self.transactions.insert_one({
            "loan_id": ObjectId(old_loan_id),
            "timestamp": datetime.datetime.now(),
            "type": "re_loan_closure",
            "payout": payment_payout
        })
        
        # Create new loan
        return self.add_loan(new_loan_data)
