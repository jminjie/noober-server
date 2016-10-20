import os
import sqlite3

from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
# from flask.ext.api import status

app = Flask(__name__)
app.config.from_object(__name__)

# load default config and override config from an environment variable
app.config.update(dict(
        DATABASE = os.path.join(app.root_path, 'basic.db'),
        SECRET_KEY='development key',
        USERNAME='admin',
        PASSWORD='defualt'))
app.config.from_envvar('BASIC_SETTINGS', silent=True)

def connect_db():
        rv = sqlite3.connect(app.config['DATABASE'])
        rv.row_factory = sqlite3.Row
        return rv

def init_db():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
                db.cursor().executescript(f.read())
        db.commit()

@app.cli.command('initdb')
def initdb_command():
        init_db()
        print('Initalized the database.')

def get_db():
        """Opens a new database connection if there is none yet for the current application context.
        """
        if not hasattr(g, 'sqlite_db'):
                g.sqlite_db = connect_db()
        return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
        """Closes the database again at the end of the request."""
        if hasattr(g, 'sqlite_db'):
                g.sqlite_db.close()

@app.route("/noober/driver")
def request_driver():
        if "coords" not in request.args:
                return 'Missing coords query param'
        coords = request.args.get('coords').split(',')
        if len(coords) != 2 or not isinstance(coords[0], (float, int)) or not isinstance(coords[1], (float, int)):
                return 'coords incorrectly formatted'

        db = get_db()
        db.execute('insert into entries (lat, long) values (?,?)',
                   [coords[0], coords[1]])
        db.commit()
        flash('New entry successfully posted')
        return redirect(url_for('show_entries'))

@app.route("/noober/show_entries")
def show_entries():
        db = get_db()
        cur = db.execute('select lat, long from entries')
        entries = cur.fetchall()
        return render_template('show_entries.html', entries=entries)

@app.route("/noober/rider")
def request_rider():
        if "coords" not in request.args:
                return 'Missing coords query param'
        coords = request.args.get('coords').split(',')
        if len(coords) != 2 or not isinstance(coords[0], (float, int)) or not isinstance(coords[1], (float, int)):                return 'coords incorrectly formatted'
        # TODO: implement rider request logic.
        return "Hello driver! Sending rider to you!"


        
if __name__ == "__main__":
        app.run(debug=True)
