import os
import sqlite3

from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash

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

def get_db():
        """Opens a new database connection if there is none yet for the current application context.
        """
        if not hasattr(g, 'sqlite_db'):
                g.sqlite_db = connect_db()
        return g.sqlite_db

def query_db(query, args=(), one=False):
        cur = get_db().execute(query,args)
        rv = cur.fetchall()
        cur.close()
        return (rv[0] if rv else None) if one else rv
        
def init_db():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
                db.cursor().executescript(f.read())
        db.commit()
        
