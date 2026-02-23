from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

# สร้างแอป Flask
app = Flask(__name__)

# ตั้งค่า Secret Key สำหรับ Session
app.secret_key = "supersecretkey"

# ตั้งค่า Database (SQLite)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# เชื่อมต่อฐานข้อมูล
db = SQLAlchemy(app)


# =========================
# สร้าง Model (ตารางสินค้า)
# =========================
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<Product {self.name}>"


# =========================
# สร้าง Database อัตโนมัติ
# =========================
with app.app_context():
    db.create_all()


# =========================
# ฟังก์ชัน Seed Data
# =========================
def seed_data():
    # เช็คว่ามีสินค้าในฐานข้อมูลหรือยัง
    if Product.query.first():
        print("มีสินค้าอยู่แล้ว ไม่ต้องเพิ่มข้อมูลตัวอย่าง")
        return

    # ถ้ายังไม่มี → เพิ่มข้อมูลตัวอย่าง
    sample_products = [
        Product(
            name="นาฬิกาโทนชมพู",
            price=990,
            image_url="https://images.unsplash.com/photo-1523275335684-37898b6baf30"
        ),
        Product(
            name="กระเป๋าพาสเทล",
            price=1290,
            image_url="https://images.unsplash.com/photo-1584917865442-de89df76afd3"
        ),
        Product(
            name="รองเท้าสีหวาน",
            price=1590,
            image_url="https://images.unsplash.com/photo-1542291026-7eec264c27ff"
        ),
        Product(
            name="หมวกน่ารัก",
            price=590,
            image_url="https://images.unsplash.com/photo-1521369909029-2afed882baee"
        ),
    ]

    db.session.bulk_save_objects(sample_products)
    db.session.commit()
    print("เพิ่มข้อมูลตัวอย่างเรียบร้อย 🎉")


# เรียกใช้ seed_data เมื่อเริ่มแอป
with app.app_context():
    db.create_all()
    seed_data()  # เรียกฟังก์ชันเพิ่มข้อมูลตัวอย่าง


# Route ทดสอบ
@app.route("/")
def home():
    products = Product.query.all()  # ดึงสินค้าทั้งหมดจาก DB
    cart = session.get("cart", {})
    cart_count = sum(cart.values())  # รวมจำนวนทั้งหมดในตะกร้า
    return render_template("index.html", products=products, cart_count=cart_count)


@app.route('/api/products/<int:product_id>')
def get_product(product_id):
    product = Product.query.get(product_id)
    if product:
        return jsonify({
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "image": product.image_url
        })
    return jsonify({"error": "Not found"}), 404


# =========================
# เส้นทาง Admin (Login)
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "1234":
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            return "Login ไม่ถูกต้อง"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("home"))


# =========================
# เส้นทาง Admin Dashboard
# =========================
@app.route("/admin")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("login"))

    products = Product.query.all()
    return render_template("admin.html", products=products)


@app.route("/add_product", methods=["POST"])
def add_product():
    if not session.get("admin"):
        return redirect(url_for("login"))

    name = request.form["name"]
    price = float(request.form["price"])
    image_url = request.form["image_url"]

    new_product = Product(name=name, price=price, image_url=image_url)
    db.session.add(new_product)
    db.session.commit()

    return redirect(url_for("admin_dashboard"))


@app.route("/delete_product/<int:id>")
def delete_product(id):
    if not session.get("admin"):
        return redirect(url_for("login"))

    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()

    return redirect(url_for("admin_dashboard"))


# =========================
# เส้นทาง Shopping Cart
# =========================
@app.route("/add_to_cart/<int:id>")
def add_to_cart(id):
    if "cart" not in session:
        session["cart"] = {}

    cart = session["cart"]

    if str(id) in cart:
        cart[str(id)] += 1
    else:
        cart[str(id)] = 1

    session.modified = True
    return redirect(url_for("home"))


@app.route("/cart")
def cart():
    cart = session.get("cart", {})
    products = []
    total = 0

    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            subtotal = product.price * quantity
            total += subtotal
            products.append({
                "product": product,
                "quantity": quantity,
                "subtotal": subtotal
            })

    return render_template("cart.html", products=products, total=total)


@app.route("/remove_from_cart/<int:id>")
def remove_from_cart(id):
    if "cart" in session:
        cart = session["cart"]
        if str(id) in cart:
            del cart[str(id)]
            session.modified = True
    
    return redirect(url_for("cart"))


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if request.method == "POST":
        payment_method = request.form.get("payment", "เก็บเงินปลายทาง")
        
        session.pop("cart", None)  # ล้างตะกร้า
        session.modified = True
        
        return render_template("success.html", payment_method=payment_method)

    return render_template("checkout.html")


if __name__ == "__main__":
    app.run(debug=True)
