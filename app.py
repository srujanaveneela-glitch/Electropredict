"""ElectroPredict Flask application and backend product APIs."""

import json
import os
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, g, jsonify, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from ml.catalogue_seed import CATALOGUE_PRODUCTS
from ml.prediction_service import get_unified_explanation
from ml.recommendation import normalize_category, recommend_products
from ml.utils import category_display_name


app = Flask(__name__)
# Replace this development fallback with a long random environment value before
# deployment: set ELECTROPREDICT_SECRET_KEY=your-random-secret
app.config["SECRET_KEY"] = os.environ.get("ELECTROPREDICT_SECRET_KEY", "development-only-change-this-key")

# Flask keeps instance-specific files out of the source folders. The database
# file is created automatically on the first application start.
DATABASE_PATH = Path(app.instance_path) / "electropredict.db"


def get_db():
    """Return one SQLite connection for the current Flask request."""
    if "database" not in g:
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        g.database = sqlite3.connect(DATABASE_PATH)
        g.database.row_factory = sqlite3.Row
    return g.database


@app.teardown_appcontext
def close_db(error=None):
    """Close the request database connection after Flask finishes."""
    database = g.pop("database", None)
    if database is not None:
        database.close()


def initialize_database():
    """Create the project tables if they do not already exist."""
    database = get_db()
    database.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            original_price REAL NOT NULL,
            rating REAL NOT NULL DEFAULT 0,
            review_count INTEGER NOT NULL DEFAULT 0,
            image_url TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS user_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            action_type TEXT NOT NULL,
            category TEXT,
            price REAL,
            rating REAL,
            discount REAL,
            quantity INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        );

        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, product_id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        );

        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, product_id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'placed',
            total_amount REAL NOT NULL,
            delivery_address TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        );

        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
            review_text TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, product_id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        );

        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            probability REAL NOT NULL,
            prediction_label TEXT NOT NULL,
            model_version TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        );

        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            score REAL,
            reason TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        );
        """
    )
    database.commit()


def seed_products():
    """Insert starter catalogue records once, without replacing later data."""
    expand_catalogue()


def expand_catalogue():
    """Add missing legitimate electronics products without deleting existing rows."""
    database = get_db()
    for product in CATALOGUE_PRODUCTS:
        existing = database.execute(
            "SELECT id FROM products WHERE brand = ? AND name = ?",
            (product[0], product[1]),
        ).fetchone()
        if existing:
            continue
        database.execute(
            """
            INSERT INTO products
            (brand, name, category, description, price, original_price, rating,
             review_count, image_url, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            product,
        )
    database.commit()

@app.route("/api/products")
def api_products():
    """Return active products as JSON with flexible product search.

    Optional query parameters:
    - search: match part of a product name, brand, or category
    - category: return one product category only
    """

    search_text = request.args.get("search", "").strip().lower()
    category = request.args.get("category", "").strip()

    query = """
        SELECT *
        FROM products
        WHERE is_active = 1
    """

    values = []

    if search_text:
        # Make common singular/plural searches work.
        search_terms = {search_text}

        if search_text.endswith("s"):
            search_terms.add(search_text[:-1])
        else:
            search_terms.add(search_text + "s")

        search_conditions = []

        for term in search_terms:
            match = f"%{term}%"

            search_conditions.append(
                "(LOWER(name) LIKE ? OR "
                "LOWER(brand) LIKE ? OR "
                "LOWER(category) LIKE ?)"
            )

            values.extend([match, match, match])

        query += " AND (" + " OR ".join(search_conditions) + ")"

    if category and category.lower() != "all":
        query += " AND LOWER(category) = LOWER(?)"
        values.append(category)

    query += " ORDER BY id"

    rows = get_db().execute(query, values).fetchall()

    return jsonify([dict(row) for row in rows])

def api_error(message, status_code=400):
    """Return one consistent JSON error response."""
    return jsonify({"error": message}), status_code


