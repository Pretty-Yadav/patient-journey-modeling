from fastapi import FastAPI

from api.routes.summary import get_summary

app = FastAPI(
    title="Patient Journey Modeling API",
    description="Starter API for cohort, model, and evaluation summaries.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/summary")
def summary() -> dict:
    return get_summary()


@app.get("/")
def root() -> dict:
    return {"message": "Patient Journey Modeling API"}
