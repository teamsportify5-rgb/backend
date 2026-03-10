from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Order, OrderStatus, Inventory
from app.schemas import OrderCreate, OrderUpdate, OrderResponse
from app.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify customer exists
    customer = db.query(User).filter(User.id == order_data.customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    new_order = Order(
        customer_id=order_data.customer_id,
        product=order_data.product,
        quantity=order_data.quantity,
        due_date=order_data.due_date,
        status=OrderStatus.PENDING
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return new_order


@router.get("/", response_model=List[OrderResponse])
async def get_orders(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Admin and manager can see all orders
    # Others can only see their own orders
    if current_user.role.value in ["admin", "manager"]:
        orders = db.query(Order).offset(skip).limit(limit).all()
    else:
        orders = db.query(Order).filter(Order.customer_id == current_user.id).offset(skip).limit(limit).all()
    return orders


@router.get("/products", response_model=List[str])
async def get_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of available products from inventory."""
    # Get all inventory items
    inventory_items = db.query(Inventory.item).all()
    product_names = [item[0] for item in inventory_items]
    
    # Also include products from existing orders that might not be in inventory yet
    existing_products = db.query(Order.product).distinct().all()
    existing_product_names = [p[0] for p in existing_products]
    
    # Combine and remove duplicates, then sort
    all_products = sorted(list(set(product_names + existing_product_names)))
    
    return all_products


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check permissions
    if current_user.role.value not in ["admin", "manager"] and order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this order"
        )
    
    return order


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    order_data: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check permissions - workers can only update status
    if current_user.role.value == "worker":
        if order_data.status is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workers can only update order status"
            )
        order.status = order_data.status
    else:
        # Admin, manager, accountant can update all fields
        if order_data.product is not None:
            order.product = order_data.product
        if order_data.quantity is not None:
            order.quantity = order_data.quantity
        if order_data.status is not None:
            order.status = order_data.status
        if order_data.due_date is not None:
            order.due_date = order_data.due_date
    
    db.commit()
    db.refresh(order)
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only admin and manager can delete orders
    if current_user.role.value not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete orders"
        )
    
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    db.delete(order)
    db.commit()
    return None

