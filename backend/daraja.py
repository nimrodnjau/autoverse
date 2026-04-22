import requests
import base64
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET')
SHORTCODE = os.getenv('MPESA_SHORTCODE')
PASSKEY = os.getenv('MPESA_PASSKEY')
CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL')
MPESA_ENV = os.getenv('MPESA_ENV', 'sandbox')

BASE_URL = 'https://sandbox.safaricom.co.ke' if MPESA_ENV == 'sandbox' else 'https://api.safaricom.co.ke'


def get_access_token():
    url = f'{BASE_URL}/oauth/v1/generate?grant_type=client_credentials'
    credentials = base64.b64encode(f'{CONSUMER_KEY}:{CONSUMER_SECRET}'.encode()).decode()
    headers = {'Authorization': f'Basic {credentials}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['access_token']


def generate_password():
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    raw = f'{SHORTCODE}{PASSKEY}{timestamp}'
    password = base64.b64encode(raw.encode()).decode()
    return password, timestamp


def stk_push(phone_number, amount, order_reference):
    """
    Initiates M-Pesa STK Push.
    phone_number: format 2547XXXXXXXX
    amount: integer (KES)
    order_reference: string reference for the order
    """
    token = get_access_token()
    password, timestamp = generate_password()

    # Normalize phone number
    phone = phone_number.strip().replace('+', '').replace(' ', '')
    if phone.startswith('0'):
        phone = '254' + phone[1:]

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    payload = {
        'BusinessShortCode': SHORTCODE,
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': 'CustomerPayBillOnline',
        'Amount': int(amount),
        'PartyA': phone,
        'PartyB': SHORTCODE,
        'PhoneNumber': phone,
        'CallBackURL': CALLBACK_URL,
        'AccountReference': order_reference,
        'TransactionDesc': f'AutoVerse Payment - {order_reference}'
    }

    url = f'{BASE_URL}/mpesa/stkpush/v1/processrequest'
    response = requests.post(url, json=payload, headers=headers)
    return response.json()


def query_stk_status(checkout_request_id):
    token = get_access_token()
    password, timestamp = generate_password()

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    payload = {
        'BusinessShortCode': SHORTCODE,
        'Password': password,
        'Timestamp': timestamp,
        'CheckoutRequestID': checkout_request_id
    }

    url = f'{BASE_URL}/mpesa/stkpushquery/v1/query'
    response = requests.post(url, json=payload, headers=headers)
    return response.json()