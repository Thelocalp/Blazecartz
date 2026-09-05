import os
import json
import secrets
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import requests

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))

SUPABASE_URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'change-me-now')
STORE_NAME = 'Blaze_cartz'


def sb_headers():
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }


def sb_request(method, table, params=None, data=None):
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError('Supabase is not configured. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.')
    r = requests.request(method, f'{SUPABASE_URL}/rest/v1/{table}', headers=sb_headers(), params=params, json=data, timeout=15)
    if not r.ok:
        raise RuntimeError(f'Supabase error {r.status_code}: {r.text[:500]}')
    return r.json() if r.text else []


def get_products(active_only=True):
    params = {'select': '*', 'order': 'created_at.desc'}
    if active_only:
        params['is_active'] = 'eq.true'
    return sb_request('GET', 'products', params=params)


def get_product(pid):
    rows = sb_request('GET', 'products', {'select': '*', 'id': f'eq.{pid}', 'limit': '1'})
    return rows[0] if rows else None


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login', next=request.path))
        return fn(*args, **kwargs)
    return wrapper


@app.context_processor
def globals_for_templates():
    return {'store_name': STORE_NAME, 'cart_count': len(session.get('cart', [])), 'admin': session.get('admin_logged_in', False)}


@app.route('/')
def home():
    try:
        products = get_products()
    except Exception as e:
        products = []
        flash(str(e), 'error')
    categories = sorted({p.get('category') for p in products if p.get('category')})
    return render_template('home.html', products=products, categories=categories)


@app.route('/product/<int:pid>')
def product(pid):
    p = get_product(pid)
    if not p or not p.get('is_active'):
        return render_template('404.html'), 404
    return render_template('product.html', product=p)


@app.route('/cart')
def cart():
    ids = session.get('cart', [])
    items = []
    for pid in ids:
        p = get_product(pid)
        if p and p.get('is_active'):
            items.append(p)
    return render_template('cart.html', items=items)


@app.post('/cart/add')
def cart_add():
    pid = int(request.form['product_id'])
    p = get_product(pid)
    if not p or not p.get('is_active'):
        flash('Product is unavailable.', 'error')
        return redirect(url_for('home'))
    cart = session.get('cart', [])
    if pid not in cart:
        cart.append(pid)
    session['cart'] = cart
    flash(f"{p['name']} added to your cart.", 'success')
    return redirect(request.referrer or url_for('home'))


@app.post('/cart/remove')
def cart_remove():
    pid = int(request.form['product_id'])
    cart = [x for x in session.get('cart', []) if x != pid]
    session['cart'] = cart
    return redirect(url_for('cart'))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    ids = session.get('cart', [])
    items = [get_product(pid) for pid in ids]
    items = [p for p in items if p and p.get('is_active')]
    if not items:
        flash('Your cart is empty.', 'error')
        return redirect(url_for('home'))
    total = sum(float(p['price']) for p in items)
    if request.method == 'POST':
        data = request.form
        required = ['name', 'phone', 'address', 'city', 'state', 'pincode']
        if any(not data.get(k, '').strip() for k in required):
            flash('Please complete all required delivery fields.', 'error')
            return render_template('checkout.html', items=items, total=total)
        order_number = 'BC-' + datetime.now(timezone.utc).strftime('%y%m%d%H%M%S') + '-' + secrets.token_hex(2).upper()
        payload = {
            'order_number': order_number,
            'customer_name': data['name'].strip(),
            'phone': data['phone'].strip(),
            'email': data.get('email', '').strip() or None,
            'address': data['address'].strip(),
            'city': data['city'].strip(),
            'state': data['state'].strip(),
            'pincode': data['pincode'].strip(),
            'payment_method': data.get('payment_method', 'COD'),
            'items': [{'id': p['id'], 'name': p['name'], 'price': p['price'], 'image_url': p.get('image_url', '')} for p in items],
            'total_amount': total,
            'status': 'New'
        }
        try:
            sb_request('POST', 'orders', data=payload)
            session['cart'] = []
            return render_template('success.html', order_number=order_number, total=total)
        except Exception as e:
            flash(str(e), 'error')
    return render_template('checkout.html', items=items, total=total)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if secrets.compare_digest(request.form.get('email', ''), ADMIN_EMAIL) and secrets.compare_digest(request.form.get('password', ''), ADMIN_PASSWORD):
            session['admin_logged_in'] = True
            return redirect(request.args.get('next') or url_for('admin_dashboard'))
        flash('Invalid admin credentials.', 'error')
    return render_template('admin_login.html')


@app.get('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    products = sb_request('GET', 'products', {'select': '*', 'order': 'created_at.desc'})
    orders = sb_request('GET', 'orders', {'select': '*', 'order': 'created_at.desc'})
    stats = {
        'products': len(products),
        'active': sum(1 for p in products if p.get('is_active')),
        'orders': len(orders),
        'revenue': sum(float(o.get('total_amount') or 0) for o in orders if o.get('status') not in ('Cancelled',))
    }
    return render_template('admin.html', products=products, orders=orders, stats=stats)


@app.post('/admin/product/save')
@admin_required
def admin_product_save():
    form = request.form
    pid = form.get('id')
    payload = {
        'name': form.get('name', '').strip(),
        'description': form.get('description', '').strip(),
        'price': float(form.get('price') or 0),
        'category': form.get('category', '').strip() or 'General',
        'image_url': form.get('image_url', '').strip(),
        'stock': int(form.get('stock') or 0),
        'is_active': form.get('is_active') == 'on'
    }
    if not payload['name'] or payload['price'] < 0:
        flash('Product name and valid price are required.', 'error')
        return redirect(url_for('admin_dashboard'))
    try:
        if pid:
            sb_request('PATCH', 'products', {'id': f'eq.{pid}'}, payload)
            flash('Product updated.', 'success')
        else:
            sb_request('POST', 'products', data=payload)
            flash('Product created.', 'success')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('admin_dashboard'))


@app.post('/admin/product/delete')
@admin_required
def admin_product_delete():
    pid = request.form.get('id')
    try:
        sb_request('PATCH', 'products', {'id': f'eq.{pid}'}, {'is_active': False})
        flash('Product archived.', 'success')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('admin_dashboard'))


@app.post('/admin/order/status')
@admin_required
def admin_order_status():
    oid = request.form.get('id')
    status = request.form.get('status')
    allowed = {'New', 'Confirmed', 'Packed', 'Shipped', 'Delivered', 'Cancelled'}
    if status not in allowed:
        flash('Invalid order status.', 'error')
    else:
        try:
            sb_request('PATCH', 'orders', {'id': f'eq.{oid}'}, {'status': status})
            flash('Order status updated.', 'success')
        except Exception as e:
            flash(str(e), 'error')
    return redirect(url_for('admin_dashboard') + '#orders')


@app.get('/health')
def health():
    return jsonify({'status': 'ok', 'store': STORE_NAME})


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html', error=str(e)), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=False)
