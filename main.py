from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.rf import router as rf_router, dsp_loop
import asyncio


@asynccontextmanager
async def lifespan(app: FastAPI):

    print("startup")

    task = asyncio.create_task(dsp_loop())

    yield

    print("shutdown")

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)
async def startup():
    print("startup")
    asyncio.create_task(dsp_loop())


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