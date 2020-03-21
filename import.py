import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


engine = create_engine("postgres://postgres:12345@localhost:5432/vending")
db = scoped_session(sessionmaker(bind=engine))

def main():
    # Create table to import data into
    db.execute("CREATE TABLE tickets (id SERIAL PRIMARY KEY, ticket_id VARCHAR NOT NULL, from_city VARCHAR NOT NULL, to_city VARCHAR NOT NULL, cost FLOAT NOT NULL)")
    db.execute("CREATE TABLE users (user_id SERIAL PRIMARY KEY, firstname VARCHAR NOT NULL, lastname VARCHAR NOT NULL, username VARCHAR NOT NULL, password VARCHAR NOT NULL)")
    db.execute("CREATE TABLE all_tickets (user_id  INTEGER, from_city VARCHAR NOT NULL, to_city VARCHAR NOT NULL, cost FLOAT NOT NULL, date VARCHAR NOT NULL)")

    with open('tickets.csv', 'r') as ticket_csv:
        csv_reader = csv.reader(ticket_csv)

        # Skip first row in csv, since this holds names of columns, not actual data
        next(csv_reader)    

        for ticket_id, from_city, to_city, cost in csv_reader:
            # Insert data in every line into TABLE books
            db.execute("INSERT INTO tickets (ticket_id, from_city, to_city, cost) VALUES (:ticket_id, :from_city, :to_city, :cost)", {'ticket_id': ticket_id, 'from_city': from_city, 'to_city': to_city, 'cost': cost})
        db.commit()

if __name__ == "__main__":
    main()