import os
import json
import sqlite3

from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
from datetime import datetime, date
from dbutil import *
from globals import *


app = Flask(__name__)
app.config.from_object(__name__)

# load default config and override config from an environment variable
app.config.update(dict(
        DATABASE = os.path.join(app.root_path, 'basic.db'),
        SECRET_KEY='development key',
        USERNAME='admin',
        PASSWORD='defualt'))
app.config.from_envvar('BASIC_SETTINGS', silent=True)

# call when returning error from request_driver or request_rider.
# log an error, flash a message, return dict with "matched" = false.
def on_error(message):
        print message
        return json.dumps({"matched" : False}, ensure_ascii=False)

class InputError(Exception):
        def __init__(self, message):
                self.message = message

class InternalError(Exception):
        def __init__(self, message):
                self.message = message

def parse_app_request(request):
        user_id = request.args.get('user_id')
        if user_id == '':
                raise InputError('Missing userid, required field.')
        request_type = request.args.get('request_type')
        if request_type == '':
                raise InputError('Missing request_type, required field.')
        try: 
                request_type = int(request_type)
        except TypeError:
                raise InputError('Request type not parseable as an integer')
        ret = {'user_id': user_id,
               'request_type': request_type}
        # If coords are passed, make sure they're properly formatted.
        if 'lat' in request.args:
                try:
                        ret['lat'] =  float(request.args.get('lat'))
                except TypeError:
                        raise InputError('Latitude not parseable as a float.')
        if 'lon' in request.args:
                try:
                        ret['lon'] =  float(request.args.get('lat'))
                except TypeError:
                        raise InputError('Longitude not parseable as a float.')                        
        return ret

@app.route("/noober/rider_app")
def handle_rider_app_request():
        try:
                rider_request = parse_app_request(request)
        except InputError as err:
                return on_error(err.message)
        if rider_request['request_type'] == RIDER_REQUESTING_DRIVER:
                return handle_rider_requesting_driver(rider_request)
        if rider_request['request_type'] == RIDER_WAITING_FOR_MATCH:
                return handle_rider_waiting_for_match(rider_request)
        # Implement rest of methods.
        return on_error("blah")

@app.route("/noober/driver_app")
def handle_driver_app_request():
        try:
                driver_request = parse_app_request(request)
        except InputError as err:
                return on_error(err.message)
        if driver_request['request_type'] == DRIVER_REQUESTING_RIDER:
                return handle_driver_requesting_rider(driver_request)
        if driver_request['request_type'] == DRIVER_WAITING_FOR_MATCH:
                return handle_driver_waiting_for_match(driver_request)
        # Implement rest of methods.
        return on_error("blah")

def handle_rider_requesting_driver(rider_request):
        # TODO: Instead of returning first option here, should try to do reasonable job of finding closest
        # counterpart.
        driver_match = query_db("SELECT * FROM drivers WHERE matched_rider_id IS NULL", one=True)
        found_match = driver_match != None
        db = get_db()
        if found_match:
                driver_user_id = driver_match[0]
                db.execute("UPDATE drivers SET matched_rider_id = ? WHERE user_id = ?",
                           (rider_request["user_id"], driver_user_id))
                db.commit()
                # return coordinates of matched driver.
                success_response = {"matched" : True,
                                    "lat" : driver_match[1],
                                    "lon" : driver_match[2]}
                print "matched with driver with id: " + str(driver_user_id)
                db.execute('insert into riders (user_id, lat, lon, timestamp, matched_driver_id) values (?,?,?,?,?)',
                           [rider_request["user_id"],
                            rider_request["lat"],
                            rider_request["lon"],
                            datetime.now(),
                            driver_user_id])
                db.commit()
                
                return json.dumps(success_response, ensure_ascii = False)
        # add to riders table.
        db.execute('insert into riders (user_id, lat, lon, timestamp) values (?,?,?,?)',                   
                   [rider_request["user_id"],
                    rider_request["lat"],
                    rider_request["lon"],
                    datetime.now()])
        db.commit()
        message = 'Added entry to riders'
        return json.dumps({"matched": False})

