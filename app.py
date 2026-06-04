from flask import Flask, render_template, redirect, url_for, session, abort, request, flash
from flask_login import LoginManager, login_user, login_required
from config import Config
from entities import *
from setup import setup_db
import logging
import psycopg2
from docker.errors import APIError, DockerException
import itertools
import operator
from werkzeug.security import check_password_hash, generate_password_hash

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

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def get_user(id):
    return User.get_by_id(id, conn)


@app.route("/", methods=['POST', 'GET'])
@login_required
def search_screen():
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        if query:
            return redirect(url_for("search_screen", query=query))
        return redirect(url_for("search_screen"))

    query = request.args.get('query', '').strip()
    results = _search_words(query) if query else []
    return render_template("search_screen.html", query=query, results=results, result_count=len(results))

@app.route("/signup", methods=['POST', 'GET'])
def createaccount():
    if request.method == "POST":
        new_user = User(
            username=request.form["username"],
            password_hash=generate_password_hash(request.form["password"]))
        existing_user = User.get_by_username(new_user.username, conn)

        if existing_user is None:
            new_user.save(conn)
            flash("Account created!")
            return redirect(url_for("search_screen"))
        else:
            flash("User already exists!")
    return render_template("createaccount.html")


@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method != "POST":
        return render_template("login.html")
    
    username,password = (request.form["username"],request.form["password"])
    user = User.get_by_username(username, conn)
    if user is not None and check_password_hash(user.password_hash, password):
        login_user(user)
        flash('Logged in successfully!')
        return redirect(url_for("search_screen"))

    flash('Incorrect username or password!')
    return render_template("login.html")

def _search_words(query: str) -> list[dict]:
    words = Word.search_words(query, conn)
    return [
        {
            "raw_form": word.raw_form,
            "description": word.description,
            "examples": [ex.text for ex in word.examples],
            "part_of_speech": word.part_of_speech.name,
            **__get_related_words(word.id),
        } for word in words]


def __get_related_words(wordid: int) -> dict[str, list[str]]:
    related_words = Word.get_related_words(wordid, conn)
    grouped = itertools.groupby(related_words, operator.itemgetter(1))
    related = {
        ("synonyms" if relation == int(RelationType.SYNONYM) else "antonyms"): [word for word,_ in value]
        for relation,value in grouped
    }
    if not "synonyms" in related:
        related["synonyms"] = []
    if not "antonyms" in related:
        related["antonyms"] = []
    return related

def __cleanup_container(container_to_cleanup) -> None:
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
    finally:
        conn.close()
        __cleanup_container(container)
