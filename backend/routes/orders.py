from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Order, OrderItem, Car
import random
import string

orders_bp = Blueprint('orders', __name__)


def generate_reference():
    suffix = ''.join(random.choices(string.digits, k=4))
    return f'AV-2026-{suffix}'


@orders_bp.route('/', methods=['POST'])
@jwt_required()
def create_order():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    items = data.get('items', [])
    if not items:
        return jsonify({'error': 'No items in order'}), 400

    total = 0
    order_items = []

    for item in items:
        car = Car.query.get(item['car_id'])
        if not car or not car.in_stock:
            return jsonify({'error': f'Car {item["car_id"]} not available'}), 400
        subtotal = car.price * item['quantity']
        total += subtotal
        order_items.append(OrderItem(
            car_id=car.id,
            quantity=item['quantity'],
            price_at_purchase=car.price
        ))

    vat = total * 0.16
    grand_total = total + vat

    order = Order(
        reference=generate_reference(),
        user_id=user_id,
        total_amount=round(grand_total, 2),
        delivery_address=data.get('delivery_address', ''),
        phone=data.get('phone', ''),
        payment_method=data.get('payment_method', 'mpesa'),
        status='pending'
    )
    db.session.add(order)
    db.session.flush()

    for oi in order_items:
        oi.order_id = order.id
        db.session.add(oi)

    db.session.commit()
    return jsonify({'order': order.to_dict()}), 201


@orders_bp.route('/', methods=['GET'])
@jwt_required()
def get_orders():
    user_id = int(get_jwt_identity())
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
    return jsonify({'orders': [o.to_dict() for o in orders]}), 200


@orders_bp.route('/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    user_id = int(get_jwt_identity())
    order = Order.query.filter_by(id=order_id, user_id=user_id).first_or_404()
    return jsonify({'order': order.to_dict()}), 200