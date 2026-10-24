import os
from datetime import date, timedelta

import psycopg2
import psycopg2.extras
from flask import Flask, flash, g, redirect, render_template, request, url_for
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]
metrics = PrometheusMetrics(app)
metrics.info("library_app_info", "Library management app", version="1.0")


def get_db():
    if "db" not in g:
        g.db = psycopg2.connect(
            host=os.environ["DB_HOST"],
            dbname=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            connect_timeout=5,
        )
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def fetch(sql, params=()):
    db = get_db()
    with db, db.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def run(sql, params=()):
    db = get_db()
    with db, db.cursor() as cur:
        cur.execute(sql, params)


@app.route("/")
def index():
    return redirect(url_for("books"))


@app.route("/health")
def health():
    fetch("SELECT 1")
    return {"status": "ok"}


# ---------- Sách ----------
@app.route("/books")
def books():
    q = request.args.get("q", "").strip()
    rows = fetch(
        "SELECT * FROM books WHERE title ILIKE %s OR author ILIKE %s ORDER BY id",
        (f"%{q}%", f"%{q}%"),
    )
    return render_template("books.html", books=rows, q=q)


@app.post("/books/add")
def add_book():
    try:
        run(
            "INSERT INTO books (title, author, isbn, quantity) VALUES (%s,%s,%s,%s)",
            (
                request.form["title"].strip(),
                request.form["author"].strip(),
                request.form.get("isbn", "").strip() or None,
                int(request.form["quantity"]),
            ),
        )
        flash("Đã thêm sách.")
    except (psycopg2.Error, ValueError):
        flash("Không thêm được sách (ISBN trùng hoặc dữ liệu không hợp lệ).")
    return redirect(url_for("books"))


@app.post("/books/<int:book_id>/delete")
def delete_book(book_id):
    try:
        run("DELETE FROM books WHERE id=%s", (book_id,))
        flash("Đã xóa sách.")
    except psycopg2.Error:
        flash("Không xóa được: sách đã có phiếu mượn.")
    return redirect(url_for("books"))


# ---------- Độc giả ----------
@app.route("/members")
def members():
    rows = fetch("SELECT * FROM members ORDER BY id")
    return render_template("members.html", members=rows)


@app.post("/members/add")
def add_member():
    try:
        run(
            "INSERT INTO members (full_name, email, phone) VALUES (%s,%s,%s)",
            (
                request.form["full_name"].strip(),
                request.form.get("email", "").strip() or None,
                request.form.get("phone", "").strip() or None,
            ),
        )
        flash("Đã thêm độc giả.")
    except psycopg2.Error:
        flash("Không thêm được độc giả (email trùng?).")
    return redirect(url_for("members"))


@app.post("/members/<int:member_id>/delete")
def delete_member(member_id):
    try:
        run("DELETE FROM members WHERE id=%s", (member_id,))
        flash("Đã xóa độc giả.")
    except psycopg2.Error:
        flash("Không xóa được: độc giả đã có phiếu mượn.")
    return redirect(url_for("members"))


# ---------- Mượn / trả ----------
@app.route("/loans")
def loans():
    rows = fetch(
        """SELECT l.id, b.title, m.full_name, l.borrowed_at, l.due_date, l.returned_at
           FROM loans l
           JOIN books b ON b.id = l.book_id
           JOIN members m ON m.id = l.member_id
           ORDER BY l.id DESC"""
    )
    return render_template(
        "loans.html",
        loans=rows,
        books=fetch("SELECT id, title, quantity FROM books WHERE quantity > 0 ORDER BY title"),
        members=fetch("SELECT id, full_name FROM members ORDER BY full_name"),
        today=date.today(),
    )


@app.post("/loans/borrow")
def borrow():
    db = get_db()
    try:
        days = int(request.form.get("days", 14))
        with db, db.cursor() as cur:
            cur.execute(
                "UPDATE books SET quantity = quantity - 1 WHERE id=%s AND quantity > 0 RETURNING id",
                (request.form["book_id"],),
            )
            if cur.fetchone() is None:
                raise ValueError("Sách đã hết.")
            cur.execute(
                "INSERT INTO loans (book_id, member_id, due_date) VALUES (%s,%s,%s)",
                (request.form["book_id"], request.form["member_id"], date.today() + timedelta(days=days)),
            )
        flash("Mượn sách thành công.")
    except ValueError as e:
        flash(str(e))
    except psycopg2.Error:
        flash("Lỗi cơ sở dữ liệu khi mượn sách.")
    return redirect(url_for("loans"))


@app.post("/loans/<int:loan_id>/return")
def return_book(loan_id):
    db = get_db()
    try:
        with db, db.cursor() as cur:
            cur.execute(
                "UPDATE loans SET returned_at = CURRENT_DATE WHERE id=%s AND returned_at IS NULL RETURNING book_id",
                (loan_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("Phiếu không tồn tại hoặc đã trả.")
            cur.execute("UPDATE books SET quantity = quantity + 1 WHERE id=%s", (row[0],))
        flash("Trả sách thành công.")
    except ValueError as e:
        flash(str(e))
    except psycopg2.Error:
        flash("Lỗi cơ sở dữ liệu khi trả sách.")
    return redirect(url_for("loans"))