def current_user_id():
    """Return the logged-in user's ID, or None for a visitor."""
    return session.get("user_id")


def login_required(view_function):
    """Protect JSON endpoints that belong to one signed-in user."""
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if current_user_id() is None:
            return api_error("Please log in to use this feature.", 401)
        return view_function(*args, **kwargs)
    return wrapped_view


def request_json():
    """Return a JSON request body, or a useful error response."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, api_error("Send request data as a JSON object.")
    return data, None


def get_product(product_id):
    """Find an active product by primary key."""
    return get_db().execute(
        "SELECT * FROM products WHERE id = ? AND is_active = 1", (product_id,)
    ).fetchone()


@app.route("/api/products/<int:product_id>")
def api_product_details(product_id):
    """Return one product record for the future dynamic details page."""
    product = get_product(product_id)
    if product is None:
        return api_error("Product not found.", 404)
    return jsonify(dict(product))


@app.route("/api/categories")
def api_categories():
    """Return categories that currently have at least one active product."""
    rows = get_db().execute(
        """
        SELECT category, COUNT(*) AS product_count
        FROM products
        WHERE is_active = 1
        GROUP BY category
        HAVING product_count > 0
        ORDER BY category
        """
    ).fetchall()
    categories = []
    for row in rows:
        canonical = normalize_category(row["category"])
        if not canonical:
            continue
        categories.append(
            {
                "category": row["category"],
                "canonical": canonical,
                "display_name": category_display_name(row["category"]),
                "product_count": row["product_count"],
            }
        )
    return jsonify(categories)


@app.route("/api/recommendations", methods=["GET", "POST"])
def api_recommendations():
    """Return product-specific recommendations within the predicted category."""
    try:
        # ---------------------------------------------------------
        # Existing ML prediction remains completely unchanged.
        # ---------------------------------------------------------
        explanation = get_unified_explanation()

        predicted_category = explanation["recommendation_category"]

        # ---------------------------------------------------------
        # Read request parameters.
        # ---------------------------------------------------------
        payload = (
            request.get_json(silent=True)
            if request.method == "POST"
            else {}
        )

        if not isinstance(payload, dict):
            payload = {}

        limit = payload.get(
            "limit",
            request.args.get("limit", 4)
        )

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 4

        limit = min(50, max(1, limit))

        exclude_id = payload.get(
            "exclude_product_id",
            request.args.get("exclude_product_id")
        )

        try:
            exclude_id = (
                int(exclude_id)
                if exclude_id not in (None, "")
                else None
            )
        except (TypeError, ValueError):
            exclude_id = None

        # ---------------------------------------------------------
        # Load all active catalogue products.
        # ---------------------------------------------------------
        rows = get_db().execute(
            """
            SELECT *
            FROM products
            WHERE is_active = 1
            ORDER BY id
            """
        ).fetchall()

        catalogue_products = [
            dict(row)
            for row in rows
        ]

        # ---------------------------------------------------------
        # Find the EXACT product currently being viewed.
        # ---------------------------------------------------------
        selected_product = None

        if exclude_id is not None:
            selected_product = next(
                (
                    product
                    for product in catalogue_products
                    if int(product.get("id") or 0)
                    == exclude_id
                ),
                None,
            )

        # ---------------------------------------------------------
        # Generate PRODUCT-SPECIFIC recommendations.
        #
        # Random Forest prediction is still only used to determine
        # the predicted category.
        # ---------------------------------------------------------
        result = recommend_products(
            predicted_category,
            catalogue_products,
            selected_product=selected_product,
            exclude_product_id=exclude_id,
            limit=limit,
        )

        # ---------------------------------------------------------
        # Existing explanation metadata.
        # ---------------------------------------------------------
        result["predicted_category_display"] = (
            explanation["predicted_category"]
        )

        result["prediction_probability"] = (
            explanation["prediction_probability"]
        )

        result["explanation"] = {
            "predicted_category": (
                explanation["predicted_category_canonical"]
            ),

            "shap_explained_category": (
                explanation["shap_explained_category"]
            ),

            "gemini_explained_category": (
                explanation["gemini_explained_category"]
            ),

            "recommendation_category": (
                explanation["recommendation_category"]
            ),
        }

        return jsonify(result)

    except ValueError as exc:
        return api_error(str(exc))

    except Exception as exc:
        return api_error(
            f"Could not load recommendations: {exc}",
            500
        )


@app.route("/api/explanation")
def api_explanation():
    """Return friendly SHAP/Gemini evidence for the live Random Forest prediction."""
    try:
        return jsonify(get_unified_explanation())
    except Exception as exc:
        return api_error(f"Could not load explanation: {exc}", 500)


@app.route("/api/register", methods=["POST"])
def api_register():
    """Create a user and start a login session."""
    data, error = request_json()
    if error:
        return error
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    if not name or "@" not in email or len(password) < 6:
        return api_error("Enter a name, a valid email, and a password of at least 6 characters.")
    try:
        cursor = get_db().execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        get_db().commit()
    except sqlite3.IntegrityError:
        return api_error("An account already uses this email address.")
    session.clear()
    session["user_id"] = cursor.lastrowid
    return jsonify({"message": "Account created.", "user": {"id": cursor.lastrowid, "name": name, "email": email}}), 201


@app.route("/api/login", methods=["POST"])
def api_login():
    """Verify an email/password pair and begin a session."""
    data, error = request_json()
    if error:
        return error
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return api_error("Invalid email or password.", 401)
    session.clear()
    session["user_id"] = user["id"]
    return jsonify({"message": "Logged in.", "user": {"id": user["id"], "name": user["name"], "email": user["email"]}})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    """End the current Flask session."""
    session.clear()
    return jsonify({"message": "Logged out."})


@app.route("/api/me")
def api_me():
    """Return the current session user, if one exists."""
    user_id = current_user_id()
    if user_id is None:
        return jsonify({"user": None})
    user = get_db().execute("SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    return jsonify({"user": dict(user) if user else None})


@app.route("/api/wishlist", methods=["GET", "POST"])
@login_required
def api_wishlist():
    """List saved products or add one product to the user's wishlist."""
    user_id = current_user_id()
    database = get_db()
    if request.method == "GET":
        rows = database.execute(
            """SELECT products.* FROM wishlist JOIN products ON products.id = wishlist.product_id
               WHERE wishlist.user_id = ? ORDER BY wishlist.created_at DESC""", (user_id,)
        ).fetchall()
        return jsonify([dict(row) for row in rows])
    data, error = request_json()
    if error:
        return error
    product = get_product(data.get("product_id"))
    if product is None:
        return api_error("Product not found.", 404)
    try:
        database.execute("INSERT INTO wishlist (user_id, product_id) VALUES (?, ?)", (user_id, product["id"]))
        database.commit()
    except sqlite3.IntegrityError:
        return api_error("This product is already in the wishlist.")
    return jsonify({"message": "Product added to wishlist."}), 201


