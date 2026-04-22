from flask import Blueprint, request, jsonify
from models import Car

cars_bp = Blueprint('cars', __name__)


@cars_bp.route('/', methods=['GET'])
def get_cars():
    category = request.args.get('category')
    search = request.args.get('search', '').lower()

    query = Car.query.filter_by(in_stock=True)

    if category and category != 'all':
        query = query.filter_by(category=category)

    cars = query.all()

    if search:
        cars = [c for c in cars if search in c.name.lower() or search in c.brand.lower()]

    return jsonify({'cars': [c.to_dict() for c in cars]}), 200


@cars_bp.route('/<int:car_id>', methods=['GET'])
def get_car(car_id):
    car = Car.query.get_or_404(car_id)
    return jsonify({'car': car.to_dict()}), 200


@cars_bp.route('/featured', methods=['GET'])
def get_featured():
    cars = Car.query.filter_by(in_stock=True).limit(4).all()
    return jsonify({'cars': [c.to_dict() for c in cars]}), 200