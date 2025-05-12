# app/predict.py
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import joblib

# Pydantic models for request and response
class PredictRequest(BaseModel):
    text: str

class PredictResponse(BaseModel):
    intent: str

# Initialize router
router = APIRouter(
    prefix="/predict",
    tags=["predict"],
    redirect_slashes=False  # <--- добавь это
)

# Paths to trained artifacts
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VECT_PATH = os.path.join(BASE_DIR, "models", "artifacts", "intent_vectorizer.pkl")
MODEL_PATH = os.path.join(BASE_DIR, "models", "artifacts", "intent_model.pkl")

# Load vectorizer and model at startup
try:
    vectorizer = joblib.load(VECT_PATH)
except Exception as e:
    raise RuntimeError(f"Failed to load vectorizer at {VECT_PATH}: {e}")

try:
    model = joblib.load(MODEL_PATH)
except Exception as e:
    raise RuntimeError(f"Failed to load model at {MODEL_PATH}: {e}")

@router.post("", response_model=PredictResponse)
def predict(request: PredictRequest):
    """
    Accepts raw text and returns the predicted intent.
    """
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text provided")

    # Import preprocessing
    from features.preprocessing import clean_text

    # Preprocess input and vectorize
    try:
        cleaned = clean_text(text)
        vec = vectorizer.transform([cleaned])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preprocessing error: {e}")

    # Predict intent
    try:
        intent = model.predict(vec)[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {e}")

    return PredictResponse(intent=intent)
