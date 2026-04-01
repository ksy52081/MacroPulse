import os
import json
import traceback
import requests
import gspread
import yfinance as yf
from fredapi import Fred
from datetime import datetime
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from alarm import send_telegram_message


load_dotenv()

fred_key = os.environ['FRED_API_KEY']
eia_key  = os.environ.get('EIA_API_KEY')
gcp_json = json.loads(os.environ['GCP_JSON_KEY'])

fred = Fred(api_key=fred_key)
date = datetime.now().strftime('%Y-%m-%d')

def get_eia_inventory():
    res = requests.get('https://api.eia.gov/v2/petroleum/stoc/wstk/data/', params={
        'api_key': eia_key,
        'frequency': 'weekly',
        'data[0]': 'value',
        'facets[product][]': 'EPC0',
        'facets[duoarea][]': 'NUS',
        'sort[0][column]': 'period',
        'sort[0][direction]': 'desc',
        'length': 1
    }).json()
    data = res.get('response', {}).get('data', [])
    if not data:
        raise ValueError(f"EIA 원유 재고 응답 오류: {res}")
    return data[0]['value']

try:
    # --- [1/5] 거시·통화 정책 ---
    print("🔄 [1/5] 거시·통화 정책 수집 중...")
    yield_curve    = fred.get_series('T10Y2Y').dropna().iloc[-1]        # 1. 10년-2년 금리차
    bei_5y         = fred.get_series('T5YIE').dropna().iloc[-1]         # 2. 5년 기대인플레이션
    real_rate      = fred.get_series('DFII10').dropna().iloc[-1]        # 3. 10년 실질 금리
    sahm_rule      = fred.get_series('SAHMREALTIME').dropna().iloc[-1]  # 4. 삼 법칙 (Sahm Rule)
    fedfunds       = fred.get_series('FEDFUNDS').dropna().iloc[-1]      # 5. 실효 연방기금금리

    # --- [2/5] 유동성·신용 + 실물 경제 ---
    print("🔄 [2/5] 유동성·신용·실물 경제 수집 중...")
    dxy            = yf.Ticker("DX-Y.NYB").history(period="5d")['Close'].iloc[-1]  # 6. 달러 인덱스
    credit_spread  = fred.get_series('BAMLH0A0HYM2').dropna().iloc[-1]             # 7. 하이일드 스프레드
    mfg_production = fred.get_series('IPMAN').dropna().iloc[-1]                    # 8. 제조업 생산 지수

    # --- [3/5] 금융 섹터 ---
    print("🔄 [3/5] 금융 섹터 수집 중...")
    bank_nim         = fred.get_series('USNIM').dropna().iloc[-1]       # 9. 미국 은행 순이자마진 (NIM)
    bank_delinquency = fred.get_series('DRALACBN').dropna().iloc[-1]    # 10. 상업 은행 연체율
    xlf_pb           = yf.Ticker("XLF").info.get('priceToBook')        # 11. 금융 섹터 P/B (XLF)

    # --- [4/5] 에너지·경기 심리 ---
    print("🔄 [4/5] 에너지·경기 심리 수집 중...")
    cl = yf.Ticker("CL=F").history(period="5d")['Close'].iloc[-1]   # 원유 선물
    rb = yf.Ticker("RB=F").history(period="5d")['Close'].iloc[-1]   # 휘발유 선물
    ho = yf.Ticker("HO=F").history(period="5d")['Close'].iloc[-1]   # 디젤(가열유) 선물
    crack_spread     = (2 * rb * 42 + ho * 42 - 3 * cl) / 3        # 12. 3:2:1 정제마진 (배럴당 달러)
    crude_inventory  = get_eia_inventory()                               # 13. 미국 원유 재고 (전국, EIA)
    oil_extraction   = fred.get_series('IPG211111N').dropna().iloc[-1]  # 14. 석유·가스 추출 생산지수 (동행)
    oil_drilling     = fred.get_series('IPN213111N').dropna().iloc[-1]  # 15. 석유·가스 시추 활동지수 (선행)
    wti_oil          = cl                                                # 16. WTI 원유 현물가격 (CL=F 재사용)
    copper           = yf.Ticker("HG=F").history(period="5d")['Close'].iloc[-1]
    gold             = yf.Ticker("GC=F").history(period="5d")['Close'].iloc[-1]
    copper_gold      = copper / gold                                     # 17. 구리/금 비율

    # --- [5/5] Google Sheets 적재 ---
    print("🔄 [5/5] Google Sheets 적재 중...")
    row = [
        date,
        yield_curve, bei_5y, real_rate, sahm_rule, fedfunds,
        dxy, credit_spread,
        mfg_production,
        bank_nim, bank_delinquency, xlf_pb,
        crack_spread, crude_inventory, oil_extraction, oil_drilling,
        wti_oil, copper_gold
    ]
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(gcp_json, scopes=scopes)
    client = gspread.authorize(creds)
    sh = client.open("macro_pulse_parameters")
    wks = sh.get_worksheet(0)
    wks.append_row(row)

    print(f"✅ {date} 데이터 적재 완료! (총 {len(row)-1}개 지표)")
    send_telegram_message("✅ 데이터 적재 완료!")

except Exception as e:
    print(f"❌ 오류 발생: {e}")
    traceback.print_exc()
