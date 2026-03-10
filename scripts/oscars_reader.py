import time
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# -------------------------
# Settings
# -------------------------

SERVICE_ACCOUNT_FILE = "google_credentials.json"   
SPREADSHEET_NAME = "Oscar Predictions & Wants (Antworten)" 

REFRESH_SECONDS = 10


# -------------------------
# Connection to Google Sheets
# -------------------------

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly"
]

creds = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES
)

client = gspread.authorize(creds)

sheet = client.open(SPREADSHEET_NAME).sheet1


# -------------------------
# Read Data 
# -------------------------

while True:
    print("\n---New Data Loaded---\n")

    data = sheet.get_all_records()

    df = pd.DataFrame(data)

    print(df)

    time.sleep(REFRESH_SECONDS)