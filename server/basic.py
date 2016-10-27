import os
import json
import sqlite3
import uuid

from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
from datetime import datetime, date
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

@app.cli.command('initdb')
def initdb_command():
        init_db()
        print('Initalized the database.')

@app.teardown_appcontext
def close_db(error):
        """Closes the database again at the end of the request."""
        if hasattr(g, 'sqlite_db'):
                g.sqlite_db.close()

# call when returning error from request_driver or request_rider.
# log an error, flash a message, return dict with "matched" = false.
def on_error(message):
        print message
        flash(message)
        return json.dumps({"matched" : False}, ensure_ascii=False)

# either update other table, matching an entry with my ID, or if no
# entries "available" in other table, insert into my table.
def update_other_table_or_add_to_my_table(coords, user_id, other_table, my_table):
        # TODO: handle repeat requests.
        transaction_id = str(uuid.uuid4())
        # TODO: Instead of returning first option here, should try to do reasonable job of finding closest
        # counterpart.
        first_choice = query_db("SELECT * FROM {} WHERE counterpart_user_id IS NULL".format(other_table), one=True)
        found_match = first_choice != None
        db = get_db()
        if found_match:
                other_user_id = first_choice[1]
                # update <other_table> table.    
                db.execute("UPDATE {} SET counterpart_user_id = ? WHERE user_id = ?".format(other_table),
                           (user_id, other_user_id))
                db.commit()
                message = 'Successfully updated ' + other_table
                flash(message)
                # return coordinates of counterpart.
                coords_dict = {"matched" : True,
                               "lat" : first_choice[1],
                               "lon" : first_choice[2]}
                print "found counterpart with id: " + str(other_user_id)
                db.execute('insert into {} (transaction_id, user_id, lat, lon, timestamp, counterpart_user_id) values (?,?,?,?,?,?)'.format(my_table), [transaction_id, user_id, coords[0], coords[1], datetime.now(), other_user_id])
                db.commit()
                
                return json.dumps(coords_dict, ensure_ascii = False)
        # add to <my_table> table.
        db.execute('insert into {} (transaction_id, user_id, lat, lon, timestamp) values (?,?,?,?,?)'.format(my_table),                   
                   [transaction_id, user_id, coords[0], coords[1], datetime.now()])
        db.commit()
        message = 'Added entry to ' + my_table
        return on_error(message)        

# when rider requests a driver, check drivers table to see if any drivers
# available.  if so, return that driver. otherwise, let rider know they've
# been added to waiting queue.
@app.route("/noober/driver")
def request_driver():
        if "coords" not in request.args:
                return on_error('Missing coords query param')
        coords = request.args.get('coords').split(',')
        if len(coords) != 2: 
                return on_error('coords incorrectly formatted')
        user_id = request.args.get('userid')
        return update_other_table_or_add_to_my_table(coords, user_id, 'drivers', 'riders')

@app.route("/noober/rider")
def request_rider():
        if "coords" not in request.args:
                return on_error('Missing coords query param')
        coords = request.args.get('coords').split(',')
        if len(coords) != 2:
                return on_error('coords incorrectly formatted')
        user_id = request.args.get('userid')
        return update_other_table_or_add_to_my_table(coords, user_id, 'riders', 'drivers')        

@app.route("/noober/show_riders")
def show_riders():
        riders = query_db('select * from riders')
        return render_template('show_entries.html', entries=riders)

@app.route("/noober/show_drivers")
def show_drivers():
        drivers = query_db('select * from drivers')
        return render_template('show_entries.html', entries=drivers)

        
if __name__ == "__main__":
        app.run(debug=True)
