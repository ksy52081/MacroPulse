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
    # --- [기존 지표] ---
    yield_curve = fred.get_series('T10Y2Y').iloc[-1]        # 장단기 금리차
    bei_5y = fred.get_series('T5YIE').iloc[-1]             # 5년 기대인플레이션
    credit_spread = fred.get_series('BAMLH0A0HYM2').iloc[-1] # 신용 스프레드 (하이일드)
    
    # --- [신규 지표 추가: FRED] ---
    # 1. 실질 금리 (10년물 TIPS 수익률)
    real_rate = fred.get_series('DFII10').iloc[-1]
    # 2. 산업 생산 지수 (PMI 대용치, 월간 데이터의 최신값)
    ind_prod = fred.get_series('INDPRO').iloc[-1]
    # 3. 삼 법칙 경기침체 지표 (0.5 이상이면 침체 진입 신호)
    sahm_rule = fred.get_series('SAHMREALTIME').iloc[-1]
    
    # --- [신규 지표 추가: Yahoo Finance] ---
    # 4. 달러 인덱스 (DXY)
    dxy = yf.Ticker("DX-Y.NYB").history(period="1d")['Close'].iloc[-1]
    # 5. WTI 유가 (인플레이션 공급 압력)
    wti_oil = yf.Ticker("CL=F").history(period="1d")['Close'].iloc[-1]

    # --- [기존 Yahoo Finance 지표] ---
    copper = yf.Ticker("HG=F").history(period="1d")['Close'].iloc[-1]
    gold = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
    copper_gold = copper / gold
    rate_proxy = yf.Ticker("^IRX").history(period="1d")['Close'].iloc[-1] # 13주 국채수익률
    
    # --- 데이터 정리 (총 11개 컬럼) ---
    # 순서: 날짜, 장단기, 기대인플레, 신용스프레드, 구리/금, 시장금리프록시, 실질금리, 산업생산, 삼법칙, 달러인덱스, 유가
    row = [
        date, yield_curve, bei_5y, credit_spread, copper_gold, rate_proxy,
        real_rate, ind_prod, sahm_rule, dxy, wti_oil
    ]

    # 3. 구글 시트 적재
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(gcp_json, scopes=scopes)
    client = gspread.authorize(creds)
    
    sh = client.open("macro_pulse_parameters")
    wks = sh.get_worksheet(0)
    wks.append_row(row)
    
    print(f"✅ {now} 데이터 적재 완료! (총 {len(row)-1}개 지표)")

except Exception as e:
    print(f"❌ 오류 발생: {e}")
