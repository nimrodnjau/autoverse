from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Order, Payment
from daraja import stk_push, query_stk_status

payments_bp = Blueprint('payments', __name__)


@payments_bp.route('/stk-push', methods=['POST'])
@jwt_required()
def initiate_stk():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    order_id = data.get('order_id')
    phone = data.get('phone')

    if not order_id or not phone:
        return jsonify({'error': 'order_id and phone are required'}), 400

    order = Order.query.filter_by(id=order_id, user_id=user_id).first_or_404()

    if order.status == 'paid':
        return jsonify({'error': 'Order already paid'}), 400

    try:
        result = stk_push(phone, order.total_amount, order.reference)
    except Exception as e:
        return jsonify({'error': f'STK Push failed: {str(e)}'}), 500

    if result.get('ResponseCode') == '0':
        payment = Payment(
            order_id=order.id,
            merchant_request_id=result.get('MerchantRequestID'),
            checkout_request_id=result.get('CheckoutRequestID'),
            amount=order.total_amount,
            phone=phone,
            status='pending'
        )
        db.session.add(payment)
        db.session.commit()

        return jsonify({
            'message': 'STK Push sent. Check your phone.',
            'checkout_request_id': result.get('CheckoutRequestID'),
            'merchant_request_id': result.get('MerchantRequestID')
        }), 200
    else:
        return jsonify({'error': result.get('errorMessage', 'STK Push failed')}), 400


@payments_bp.route('/callback', methods=['POST'])
def mpesa_callback():
    """Safaricom sends the payment result here"""
    data = request.get_json()

    try:
        stk_callback = data['Body']['stkCallback']
        merchant_request_id = stk_callback['MerchantRequestID']
        checkout_request_id = stk_callback['CheckoutRequestID']
        result_code = stk_callback['ResultCode']
        result_desc = stk_callback['ResultDesc']

        payment = Payment.query.filter_by(
            checkout_request_id=checkout_request_id
        ).first()

        if not payment:
            return jsonify({'ResultCode': 0, 'ResultDesc': 'Accepted'}), 200

        if result_code == 0:
            callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
            mpesa_receipt = next(
                (i['Value'] for i in callback_metadata if i['Name'] == 'MpesaReceiptNumber'),
                None
            )
            payment.status = 'success'
            payment.mpesa_receipt = mpesa_receipt
            payment.result_desc = result_desc
            payment.order.status = 'paid'
        else:
            payment.status = 'failed'
            payment.result_desc = result_desc

        db.session.commit()

    except Exception as e:
        print('Callback error:', str(e))

    return jsonify({'ResultCode': 0, 'ResultDesc': 'Accepted'}), 200


@payments_bp.route('/status/<checkout_request_id>', methods=['GET'])
@jwt_required()
def check_status(checkout_request_id):
    payment = Payment.query.filter_by(checkout_request_id=checkout_request_id).first_or_404()
    
    if payment.status == 'pending':
        try:
            result = query_stk_status(checkout_request_id)
            if result.get('ResultCode') == '0':
                payment.status = 'success'
                payment.order.status = 'paid'
                db.session.commit()
        except Exception:
            pass

    return jsonify({'payment': payment.to_dict(), 'order_status': payment.order.status}), 200