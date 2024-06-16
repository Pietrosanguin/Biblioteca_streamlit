import streamlit as st
import pandas as pd
import sqlite3
from PIL import Image
import io
import pickle
import pathlib as Path


# Function to create a connection to the SQLite database
def create_connection():
    conn = sqlite3.connect('library.db')
    return conn

# Function to create the books table
def create_table():
    conn = create_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS books
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 title TEXT NOT NULL,
                 author TEXT NOT NULL,
                 genre TEXT NOT NULL,
                 publisher TEXT NOT NULL,
                 city TEXT NOT NULL,
                 year TEXT NOT NULL,
                 cover BLOB,
                 shelf TEXT NOT NULL)''')
    conn.commit()
    conn.close()

# Function to add a new book to the database
def add_book(title, author, genre, publisher, city, year, cover, shelf):
    conn = create_connection()
    c = conn.cursor()
    c.execute('INSERT INTO books (title, author, genre, publisher, city, year, cover, shelf) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', 
              (title, author, genre, publisher, city, year, cover, shelf))
    conn.commit()
    conn.close()

# Function to update a book in the database
def update_book(book_id, title, author, genre, publisher, city, year, shelf):
    conn = create_connection()
    c = conn.cursor()
    c.execute('''UPDATE books 
                 SET title = ?, author = ?, genre = ?, publisher = ?, city = ?, year = ?, shelf = ?
                 WHERE id = ?''', 
              (title, author, genre, publisher, city, year, shelf, book_id))
    conn.commit()
    conn.close()

# Function to delete a book from the database
def delete_book(book_id):
    conn = create_connection()
    c = conn.cursor()
    c.execute('DELETE FROM books WHERE id = ?', (book_id,))
    conn.commit()
    conn.close()

# Function to get all books from the database
def get_all_books():
    conn = create_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM books')
    rows = c.fetchall()
    conn.close()
    return rows

# Function for pagination
def paginate(df, page_size, page_num):
    start_idx = page_size * page_num
    end_idx = start_idx + page_size
    return df.iloc[start_idx:end_idx]