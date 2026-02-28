"""
FriScan — Router Produits
CRUD complet pour la gestion des produits du frigo.
"""
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_

from server.database import get_db
from server.models import (
    ProductDB,
    ProductCreate,
    ProductUpdate,
    ProductResponse,
)

router = APIRouter(prefix="/api/products", tags=["Produits"])


def _enrich_response(product: ProductDB) -> ProductResponse:
    """Enrichit la réponse produit avec les jours avant péremption."""
    resp = ProductResponse.model_validate(product)
    if product.expiry_date:
        delta = product.expiry_date - date.today()
        resp.days_until_expiry = delta.days
    return resp


@router.get("/", response_model=list[ProductResponse])
def list_products(
    in_fridge: Optional[bool] = Query(None, description="Filtrer par présence dans le frigo"),
    expiring_soon: Optional[int] = Query(None, description="Jours avant péremption (alerte)"),
    search: Optional[str] = Query(None, description="Recherche par nom"),
    db: Session = Depends(get_db),
):
    """Liste tous les produits avec filtres optionnels."""
    query = db.query(ProductDB)

    if in_fridge is not None:
        query = query.filter(ProductDB.is_in_fridge == in_fridge)

    if search:
        query = query.filter(ProductDB.name.ilike(f"%{search}%"))

    if expiring_soon is not None:
        limit_date = date.today()
        from datetime import timedelta
        end_date = limit_date + timedelta(days=expiring_soon)
        query = query.filter(
            and_(
                ProductDB.expiry_date.isnot(None),
                ProductDB.expiry_date <= end_date,
                ProductDB.is_in_fridge == True,
            )
        )

    products = query.order_by(ProductDB.expiry_date.asc().nullslast()).all()
    return [_enrich_response(p) for p in products]


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Récupère un produit par son ID."""
    product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    return _enrich_response(product)


@router.post("/", response_model=ProductResponse, status_code=201)
def create_product(product_data: ProductCreate, db: Session = Depends(get_db)):
    """Ajoute un nouveau produit au frigo."""
    product = ProductDB(
        barcode=product_data.barcode,
        name=product_data.name,
        brand=product_data.brand,
        category=product_data.category,
        image_url=product_data.image_url,
        quantity=product_data.quantity,
        nutriscore=product_data.nutriscore,
        expiry_date=product_data.expiry_date,
        amount=product_data.amount,
        added_at=datetime.utcnow(),
        is_in_fridge=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return _enrich_response(product)


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    updates: ProductUpdate,
    db: Session = Depends(get_db),
):
    """Met à jour un produit existant."""
    product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return _enrich_response(product)


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Supprime un produit (le retire définitivement)."""
    product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    db.delete(product)
    db.commit()
    return {"message": f"Produit '{product.name}' supprimé"}


@router.post("/{product_id}/consume")
def consume_product(product_id: int, db: Session = Depends(get_db)):
    """Marque un produit comme consommé (retiré du frigo)."""
    product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")

    if product.amount > 1:
        product.amount -= 1
    else:
        product.is_in_fridge = False

    db.commit()
    db.refresh(product)
    return _enrich_response(product)


@router.get("/stats/summary")
def fridge_summary(db: Session = Depends(get_db)):
    """Résumé du contenu du frigo."""
    from datetime import timedelta

    total = db.query(ProductDB).filter(ProductDB.is_in_fridge == True).count()
    today = date.today()
    expired = db.query(ProductDB).filter(
        and_(
            ProductDB.is_in_fridge == True,
            ProductDB.expiry_date.isnot(None),
            ProductDB.expiry_date < today,
        )
    ).count()
    expiring_3d = db.query(ProductDB).filter(
        and_(
            ProductDB.is_in_fridge == True,
            ProductDB.expiry_date.isnot(None),
            ProductDB.expiry_date >= today,
            ProductDB.expiry_date <= today + timedelta(days=3),
        )
    ).count()

    return {
        "total_products": total,
        "expired": expired,
        "expiring_in_3_days": expiring_3d,
    }
