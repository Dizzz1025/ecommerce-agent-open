from fastapi import APIRouter

from app.api.routes import cart, chat, products, session, voice

api_router = APIRouter()
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(cart.router, prefix="/cart", tags=["cart"])
api_router.include_router(session.router, prefix="/session", tags=["session-debug"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
