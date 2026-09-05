# Blaze_cartz — Free E-commerce Starter

A professional Flask shopping website designed around:
- 60% Soft Cream `#FAF7F2`
- 30% Deep Slate `#2B2D42`
- 10% Electric Orange `#FF6B35`
- readable charcoal text `#1F2937`

## Included
- Responsive storefront
- Product catalogue and product details
- Cart
- Guest checkout
- Cash on Delivery order creation
- Admin login
- Admin dashboard
- Add/edit/archive products
- Stock fields
- Customer order list
- Order status management
- Revenue/order/product stats
- Render health endpoint
- Supabase-backed persistent data
- Your uploaded Blaze_cartz logo included

## Free architecture
- Render free web service for the Flask app
- Supabase free database for persistent products/orders
- GitHub for source code
- Render supplies an `onrender.com` URL, so a custom domain is not required for testing

## 1. Create Supabase database
Create a free Supabase project, open SQL Editor and run `schema.sql`.

Then copy:
- Project URL -> `SUPABASE_URL`
- Service role key -> `SUPABASE_SERVICE_ROLE_KEY`

Keep the service-role key private. Never put it in browser JavaScript.

## 2. Push to GitHub
Create a repository and upload every file/folder in this project.

## 3. Deploy to Render
Create a new Web Service from the GitHub repo.

Build command:
`pip install -r requirements.txt`

Start command:
`gunicorn app:app --workers 1 --threads 4 --timeout 120`

Choose the free plan.

Add environment variables:
- `SUPABASE_URL` = your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` = your Supabase service-role key
- `FLASK_SECRET_KEY` = a long random secret
- `ADMIN_EMAIL` = your admin email
- `ADMIN_PASSWORD` = a strong admin password

Render will give you a URL such as `https://blaze-cartz.onrender.com`.

## Admin
Open `/admin` on your Render URL and sign in with the environment credentials.

## Important production notes
This starter is genuinely usable for testing and small launches, but before taking significant paid traffic/orders you should add:
- proper customer accounts / password reset
- a production payment gateway such as Razorpay/Stripe
- shipping integration
- image uploads/storage (Supabase Storage is a good next step)
- rate limiting and stronger admin authentication
- order emails/WhatsApp notifications
- privacy policy, terms, refund/return policy and required business/tax details

COD is intentionally used in this zero-cost starter so orders can work without requiring a paid payment gateway account.
