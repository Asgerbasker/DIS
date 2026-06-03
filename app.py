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

# set your own database name, username and password
db = "dbname='cyper' user='postgres' host='localhost' password='123'" #potentially wrong password
conn = psycopg2.connect(db)
cursor = conn.cursor()


bcrypt = Bcrypt(app)


@app.route("/", methods=['POST', 'GET'])
def createaccount():
    cur = conn.cursor()
    if request.method == 'POST':
        new_username = request.form['username']
        new_password = request.form['password']
        cur.execute(f'''select * from users where username = '{new_username}' ''')
        unique = cur.fetchall()
        flash('Account created!')
        if  len(unique) == 0:
            cur.execute(f'''INSERT INTO users(username, password) VALUES ('{new_username}', '{new_password}')''')
            flash('Account created!')
            conn.commit()

            return redirect(url_for("home"))
        else: 
            flash('Username already exists!')


    return render_template("createaccount.html")


@app.route("/login", methods=['POST', 'GET'])
def login():
    cur = conn.cursor()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur.execute(f'''select * from users where username = '{username}' and password = '{password}' ''')
        user = cur.fetchall()
        if len(user) == 1:
            flash('Logged in successfully!')
            return redirect(url_for("home"))
        else: 
            flash('Incorrect username or password!')

    return render_template("login.html")


@app.route("/search_screen", methods=['POST', 'GET'])
def search_screen():
    if request.method == 'POST':
        word = request.form['word']
        return redirect(url_for("search", word=word))
    return render_template("search_screen.html")

if __name__ == "__main__":
    app.run(debug=True)