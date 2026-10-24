from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product
from app.schemas import ProductOut

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    """Каталог кредитных продуктов (публичный, без авторизации)."""
    return db.scalars(select(Product).where(Product.is_active).order_by(Product.id)).all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=404, detail="Продукт не найден")
    return product
