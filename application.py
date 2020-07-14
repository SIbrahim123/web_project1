import os
import requests

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    return render_template("create_account.html")

@app.route("/create_account", methods=["GET", "POST"])
def create_account():
    #Get the user credentials from the form
    if request.method == "POST":
        fullname = request.form.get("fullname")
        new_username = request.form.get("username")
        new_password = request.form.get("password")

        # Ensure that username is unique.
        if db.execute("SELECT username FROM users WHERE username = :name", {"name": new_username}).rowcount == 0:
            db.execute("INSERT INTO users (full_name, username, password) VALUES (:fullname, :username, :password)", {"fullname": fullname, "username": new_username, "password": new_password})
            db.commit()

            # Get the username from the database and store in the session dictionary
            session["username"] = new_username
            flash("You are now logged in", "success")
            return redirect(url_for("profile"))
        else:
            flash("Username already exists.", "error")
            return redirect(url_for("create_account"))

    return redirect(url_for("profile"))

@app.route("/signin")
def signin():
    return render_template("sign_in.html")

@app.route("/sign_in", methods=["POST", "GET"])
def sign_in():
    if request.method == "POST":
        """Get username and passoword from form."""
        user_name = request.form.get("username")
        password = request.form.get("password")

        user = db.execute("SELECT * FROM users WHERE username = :name AND password = :password", {"name":user_name, "password":password}).fetchone()
        # Check if usename and password exists in Database.
        if user is None:
            flash("incorrect username and password ", "error")
            return redirect(url_for("signin"))
        else:
        # Get the user id from the database and store in the session dictionary
            session["username"] = user.username
            flash("You are now logged in", "success")
            return redirect(url_for("profile"))

    else:
        # Get redirected to the profile page if already signed in.
        if "username" in session:
            return redirect(url_for("profile"))

        flash("You need to sign in first.", "info")
        return render_template("sign_in.html")

@app.route("/profile", methods=["GET", "POST"])
def profile():
    #check if user is logged in.
    if "username" in session:
        s_name = session["username"]
        name = db.execute("SELECT full_name FROM users WHERE username = :name", {"name": s_name}).fetchone()
        return render_template("profile.html", name=name.full_name)

    flash("You need to sign_in first before accessing your profile.", "info")
    return redirect(url_for("signin"))


@app.route("/books", methods=["GET", "POST"])
def books():
    if request.method == "POST":
      session_name = session["username"]
      query = request.form.get("query")
      void = "No matching result found."
      hint = 'Search result for '
      name = db.execute(f"SELECT full_name FROM users WHERE username = :name", {"name": session_name}).fetchone()
      result = db.execute(f"SELECT * FROM books WHERE author LIKE '%{query}%' OR title LIKE '%{query}%' OR isbn LIKE '%{query}%'").fetchall()
      if len(result) == 0:
      #if not result:
           return render_template("profile.html", void=void, hint=hint, query=f'{query}', name=name.full_name)
      else:
          return render_template("profile.html", result=result, hint=hint, query=f'{query}', name=name.full_name, title="Title", author="Author")

    return redirect(url_for("profile"))

@app.route("/book_details/<string:book_isbn>", methods=["POST", "GET"])
def book_page(book_isbn):

    reviews = db.execute(f"SELECT title, review, rating, username FROM users JOIN reviews ON users.id=reviews.user_id JOIN books ON books.id=reviews.book_id WHERE isbn LIKE '%{book_isbn}%'").fetchall()#fetch the review from the database.
    book = db.execute(f"SELECT * FROM books WHERE isbn LIKE '%{book_isbn}%'").fetchall()

    my_review = request.form.get("review")
    my_rating = request.form.get("rating")
    session_name = session["username"]
    user_id = db.execute(f"SELECT id FROM users WHERE username = '{session_name}'").fetchone()
    book_id = db.execute(f"SELECT id FROM books WHERE isbn = '{book_isbn}'").fetchone()

    #Goodreads data
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "3GQrO46MvEYSvD3Ml4dXyA", "isbns": f"{book_isbn}"})
    goodreads_dict = res.json()
    goodreads = goodreads_dict["books"][0]
    r_count = goodreads["work_ratings_count"]
    avg_score = goodreads["average_rating"]

    #if the review is empty
    if not my_review:
        return render_template("book_page.html", book=book, reviews=reviews, avg_score=avg_score, r_count=r_count)

    #Add user review to the database if found none
    if not db.execute(f"SELECT * FROM reviews WHERE user_id=:user AND book_id=:book AND rating=:rating", {"user":user_id.id, "book":book_id.id, "rating":my_rating}).fetchone():
        db.execute(f"INSERT INTO reviews (book_id, user_id, review, rating) VALUES ({book_id.id}, {user_id.id}, '{my_review}', {my_rating})")
        db.commit()
        return render_template("book_page.html", book=book, reviews=reviews, avg_score=avg_score, r_count=r_count)
    #if user already made a review
    else:
        return render_template("book_page.html", book=book, reviews=reviews, avg_score=avg_score, r_count=r_count)

    #return redirect(url_for("profile"))

@app.route("/api/<string:book_isbn>", methods=["GET"])
def api(book_isbn):
    row = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn":book_isbn}).fetchone()
    if not row:
        return jsonify({"Error": "ISBN not found"}), 404

    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "3GQrO46MvEYSvD3Ml4dXyA", "isbns": f"{book_isbn}"})

    goodreads_dict = res.json()
    goodreads = goodreads_dict["books"][0]
    review_count = goodreads["work_ratings_count"]
    average_score = goodreads["average_rating"]

    data = {"title":row.title, "author":row.author,"year":row.pub_year, "isbn":row.isbn, "review_count":review_count,"average_score":average_score}

    return jsonify(data)

@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("You are now logged out")
    return redirect(url_for("signin"))


if __name__ == '__main__':
   app.run(debug = True)
