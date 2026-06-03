from flask import Flask, render_template, redirect, url_for, session, abort, request, flash
from config import Config
from setup import setup_db
import logging
import psycopg2
from docker.errors import APIError, DockerException


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

app = Flask(__name__, static_url_path='/templates')
app.config.from_object(Config)
app.secret_key = "my_secret_key"
app.logger.handlers = logging.getLogger().handlers
app.logger.setLevel(logging.INFO)

container = None
with app.app_context():
    container = setup_db()

conn = psycopg2.connect(
            host="localhost",
            port=app.config['POSTGRES_PORT'],
            dbname=app.config['POSTGRES_DB'],
            user=app.config['POSTGRES_USER'],
            password=app.config['POSTGRES_PASSWORD'],
        )
cursor = conn.cursor()


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



def cleanup_container(container_to_cleanup) -> None:
    if container_to_cleanup is None:
        return

    try:
        container_to_cleanup.reload()
        if container_to_cleanup.status == "running":
            container_to_cleanup.stop()
        container_to_cleanup.remove()
        app.logger.info("Stopped and removed Postgres container %s", container_to_cleanup.name)
    except (APIError, DockerException) as exc:
        app.logger.warning("Could not fully clean up Postgres container: %s", exc)
    except Exception as exc:
        app.logger.warning("Could not fully clean up Postgres container: %s", exc)

if __name__ == "__main__":
    try:
        app.run(debug=True, use_reloader=False)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
        cleanup_container(container)