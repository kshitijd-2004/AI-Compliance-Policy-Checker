from fastapi import FastAPI

app = FastAPI(title="AI Compliance Policy Checker", description="A tool to check AI models for compliance with various policies.")

@app.get("/health")
def get_health():
    return {"status": "AI Compliance Policy Checker is running."}



