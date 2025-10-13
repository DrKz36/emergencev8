"""Test script for beta_report router"""
import sys
sys.path.append('src')

from fastapi import FastAPI
from backend.features.beta_report.router import router

app = FastAPI()
app.include_router(router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    print("Starting test server...")
    print("Test with: curl -X POST http://localhost:8001/api/beta-report -H 'Content-Type: application/json' -d '{\"email\":\"test@test.com\",\"checklist\":{},\"completion\":\"0/55\",\"completionPercentage\":0}'")
    uvicorn.run(app, host="0.0.0.0", port=8001)
