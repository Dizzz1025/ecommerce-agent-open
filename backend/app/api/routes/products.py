from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import get_product_service
from app.models.schemas import ProductListResponse, ProductResponse
from app.services.product_service import ProductService

router = APIRouter()


@router.get("", response_model=ProductListResponse)
async def list_products(
    q: str | None = Query(default=None, description="Keyword query."),
    category: str | None = Query(default=None),
    sub_category: str | None = Query(default=None),
    brand: str | None = Query(default=None),
    price_min: float | None = Query(default=None, ge=0),
    price_max: float | None = Query(default=None, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    product_service: ProductService = Depends(get_product_service),
) -> ProductListResponse:
    products = product_service.list_products(
        query=q,
        limit=limit,
        category=category,
        sub_category=sub_category,
        brand=brand,
        price_min=price_min,
        price_max=price_max,
    )
    return ProductListResponse(products=products)


@router.get("/{sku_id}", response_model=ProductResponse)
async def get_product(
    sku_id: str,
    product_service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    product = product_service.get_product(sku_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse(product=product)
