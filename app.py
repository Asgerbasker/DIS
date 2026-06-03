from flask import Flask, render_template, redirect, url_for, session, abort, request, flash
import requests
from bs4 import BeautifulSoup
import psycopg2
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
import os
import glob
import pandas as pd
import random


app = Flask(__name__, static_url_path='/templates')
app.secret_key = "my_secret_key"

def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        port=8888,
        dbname="db",
        user="postgres",
        password="123"
    )
    return conn

@app.route("/")
def home():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT NOW();")
    time = cur.fetchone()
    conn.close()

    return render_template("home.html", time=time)




@app.route("/createaccount", methods=['POST', 'GET'])
def createaccount():
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        new_username = request.form['username']
        new_password = request.form['password']
        cur.execute("SELECT * FROM users WHERE username = %s", (new_username,))
        unique = cur.fetchall()
        flash('Account created!')
        if  len(unique) == 0:
            cur.execute("INSERT INTO users(username, password) VALUES (%s, %s)", (new_username, new_password))
            flash('Account created!')
            conn.commit()

            return redirect(url_for("home"))
        else: 
            flash('Username already exists!')


    return render_template("createaccount.html")


@app.route("/login", methods=['POST', 'GET'])
def login():
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cur.fetchall()
        if len(user) == 1:
            flash('Logged in successfully!')
            return redirect(url_for("search_screen"))
        else: 
            flash('Incorrect username or password!')

    return render_template("login.html")


@app.route("/search_screen", methods=['POST', 'GET'])
def search_screen():
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        word = request.form['word']
        return redirect(url_for("search", word=word))
    return render_template("search_screen.html")




@app.route("/search/<word>")
def search(word):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM word WHERE word = %s", (word,))
    result = cur.fetchall()
    if len(result) == 0:
        flash('Word not found in the dictionary!')
        return redirect(url_for("search_screen"))
    else:
        definition = result[0][2]
        return render_template("search.html", word=word, definition=definition)
    
    
if __name__ == "__main__":
    app.run(debug=True)