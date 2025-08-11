# Django Billing System

A minimal but production-minded Django billing application that supports:

- Product management (with stock, price, and tax percentage)
- Shop denominations management
- Dynamic billing form (add/remove products on the fly)
- Automatic invoice creation with:
  - Total calculation (including tax)
  - Change calculation using available denominations
  - Deducting stock and denominations upon sale
- Asynchronous invoice email sending (prints to console in dev)
- Protected APIs using Django REST Framework (DRF) with Session and Token Authentication


**On the Previous Purchases page**:
   - You can also access it directly via `/previous-purchases/`.
   - Enter the **Customer Email** and click **Search**.
   - A table of all invoices for that customer will appear, showing:
     - Invoice ID
     - Date
     - Total Amount
     - View Items link
   - Clicking **View Items** for a specific invoice will show all products, quantities, prices, taxes, and subtotals for that invoice.

---

## 1. Requirements

- Python **3.9+**
- pip
- SQLite (default) or any Django-supported DB
- (Optional) Virtual environment tool like `venv` or `virtualenv`

---

## 2. Project Setup

### 2.1 Clone or copy the project files
```bash
git clone <your-repo-url> billing_system
cd billing_system
```

### 2.2 Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 2.3 Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt`:
```
Django>=4.2
djangorestframework>=3.14
```

---

## 3. Database Setup

Run migrations to set up the database schema:

```bash
python manage.py migrate
```

Create a superuser (admin account):

```bash
python manage.py createsuperuser
```

---

## 4. Run the Server

```bash
python manage.py runserver
```

Django will start on:  
`http://127.0.0.1:8000/`

---

## 5. Seed Initial Data

### 5.1 Add Products
- Go to: `http://127.0.0.1:8000/admin/`
- Log in with your superuser credentials.
- Add `Product` entries with:
  - **product_id** (unique code)
  - **name**
  - **stock**
  - **price**
  - **tax_pct** (as percentage, e.g., `18.00`)

### 5.2 Add Denominations
Add typical shop denominations (Indian example):

| Value    | Count Available |
|----------|-----------------|
| 2000.00  | 10              |
| 500.00   | 20              |
| 200.00   | 30              |
| 100.00   | 50              |
| 50.00    | 50              |
| 20.00    | 50              |
| 10.00    | 100             |
| 5.00     | 100             |
| 2.00     | 100             |
| 1.00     | 200             |

---

## 6. Using the Web UI

1. **Login** with your admin account (Django Session Auth is used).
2. Visit `/` (root URL) — you’ll see the **Create Bill** form.
3. Enter:
   - **Customer Email**
   - Add product rows (Product ID + Quantity)
   - Paid amount
4. Click **Generate Bill**.
5. The system will:
   - Calculate totals & tax
   - Calculate change based on available denominations
   - Reduce product stock & denomination counts
   - Save the invoice
   - Send an invoice email asynchronously (prints to console in dev)
6. You’ll see a summary with a link to the **Printable Invoice**.

---

## 7. API Documentation

All API endpoints require **authentication** (`IsAuthenticated`).

### 7.1 Authentication Methods

#### Option 1: Session Authentication
- Log into the Django admin or login page in a browser; API calls will work in that session.

#### Option 2: Token Authentication
Obtain a token:
```bash
curl -X POST -d "username=admin&password=yourpass" \
     http://127.0.0.1:8000/api-token-auth/
```
Response:
```json
{"token": "abc123..."}
```

Use token in requests:
```
Authorization: Token abc123...
```

---

### 7.2 Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET,POST | `/api/products/` | List or create products |
| GET,PUT,PATCH,DELETE | `/api/products/{product_id}/` | Retrieve/update/delete product |
| GET,POST | `/api/denominations/` | List or create denominations |
| GET,PUT,PATCH,DELETE | `/api/denominations/{id}/` | Retrieve/update/delete denomination |
| GET | `/api/invoices/` | List invoices |
| GET | `/api/invoices/{id}/` | Retrieve invoice detail |
| POST | `/api/create-invoice/` | Create new invoice |

---

### 7.3 Create Invoice Example

Request:
```http
POST /api/create-invoice/
Authorization: Token abc123...
Content-Type: application/json

{
  "customer_email": "customer@example.com",
  "items": [
    {"product_id": "PROD001", "quantity": 2},
    {"product_id": "PROD002", "quantity": 1}
  ],
  "paid_amount": "500.00"
}
```

Response:
```json
{
  "id": 1,
  "customer_email": "customer@example.com",
  "created_at": "2025-08-11T10:15:30Z",
  "total_without_tax": "300.00",
  "total_tax": "54.00",
  "total_amount": "354.00",
  "paid_amount": "500.00",
  "change_amount": "146.00",
  "denominations_given": {
    "100.00": 1,
    "20.00": 2,
    "5.00": 1,
    "1.00": 1
  },
  "items": [
    {
      "product": 1,
      "name": "Item 1",
      "price": "100.00",
      "tax_amount": "18.00",
      "quantity": 2,
      "subtotal": "236.00"
    }
  ]
}
```

---

## 8. Email Sending

- By default, emails are sent to the console:
  ```
  EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
  DEFAULT_FROM_EMAIL = 'no-reply@example.com'
  ```
- To send real emails, update `EMAIL_BACKEND` in `settings.py` to use SMTP.

---

## 9. CSRF in the Frontend

The billing form uses:
```html
{% csrf_token %}
<script>
  const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
</script>
```
This ensures AJAX `fetch` calls can send:
```js
headers: {
  'Content-Type': 'application/json',
  'X-CSRFToken': csrftoken
}
```
without causing CSRF verification failures.

---

## 10. Development Notes

- **Change Calculation**: Greedy algorithm using `Denomination` table values in descending order, respecting `count_available`.
- **Stock & Denomination Updates**: Deducted upon invoice creation.
- **Concurrency**: In production, wrap invoice creation in `transaction.atomic()` and use `select_for_update()` to prevent race conditions.
- **Async Email**: Implemented via `threading.Thread`. For production, use Celery.

---

## 11. License

This project is provided as-is for educational purposes. No warranty.