@app.route("/api/wishlist/<int:product_id>", methods=["DELETE"])
@login_required
def api_remove_wishlist(product_id):
    """Remove one product from the signed-in user's wishlist."""
    cursor = get_db().execute("DELETE FROM wishlist WHERE user_id = ? AND product_id = ?", (current_user_id(), product_id))
    get_db().commit()
    if cursor.rowcount == 0:
        return api_error("Wishlist item not found.", 404)
    return jsonify({"message": "Product removed from wishlist."})


@app.route("/api/cart", methods=["GET", "POST"])
@login_required
def api_cart():
    """List cart items or add/increment one product in the cart."""
    user_id = current_user_id()
    database = get_db()
    if request.method == "GET":
        rows = database.execute(
            """SELECT cart.quantity, products.* FROM cart JOIN products ON products.id = cart.product_id
               WHERE cart.user_id = ? ORDER BY cart.created_at DESC""", (user_id,)
        ).fetchall()
        return jsonify([dict(row) for row in rows])
    data, error = request_json()
    if error:
        return error
    product = get_product(data.get("product_id"))
    quantity = data.get("quantity", 1)
    if product is None or not isinstance(quantity, int) or quantity < 1:
        return api_error("Provide a valid product ID and positive integer quantity.")
    database.execute(
        """INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)
           ON CONFLICT(user_id, product_id) DO UPDATE SET quantity = quantity + excluded.quantity""",
        (user_id, product["id"], quantity),
    )
    database.commit()
    return jsonify({"message": "Product added to cart."}), 201


