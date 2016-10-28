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
# todo: right now this is used for error and not matched. split
# this into two separate methods.
def on_error(message):
        print message
        flash(message)
        return json.dumps({"matched" : False}, ensure_ascii=False)

# TODO: define db row converter to get dict syntax, so updating indices isnt a pain.

# either update other table, matching an entry with my ID, or if no
# entries "available" in other table, insert into my table.
# TODO: this comment out of date, update.
def update_other_table_or_add_to_my_table(coords, user_id, other_table, my_table):
        # first check if this is a repeat request, that is, user_id already exists in
        # my_table.  If so, just return the current status of the row.
        existing_row = query_db("SELECT * FROM {} WHERE user_id = ?".format(my_table),(user_id,), one=True)
        if existing_row != None:
                # either it's still unmatched, or it's matched now.
                counterpart_user_id = existing_row[5]
                if counterpart_user_id == None:
                        return on_error("Still not matched")
                else:
                        counterpart_row = query_db("SELECT * FROM {} where user_id = ?".format(other_table),(counterpart_user_id,), one=True)
                        if counterpart_row == None:
                                return on_error("Internal error, had counterpart id with no corresponding entry in other table")
                        coords_dict = {"matched" : True,
                                       "lat" : counterpart_row[2],
                                       "lon" : counterpart_row[3]}
                        return json.dumps(coords_dict, ensure_ascii = False)
        # otherwise, this is a new driver/rider and the db state needs to be updated.
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
                               "lat" : first_choice[2],
                               "lon" : first_choice[3]}
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

# if user submits cancel, remove all entries from drivers/riders table with that user id,
# and unmatch all requests which have same counterpart_user_id.
@app.route("/noober/cancel")
def cancel():
        if "userid" not in request.args:
                return on_error('Missing userid query param from cancel request')
        user_id = request.args.get('userid')        
        db = get_db()
        db.execute('DELETE FROM riders WHERE user_id = ?',(user_id,))
        db.execute('DELETE FROM drivers WHERE user_id = ?',(user_id,))        
        db.execute("UPDATE drivers SET counterpart_user_id = null WHERE counterpart_user_id = ?",
                   (user_id, ))
        db.execute("UPDATE riders SET counterpart_user_id = null WHERE counterpart_user_id = ?",
                   (user_id, ))                
        db.commit()
        return json.dumps({"matched" : False}, ensure_ascii=False)
        

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
