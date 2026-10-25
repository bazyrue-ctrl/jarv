
import os
import secrets
from pathlib import Path

import requests
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_file,
    abort,
    url_for,
)
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

app = Flask(__name__, static_folder="static", template_folder="templates")

# Render environment variables
app.secret_key = os.environ.get("SECRET_KEY", "")

PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
PAYPAL_MODE = os.environ.get("PAYPAL_MODE", "sandbox").lower()

PAYPAL_BASE = (
    "https://api-m.paypal.com"
    if PAYPAL_MODE == "live"
    else "https://api-m.sandbox.paypal.com"
)

CURRENCY = "USD"

# Private product files
PRODUCTS_DIR = Path(__file__).resolve().parent / "private_products"

# Product IDs, prices, and exact filenames
PRODUCTS = {
    "content-planner": {
        "name": "Content Planner",
        "price": "150.00",
        "file": "content_planner.png",
        "mimetype": "image/png",
    },
    "youtube-growth-guide": {
        "name": "YouTube Growth Guide",
        "price": "200.00",
        "file": "youtube_growth_giude.pdf",
        "mimetype": "application/pdf",
    },
}

signer = (
    URLSafeTimedSerializer(app.secret_key, salt="product-download")
    if app.secret_key
    else None
)


def get_paypal_token():
    """Obtain an access token from PayPal."""
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        raise RuntimeError("PayPal credentials are not configured.")

    response = requests.post(
        f"{PAYPAL_BASE}/v1/oauth2/token",
        auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def paypal_api(method, endpoint, payload=None):
    """Make an authenticated PayPal API request."""
    token = get_paypal_token()

    response = requests.request(
        method,
        f"{PAYPAL_BASE}{endpoint}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=25,
    )
    response.raise_for_status()
    return response.json()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/content-planner")
def content_planner():
    return render_template("content_planner.html")


@app.route("/api/paypal/create-order", methods=["POST"])
def create_order():
    if not signer or not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        return jsonify(error="Payment system is not configured."), 503

    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    product = PRODUCTS.get(product_id)

    if not product:
        return jsonify(error="Invalid product."), 400

    try:
        order = paypal_api(
            "POST",
            "/v2/checkout/orders",
            {
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "custom_id": product_id,
                        "description": product["name"],
                        "amount": {
                            "currency_code": CURRENCY,
                            "value": product["price"],
                        },
                    }
                ],
            },
        )

        return jsonify(orderID=order["id"])

    except (requests.RequestException, RuntimeError, KeyError):
        app.logger.exception("PayPal order creation failed")
        return jsonify(
            error="Could not create payment. Please try again."
        ), 502


@app.route("/api/paypal/capture-order", methods=["POST"])
def capture_order():
    if not signer or not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        return jsonify(error="Payment system is not configured."), 503

    data = request.get_json(silent=True) or {}
    order_id = data.get("orderID")

    if not isinstance(order_id, str) or not order_id.strip():
        return jsonify(error="Missing order ID."), 400

    try:
        # Verify the order directly with PayPal.
        order = paypal_api(
            "GET",
            f"/v2/checkout/orders/{order_id}",
        )

        units = order.get("purchase_units", [])

        if len(units) != 1:
            return jsonify(error="Invalid order details."), 400

        product_id = units[0].get("custom_id")
        product = PRODUCTS.get(product_id)

        if not product:
            return jsonify(error="Invalid purchased product."), 400

        # Capture payment if the buyer has approved the order.
        if order.get("status") == "APPROVED":
            order = paypal_api(
                "POST",
                f"/v2/checkout/orders/{order_id}/capture",
                {},
            )
        elif order.get("status") != "COMPLETED":
            return jsonify(error="Payment has not been completed."), 402

        # Confirm capture status and the amount paid.
        if order.get("status") != "COMPLETED":
            return jsonify(error="Payment is not complete."), 402

        units = order.get("purchase_units", [])

        if len(units) != 1:
            return jsonify(error="Payment verification failed."), 400

        captured_product_id = units[0].get("custom_id")

        if captured_product_id != product_id:
            return jsonify(error="Payment verification failed."), 400

        captures = units[0].get("payments", {}).get("captures", [])

        if len(captures) != 1:
            return jsonify(error="Payment verification failed."), 400

        capture = captures[0]
        amount = capture.get("amount", {})

        if (
            capture.get("status") != "COMPLETED"
            or amount.get("currency_code") != CURRENCY
            or amount.get("value") != product["price"]
        ):
            return jsonify(
                error="Payment amount could not be verified."
            ), 402

        # Ensure the corresponding product file exists before issuing a link.
        product_path = (PRODUCTS_DIR / product["file"]).resolve()

        if (
            product_path.parent != PRODUCTS_DIR.resolve()
            or product_path.suffix.lower() not in (".png", ".pdf")
            or not product_path.is_file()
        ):
            app.logger.error("Product file missing: %s", product["file"])
            return jsonify(
                error="Payment succeeded, but the product file is unavailable. Contact support."
            ), 500

        # Generate a signed download link valid for 30 minutes.
        download_token = signer.dumps(
            {
                "product_id": product_id,
                "nonce": secrets.token_urlsafe(16),
            }
        )

        download_url = url_for(
            "download_product",
            token=download_token,
            _external=True,
        )

        return jsonify(
            success=True,
            product=product["name"],
            download_url=download_url,
        )

    except requests.HTTPError:
        app.logger.exception("PayPal payment verification failed")
        return jsonify(
            error="Unable to verify payment. If charged, contact support."
        ), 400

    except (requests.RequestException, RuntimeError, KeyError):
        app.logger.exception("PayPal capture request failed")
        return jsonify(
            error="Payment verification is temporarily unavailable."
        ), 502


@app.route("/download/<token>", methods=["GET"])
def download_product(token):
    if not signer:
        abort(503)

    try:
        data = signer.loads(token, max_age=1800)
    except SignatureExpired:
        return (
            "Your download link has expired. Please contact support.",
            410,
        )
    except BadSignature:
        abort(403)

    product_id = data.get("product_id")
    product = PRODUCTS.get(product_id)

    if not product:
        abort(404)

    product_path = (PRODUCTS_DIR / product["file"]).resolve()

    if (
        product_path.parent != PRODUCTS_DIR.resolve()
        or product_path.suffix.lower() not in (".png", ".pdf")
        or not product_path.is_file()
    ):
        app.logger.error("Product file missing: %s", product["file"])
        abort(404)

    return send_file(
        product_path,
        as_attachment=True,
        download_name=product["file"],
        mimetype=product["mimetype"],
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
    )