@app.route("/api/cart/<int:product_id>", methods=["PATCH", "DELETE"])
@login_required
def api_cart_item(product_id):
    """Update a cart quantity or remove a cart item."""
    database = get_db()
    if request.method == "DELETE":
        cursor = database.execute("DELETE FROM cart WHERE user_id = ? AND product_id = ?", (current_user_id(), product_id))
        database.commit()
        return (jsonify({"message": "Product removed from cart."}), 200) if cursor.rowcount else api_error("Cart item not found.", 404)
    data, error = request_json()
    if error:
        return error
    quantity = data.get("quantity")
    if not isinstance(quantity, int) or quantity < 1:
        return api_error("Quantity must be a positive integer.")
    cursor = database.execute("UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?", (quantity, current_user_id(), product_id))
    database.commit()
    return (jsonify({"message": "Cart quantity updated."}) if cursor.rowcount else api_error("Cart item not found.", 404))


@app.route("/api/activity", methods=["GET", "POST"])
@login_required
def api_activity():
    """Store or retrieve consent-based interaction records for one user."""
    database = get_db()
    user_id = current_user_id()
    if request.method == "GET":
        rows = database.execute(
            "SELECT * FROM user_activity WHERE user_id = ? ORDER BY created_at DESC LIMIT 100", (user_id,)
        ).fetchall()
        return jsonify([dict(row) for row in rows])
    data, error = request_json()
    if error:
        return error
    action = str(data.get("action_type", "")).lower()
    allowed_actions = {"view", "search", "click", "wishlist", "cart", "purchase", "rating"}
    if action not in allowed_actions:
        return api_error("Use a valid action_type: view, search, click, wishlist, cart, purchase, or rating.")
    product_id = data.get("product_id")
    product = get_product(product_id) if product_id is not None else None
    if product_id is not None and product is None:
        return api_error("Product not found.", 404)
    database.execute(
        """INSERT INTO user_activity (user_id, product_id, action_type, category, price, rating, discount, quantity)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, product_id, action, data.get("category", product["category"] if product else None),
         data.get("price", product["price"] if product else None), data.get("rating"),
         data.get("discount"), data.get("quantity")),
    )
    database.commit()
    return jsonify({"message": "Activity recorded."}), 201


@app.route("/api/ratings", methods=["POST"])
@login_required
def api_rating():
    """Save or replace the signed-in user's product rating."""
    data, error = request_json()
    if error:
        return error
    product = get_product(data.get("product_id"))
    rating = data.get("rating")
    if product is None or not isinstance(rating, int) or not 1 <= rating <= 5:
        return api_error("Provide an existing product ID and a rating from 1 to 5.")
    database = get_db()
    database.execute(
        """INSERT INTO ratings (user_id, product_id, rating, review_text) VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id, product_id) DO UPDATE SET rating=excluded.rating, review_text=excluded.review_text""",
        (current_user_id(), product["id"], rating, str(data.get("review_text", "")).strip()),
    )
    database.execute(
        """UPDATE products SET rating = (SELECT ROUND(AVG(rating), 2) FROM ratings WHERE product_id = ?),
           review_count = (SELECT COUNT(*) FROM ratings WHERE product_id = ?) WHERE id = ?""",
        (product["id"], product["id"], product["id"]),
    )
    database.commit()
    return jsonify({"message": "Rating saved."})


@app.route("/api/checkout", methods=["POST"])
@login_required
def api_checkout():
    """Turn the signed-in user's cart into an order; no payment gateway is used."""
    data, error = request_json()
    if error:
        return error
    address = str(data.get("delivery_address", "")).strip()
    if not address:
        return api_error("A delivery address is required.")
    database = get_db()
    user_id = current_user_id()
    items = database.execute(
        """SELECT cart.product_id, cart.quantity, products.price FROM cart JOIN products
           ON products.id = cart.product_id WHERE cart.user_id = ?""", (user_id,)
    ).fetchall()
    if not items:
        return api_error("Your cart is empty.")
    total = sum(item["quantity"] * item["price"] for item in items)
    try:
        cursor = database.execute(
            "INSERT INTO orders (user_id, total_amount, delivery_address) VALUES (?, ?, ?)",
            (user_id, total, address),
        )
        order_id = cursor.lastrowid
        database.executemany(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
            [(order_id, item["product_id"], item["quantity"], item["price"]) for item in items],
        )
        database.executemany(
            "INSERT INTO user_activity (user_id, product_id, action_type, quantity) VALUES (?, ?, 'purchase', ?)",
            [(user_id, item["product_id"], item["quantity"]) for item in items],
        )
        database.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        database.commit()
    except sqlite3.Error:
        database.rollback()
        return api_error("The order could not be created.", 500)
    return jsonify({"message": "Demo order placed.", "order_id": order_id, "total_amount": total}), 201


@app.route("/api/orders")
@login_required
def api_orders():
    """Return the signed-in user's order history with its order items."""
    database = get_db()
    orders = [dict(row) for row in database.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC", (current_user_id(),)).fetchall()]
    for order in orders:
        rows = database.execute(
            """SELECT order_items.quantity, order_items.unit_price, products.brand, products.name
               FROM order_items JOIN products ON products.id = order_items.product_id WHERE order_id = ?""",
            (order["id"],),
        ).fetchall()
        order["items"] = [dict(row) for row in rows]
    return jsonify(orders)
with app.app_context():
    initialize_database()
    seed_products()


@app.route("/")
def home():
    """Display the ElectroPredict home page."""
    return render_template("index.html")


@app.route("/products")
def products():
    """Display the demo electronics catalogue."""
    return render_template("products.html")


@app.route("/product-details")
def product_details():
    """Display the current demo product detail page."""
    return render_template("product_details.html")


@app.route("/search")
def search():
    """Display the frontend demo search page."""
    return render_template("search.html")


@app.route("/wishlist")
def wishlist():
    """Display the frontend demo wishlist."""
    return render_template("wishlist.html")


@app.route("/cart")
def cart():
    """Display the frontend demo cart."""
    return render_template("cart.html")


@app.route("/checkout")
def checkout():
    """Display the demo checkout page."""
    return render_template("checkout.html")


@app.route("/login")
def login():
    """Display the login interface only; authentication is not active yet."""
    return render_template("login.html")


@app.route("/register")
def register():
    """Display the registration interface only; accounts are not active yet."""
    return render_template("register.html")


@app.route("/profile")
def profile():
    """Display the demo profile dashboard."""
    return render_template("profile.html")


@app.route("/orders")
def orders():
    """Display the demo order history."""
    return render_template("orders.html")


@app.route("/activity")
def activity():
    """Display sample activity records without collecting any data."""
    return render_template("activity.html")


@app.route("/prediction")
def prediction():
    """Display the clearly labelled demo prediction interface."""
    return render_template("prediction.html")


@app.route("/recommendations")
def recommendations():
    """Display manually selected demo recommendations."""
    return render_template("recommendations.html")


@app.route("/explanation")
def explanation():
    """Display the demo XAI explanation interface."""
    return render_template("explanation.html")


@app.route("/about")
def about():
    """Display the research-project information page."""
    return render_template("about.html")


if __name__ == "__main__":
    # debug=True is useful while developing. Turn it off before deployment.
    app.run(debug=True)
