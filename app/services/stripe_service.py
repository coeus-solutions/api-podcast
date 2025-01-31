import stripe
from app.config import settings
from app.models.models import User, PaymentHistory, PaymentStatus
from sqlalchemy.orm import Session
from fastapi import HTTPException

stripe.api_key = settings.STRIPE_SECRET_KEY

async def create_checkout_session(db: Session, user: User, token_amount: int) -> str:
    """Create a Stripe checkout session for token purchase"""
    try:
        # Calculate price in cents
        price_in_cents = (token_amount // 1000) * settings.TOKEN_PRICE_PER_1000
        
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'{token_amount} API Tokens',
                        'description': f'Purchase of {token_amount} API tokens for use with our services',
                    },
                    'unit_amount': price_in_cents,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=settings.STRIPE_SUCCESS_URL,
            cancel_url=settings.STRIPE_CANCEL_URL,
            metadata={
                'user_id': user.id,
                'token_amount': token_amount
            }
        )
        
        # Create payment history record
        payment = PaymentHistory(
            user_id=user.id,
            amount=price_in_cents / 100,  # Convert cents to dollars
            tokens=token_amount,
            stripe_session_id=checkout_session.id
        )
        db.add(payment)
        db.commit()
        
        return checkout_session.url
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

async def handle_stripe_webhook(db: Session, signature: str, payload: bytes):
    """Handle Stripe webhook events"""
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, settings.STRIPE_WEBHOOK_SECRET
        )
        
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            
            # Get payment record
            payment = db.query(PaymentHistory).filter_by(
                stripe_session_id=session.id
            ).first()
            
            if payment:
                # Update payment status
                payment.status = PaymentStatus.COMPLETED
                
                # Add tokens to user's account
                user = db.query(User).filter_by(id=payment.user_id).first()
                if user:
                    user.total_tokens += payment.tokens
                
                db.commit()
                
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def calculate_tokens_used(tokens_used: int, db: Session, user: User):
    """Update user's token usage"""
    user.used_tokens += tokens_used
    db.commit() 