import os
from datetime import date
from fastapi import FastAPI, HTTPException, Query, Path
from mangum import Mangum
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

app = FastAPI(
    title="ETF Investment Metrics API",
    description="Snowflake에서 정제된 일별 ETF 투자 지표를 제공하는 엔터프라이즈급 API",
    version="1.0.0"
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://serving_user:serving_password@localhost:5433/etf_service"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# ==========================================
# 🛡️ Pydantic Schema
# ==========================================
class ETFMetricResponse(BaseModel):
    TRADE_DATE: date = Field(..., description="거래 일자 (YYYY-MM-DD)")
    TICKER: str = Field(..., description="ETF 종목 티커 (예: SPY)")
    USD_CLOSE_PRICE: float | None = Field(None, description="USD 기준 종가")
    USD_KRW_RATE: float | None = Field(None, description="당일 원/달러 환율")
    KRW_CLOSE_PRICE: float | None = Field(None, description="KRW 환산 종가")
    USD_DAILY_RETURN_PCT: float | None = Field(None, description="USD 기준 일일 수익률(%)")
    KRW_DAILY_RETURN_PCT: float | None = Field(None, description="KRW 환산 일일 수익률(%)")

# 🎯 제거됨: clean_nan_to_none 함수 (SQLAlchemy가 NULL을 None으로 자동 처리함)

# ==========================================
# 🚀 API Endpoints
# ==========================================
@app.get("/health", tags=["System"])
def health_check():
    """서버 및 데이터베이스 상태를 확인합니다."""
    return {"status": "ok", "message": "Serving DB API is alive"}

@app.get("/metrics/all", response_model=list[ETFMetricResponse], tags=["Metrics"])
def get_all_metrics(
    limit: int = Query(100, ge=1, le=1000, description="가져올 최대 데이터 개수 (최대 1000)"), 
    offset: int = Query(0, ge=0, description="건너뛸 데이터 개수")
):
    try:
        query = text("SELECT * FROM daily_investment_metrics LIMIT :limit OFFSET :offset")
        
        # 🎯 최적화: Pandas 대신 SQLAlchemy Connection 사용
        with engine.connect() as conn:
            result = conn.execute(query, {"limit": limit, "offset": offset})
            # 조회된 Row 객체들을 딕셔너리 리스트로 변환하여 바로 반환
            return [dict(row._mapping) for row in result]
            
    except Exception as e:
        print(f"Database Error: {e}")
        raise HTTPException(status_code=500, detail="데이터베이스 조회 중 오류가 발생했습니다.")

@app.get("/metrics/{ticker}", response_model=list[ETFMetricResponse], tags=["Metrics"])
def get_ticker_metrics(
    ticker: str = Path(..., min_length=1, description="조회할 ETF 티커")
):
    try:
        query = text('SELECT * FROM daily_investment_metrics WHERE UPPER("TICKER") = :ticker')
        
        with engine.connect() as conn:
            result = conn.execute(query, {"ticker": ticker.upper()})
            data = [dict(row._mapping) for row in result]
        
        # 데이터가 없으면 빈 리스트가 되므로 404 처리
        if not data:
            raise HTTPException(status_code=404, detail=f"'{ticker}' 종목의 데이터를 찾을 수 없습니다.")
            
        return data
        
    except HTTPException:
        raise 
    except Exception as e:
        print(f"Internal Error: {e}")
        raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.")

handler = Mangum(app)