import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    file = open("books.csv")
    book_file = csv.reader(file)
    for isbn, title, author, p_year in book_file:
        db.execute("INSERT INTO books (isbn, title, author, pub_year) VALUES (:isbn, :title, :author, :p_year)",
                   {"isbn": isbn, "title": title, "author": author, "p_year": p_year})
    db.commit()
    print(f"Successfully added {isbn}, {title}, {author}, {p_year} to the table - books.")

if __name__ == "__main__":
    main()