def handle_driver_requesting_rider(driver_request):
        # TODO: Instead of returning first option here, should try to do reasonable job of finding closest
        # counterpart.
        rider_match = query_db("SELECT * FROM riders WHERE matched_driver_id IS NULL", one=True)
        found_match = rider_match != None
        db = get_db()
        if found_match:
                rider_user_id = rider_match[0]
                db.execute("UPDATE riders SET matched_driver_id = ? WHERE user_id = ?",
                           (driver_request["user_id"], rider_user_id))
                db.commit()
                # return coordinates of matched rider.
                success_response = {"matched" : True,
                                    "lat" : rider_match[1],
                                    "lon" : rider_match[2]}
                print "matchd with rider with id: " + str(rider_user_id)
                db.execute('insert into drivers (user_id, lat, lon, timestamp, matched_rider_id) values (?,?,?,?,?)',
                           [driver_request["user_id"],
                            driver_request["lat"],
                            driver_request["lon"],
                            datetime.now(),
                            rider_user_id])
                db.commit()
                
                return json.dumps(success_response, ensure_ascii = False)
        # add to drivers table.
        db.execute('insert into drivers (user_id, lat, lon, timestamp) values (?,?,?,?)',                   
                   [driver_request["user_id"],
                    driver_request["lat"],
                    driver_request["lon"],
                    datetime.now()])
        db.commit()
        message = 'Added entry to drivers'
        return json.dumps({"matched": False})

def handle_rider_waiting_for_match(rider_request):
        existing_row = query_db("SELECT * FROM riders WHERE user_id = ?",
                                (rider_request['user_id'],), one=True)
        if existing_row == None:
                raise InternalError("Rider sent waiting for match request, but is not in db")
        
        # either it's still unmatched, or it's matched now.
        matched_driver_id = existing_row[4]
        if matched_driver_id == None:
                return json.dumps({"matched": False})
        else:
                matched_driver = query_db("SELECT * FROM drivers where user_id = ?",
                                         (matched_driver_id,), one=True)
                if matched_driver == None:
                        raise InternalError(
                                "Driver had matched_rider_id with no corresponding entry in other table")
                success_response = {"matched" : True,
                                    "lat" : matched_driver[1],
                                    "lon" : matched_driver[2]}
                return json.dumps(success_response, ensure_ascii = False)        


def handle_driver_waiting_for_match(driver_request):
        existing_row = query_db("SELECT * FROM drivers WHERE user_id = ?",
                                (driver_request['user_id'],), one=True)
        if existing_row == None:
                raise InternalError("Driver sent waiting for match request, but is not in db")
        
        # either it's still unmatched, or it's matched now.
        matched_rider_id = existing_row[4]
        if matched_rider_id == None:
                return json.dumps({"matched": False})
        else:
                matched_rider = query_db("SELECT * FROM riders where user_id = ?",
                                         (matched_rider_id,), one=True)
                if matched_rider == None:
                        raise InternalError(
                                "Rider had matched_driver_id with no corresponding entry in other table")
                success_response = {"matched" : True,
                                    "lat" : matched_rider[1],
                                    "lon" : matched_rider[2]}
                return json.dumps(success_response, ensure_ascii = False)        


@app.route("/noober/show_riders")
def show_riders():
        riders = query_db('select * from riders')
        return render_template('show_entries.html', entries=riders)

@app.route("/noober/show_drivers")
def show_drivers():
        drivers = query_db('select * from drivers')
        return render_template('show_entries.html', entries=drivers)

@app.cli.command('initdb')
def initdb_command():
        init_db()
        print('Initalized the database.')

@app.teardown_appcontext
def close_db(error):
        """Closes the database again at the end of the request."""
        if hasattr(g, 'sqlite_db'):
                g.sqlite_db.close()

        
if __name__ == "__main__":
        app.run(debug=True)
