import os
import json
import gspread
import yfinance as yf
from fredapi import Fred
from datetime import datetime
from google.oauth2.service_account import Credentials

# 1. 환경 변수에서 키 불러오기
fred_key = os.environ['FRED_API_KEY']
gcp_json = json.loads(os.environ['GCP_JSON_KEY'])

# 2. 데이터 수집 (FRED & Yahoo Finance)
fred = Fred(api_key=fred_key)
now = datetime.now().strftime('%Y-%m-%d')

try:
    # 지표 수집
    yield_curve = fred.get_series('T10Y2Y').iloc[-1]
    bei_5y = fred.get_series('T5YIE').iloc[-1]
    credit_spread = fred.get_series('BAMLH0A0HYM2').iloc[-1]
    
    # 구리/금 비율
    copper = yf.Ticker("HG=F").history(period="1d")['Close'].iloc[-1]
    gold = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
    copper_gold = copper / gold
    
    # 시장 금리 프록시 (1개월물)
    rate_proxy = yf.Ticker("^IRX").history(period="1d")['Close'].iloc[-1]
    
    # 데이터 정리
    row = [now, yield_curve, bei_5y, credit_spread, copper_gold, rate_proxy]

    # 3. 구글 시트 적재
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(gcp_json, scopes=scopes)
    client = gspread.authorize(creds)
    
    # 시트 열기 (정해주신 이름 사용)
    sh = client.open("macro_pulse_parameters")
    wks = sh.get_worksheet(0)
    wks.append_row(row)
    
    print(f"✅ {now} 데이터 적재 완료!")

except Exception as e:
    print(f"❌ 오류 발생: {e}")
