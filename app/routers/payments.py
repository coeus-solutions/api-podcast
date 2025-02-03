from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import User
from app.services import stripe_service
from app.routers.auth import get_current_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class TokenPurchaseRequest(BaseModel):
    token_amount: int

@router.post("/create-checkout")
async def create_checkout_session(
    request: TokenPurchaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a Stripe checkout session for token purchase"""
    if request.token_amount < 1000:
        raise HTTPException(status_code=400, detail="Minimum token purchase is 1000 tokens")
    
    checkout_url = await stripe_service.create_checkout_session(
        db=db,
        user=current_user,
        token_amount=request.token_amount
    )
    
    return {"checkout_url": checkout_url}

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Handle Stripe webhook events"""
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Stripe signature is required")
    
    payload = await request.body()
    return await stripe_service.handle_stripe_webhook(db, stripe_signature, payload) 