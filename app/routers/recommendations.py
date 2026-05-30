from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.recommendation_service import run_recommendations
from app import oauth2

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.post("/run")
def trigger_recommendations(
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)  # ← auth add kiya
):
    results = run_recommendations(db)

    if not results:
        return {
            "message": "No recommendations generated.",
            "detail": "Either no passengers have ride history, or no matching future rides found.",
            "recommendations": []
        }

    return {
        "message": f"Recommendations processed for {len(results)} passenger(s).",
        "recommendations": results
    }