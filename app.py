from fastapi import FastAPI
import os, requests, pandas as pd

TOKEN = os.getenv("41b3a96dcf48a9f9376c60f7804e3570-68be605e345f3a56e808e32a6b734e3a")
BASE_URL = "https://api-fxpractice.oanda.com"
INSTRUMENT = "XAU_USD"

app = FastAPI()

@app.get("/")
def root():
    return {"status": "online"}

@app.get("/signal")
def signal():
    # minimal placeholder: just prove the API works
    return {"status": "online"}
