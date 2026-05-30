from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.rf import router as rf_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(rf_router)

for r in app.routes:
    print(
        getattr(r, "path", None),
        getattr(r, "methods", None)
    )