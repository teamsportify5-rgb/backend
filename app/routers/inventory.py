from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Inventory
from app.schemas import InventoryCreate, InventoryUpdate, InventoryResponse
from app.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    item_data: InventoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new inventory item. Only admin and manager can create items."""
    if current_user.role.value not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create inventory items"
        )
    
    # Check if item already exists
    existing_item = db.query(Inventory).filter(Inventory.item == item_data.item).first()
    if existing_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item already exists in inventory"
        )
    
    new_item = Inventory(
        item=item_data.item,
        category=item_data.category,
        quantity=item_data.quantity,
        threshold=item_data.threshold,
        unit=item_data.unit
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@router.get("/", response_model=List[InventoryResponse])
async def get_inventory(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all inventory items. Admin and manager can see all, others see limited info."""
    items = db.query(Inventory).offset(skip).limit(limit).all()
    return items


@router.get("/low-stock", response_model=List[InventoryResponse])
async def get_low_stock_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all inventory items where quantity is at or below the threshold."""
    low_stock_items = db.query(Inventory).filter(
        Inventory.quantity <= Inventory.threshold
    ).all()
    return low_stock_items


@router.get("/{item_id}", response_model=InventoryResponse)
async def get_inventory_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific inventory item."""
    item = db.query(Inventory).filter(Inventory.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    return item


@router.put("/{item_id}", response_model=InventoryResponse)
async def update_inventory_item(
    item_id: int,
    item_data: InventoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an inventory item. Only admin and manager can update."""
    if current_user.role.value not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update inventory items"
        )
    
    item = db.query(Inventory).filter(Inventory.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    # Update fields if provided
    if item_data.item is not None:
        # Check if new item name already exists
        existing = db.query(Inventory).filter(Inventory.item == item_data.item, Inventory.id != item_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Item name already exists"
            )
        item.item = item_data.item
    if item_data.category is not None:
        item.category = item_data.category
    if item_data.quantity is not None:
        item.quantity = item_data.quantity
    if item_data.threshold is not None:
        item.threshold = item_data.threshold
    if item_data.unit is not None:
        item.unit = item_data.unit
    
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an inventory item. Only admin can delete."""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete inventory items"
        )
    
    item = db.query(Inventory).filter(Inventory.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    db.delete(item)
    db.commit()
    return None



