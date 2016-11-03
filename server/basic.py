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
                raise InputError('Missing user_id, required field.')
        type = request.args.get('type')
        if type == '':
                raise InputError('Missing type, required field.')
        try: 
                type = int(type)
        except TypeError:
                raise InputError('Request type not parseable as an integer')
        ret = {'user_id': user_id,
               'type': type}
        # If coords are passed, make sure they're properly formatted.
        if 'lat' in request.args:
                try:
                        ret['lat'] =  float(request.args.get('lat'))
                except TypeError:
                        raise InputError('Latitude not parseable as a float.')
        if 'lon' in request.args:
                try:
                        ret['lon'] =  float(request.args.get('lon'))
                except TypeError:
                        raise InputError('Longitude not parseable as a float.')                        
        return ret

# If riders and drivers schema ever starts getting too different, consider
# splitting into separate helper method for rider and driver.
def get_attr_from_rider_row(row, attribute):
        if attribute == "user_id":
                return row[0]
        elif attribute == "lat":
                return row[1]
        elif attribute == "lon":
                return row[2]
        elif attribute == "timestamp":
                return row[3]
        elif attribute == "matched_driver_id":
                return row[4]
        elif attribute == "picked_up":
                return row[5]
        else:
                raise InternalError("incorrect attribute specified")

def get_attr_from_driver_row(row, attribute):
        if attribute == "user_id":
                return row[0]
        elif attribute == "lat":
                return row[1]
        elif attribute == "lon":
                return row[2]
        elif attribute == "timestamp":
                return row[3]
        elif attribute == "matched_rider_id":
                return row[4]
        elif attribute == "rider_in_car":
                return row[5]
        elif attribute == "matched_rider_id":
                return row[4]
        else:
                raise InternalError("incorrect attribute specified")
        # Implement rest of methods.        

@app.route("/noober/rider_app")
def handle_rider_app_request():
        try:
                rider_request = parse_app_request(request)
        except InputError as err:
                return on_error(err.message)
        if rider_request['type'] == RIDER_REQUESTING_DRIVER:
                return handle_rider_requesting_driver(rider_request)
        elif rider_request['type'] == RIDER_WAITING_FOR_MATCH:
                return handle_rider_waiting_for_match(rider_request)
        elif rider_request['type'] == RIDER_WAITING_FOR_PICKUP:
                return handle_rider_waiting_for_pickup(rider_request)
        elif rider_request['type'] == RIDER_GET_STATUS:
                return handle_rider_get_status(rider_request)        
        raise InternalError("incorrect attribute specified")                        
        # Implement rest of methods.

@app.route("/noober/driver_app")
def handle_driver_app_request():
        try:
                driver_request = parse_app_request(request)
        except InputError as err:
                return on_error(err.message)
        if driver_request['type'] == DRIVER_REQUESTING_RIDER:
                return handle_driver_requesting_rider(driver_request)
        elif driver_request['type'] == DRIVER_WAITING_FOR_MATCH:
                return handle_driver_waiting_for_match(driver_request)
        elif driver_request['type'] == DRIVER_DRIVING_TO_PICKUP:
                return handle_driver_driving_to_pickup(driver_request)
        elif driver_request['type'] == DRIVER_PICKED_UP_RIDER:
                return handle_driver_picked_up_rider(driver_request)
        elif driver_request['type'] == DRIVER_DROPPED_OFF:
                return handle_driver_dropped_off(driver_request)
        elif driver_request['type'] == DRIVER_GET_STATUS:
                return handle_driver_get_status(driver_request)                
        # Implement rest of methods.
        return on_error("blah")

def handle_rider_requesting_driver(rider_request):
        # TODO: Instead of returning first option here, should try to do reasonable job of finding closest
        # counterpart.
        driver_match = query_db("SELECT * FROM drivers WHERE matched_rider_id IS NULL", one=True)
        found_match = driver_match != None
        db = get_db()
        if found_match:
                driver_user_id = get_attr_from_driver_row(driver_match, "user_id")
                db.execute("UPDATE drivers SET matched_rider_id = ? WHERE user_id = ?",
                           (rider_request["user_id"], driver_user_id))
                db.commit()
                # return coordinates of matched driver.
                success_response = {"matched" : True,
                                    "lat" : get_attr_from_driver_row(driver_match, "lat"),
                                    "lon" : get_attr_from_driver_row(driver_match, "lon")}
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
        return json.dumps({"matched": False})

def handle_rider_waiting_for_match(rider_request):
        existing_row = query_db("SELECT * FROM riders WHERE user_id = ?",
                                (rider_request['user_id'],), one=True)
        if existing_row == None:
                raise InternalError("Rider sent waiting for match request, but is not in db")
        
        # either it's still unmatched, or it's matched now.
        matched_driver_id = get_attr_from_rider_row(existing_row, "matched_driver_id")
        if matched_driver_id == None:
                return json.dumps({"matched": False})
        else:
                matched_driver = query_db("SELECT * FROM drivers where user_id = ?",
                                         (matched_driver_id,), one=True)
                if matched_driver == None:
                        raise InternalError(
                                "Driver had matched_rider_id with no corresponding entry in other table")
                success_response = {"matched" : True,
                                    "lat" : get_attr_from_driver_row(matched_driver, "lat"),
                                    "lon" : get_attr_from_driver_row(matched_driver, "lon")}
                return json.dumps(success_response, ensure_ascii = False)

# check if driver has cancelled and if not, if driver has picked up.        
def handle_rider_waiting_for_pickup(rider_request):
        existing_row = query_db("SELECT * FROM riders WHERE user_id = ?",
                                (rider_request['user_id'],), one=True)
        if existing_row == None:
                raise InternalError("Rider sent waiting for pickup request, but is not in db")
        cancelled = get_attr_from_rider_row(existing_row, "matched_driver_id") == None
        if cancelled:
                return json.dumps({"cancelled": True})
        # check if driver has picked up.
        picked_up = get_attr_from_rider_row(existing_row, "picked_up")
        if (picked_up == None):
                picked_up = 0
        return json.dumps({"cancelled": False,
                           "picked_up": picked_up})

def handle_rider_get_status(rider_request):
        existing_row = query_db("SELECT * FROM riders WHERE user_id = ?",
                                (rider_request['user_id'],), one=True)
        if existing_row == None:
                raise InternalError("Rider sent get status request, but is not in db")
        print "existing row: ", existing_row
        return json.dumps({"lat": get_attr_from_rider_row(existing_row, "lat"),
                           "lon": get_attr_from_rider_row(existing_row, "lon"),
                           "matched_driver_id": get_attr_from_rider_row(existing_row, "matched_driver_id"),
                           "picked_up": get_attr_from_rider_row(existing_row, "picked_up")})

def handle_driver_requesting_rider(driver_request):
        # TODO: Instead of returning first option here, should try to do reasonable job of finding closest
        # counterpart.
        rider_match = query_db("SELECT * FROM riders WHERE matched_driver_id IS NULL", one=True)
        found_match = rider_match != None
        db = get_db()
        if found_match:
                rider_user_id = get_attr_from_rider_row(rider_match, "user_id")
                db.execute("UPDATE riders SET matched_driver_id = ? WHERE user_id = ?",
                           (driver_request["user_id"], rider_user_id))
                db.commit()
                # return coordinates of matched rider.
                success_response = {"matched" : True,
                                    "lat" : get_attr_from_rider_row(rider_match, "lat"),
                                    "lon" : get_attr_from_rider_row(rider_match, "lon")}
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

def handle_driver_waiting_for_match(driver_request):
        existing_row = query_db("SELECT * FROM drivers WHERE user_id = ?",
                                (driver_request['user_id'],), one=True)
        if existing_row == None:
                raise InternalError("Driver sent waiting for match request, but is not in db")
        
        # either it's still unmatched, or it's matched now.
        matched_rider_id = get_attr_from_driver_row(existing_row, "matched_rider_id")
        if matched_rider_id == None:
                return json.dumps({"matched": False})
        else:
                matched_rider = query_db("SELECT * FROM riders where user_id = ?",
                                         (matched_rider_id,), one=True)
                if matched_rider == None:
                        raise InternalError(
                                "Rider had matched_driver_id with no corresponding entry in other table")
                success_response = {"matched" : True,
                                    "lat" : get_attr_from_rider_row(matched_rider, "lat"),
                                    "lon" : get_attr_from_rider_row(matched_rider, "lon")}
                return json.dumps(success_response, ensure_ascii = False)

# todo: maybe this should also update driver location in DB?
# for now, this will just check if rider has cancelled by checking if it's still matched in db.
def handle_driver_driving_to_pickup(driver_request):
        existing_row = query_db("SELECT * FROM drivers WHERE user_id = ?",
                                (driver_request['user_id'],), one=True)
        if existing_row == None:
                raise InternalError("Driver sent driving to pickup request, but is not in db")
        cancelled = get_attr_from_driver_row(existing_row, "matched_rider_id") == None
        return json.dumps({"cancelled": cancelled})

# just update driver and corresponding rider table to reflect that rider has been picked up.
def handle_driver_picked_up_rider(driver_request):
        driver_id = driver_request['user_id']
        existing_row = query_db("SELECT * FROM drivers WHERE user_id = ?",
                                (driver_id, ), one=True)
        if existing_row == None:
                raise InternalError("Driver sent driving to pickup request, but is not in db")
        db = get_db()
        db.execute("UPDATE drivers SET rider_in_car = 1 WHERE user_id = ?",
                   (driver_id, ))
        db.commit()
        # update corresponding row in riders table.
        matched_rider_id = get_attr_from_driver_row(existing_row, "matched_rider_id")
        if matched_rider_id == None:
                raise InputError("Driver app sent DRIVER_PICKED_UP_RIDER request, but is not matched to any rider")
        db.execute("UPDATE riders SET picked_up = 1 WHERE user_id = ?",
                   (matched_rider_id, ))
        db.commit()
        return json.dumps({})

# unmatch both driver and rider.
def handle_driver_dropped_off(driver_request):
        driver_id = driver_request['user_id']
        existing_row = query_db("SELECT * FROM drivers WHERE user_id = ?",
                                (driver_id, ), one=True)
        if existing_row == None:
                raise InternalError("Driver sent dropped off request, but is not in db")
        db = get_db()
        db.execute("UPDATE drivers SET matched_rider_id = NULL, rider_in_car = 0 WHERE  user_id = ?",
                   (driver_id, ))
        db.commit()
        # update corresponding row in riders table.
        matched_rider_id = get_attr_from_driver_row(existing_row, "matched_rider_id")        
        if matched_rider_id == None:
                raise InputError("Driver app sent DRIVER_PICKED_UP_RIDER request, but is not matched to any rider")
        db.execute("UPDATE riders SET matched_driver_id = NULL, picked_up = 0 WHERE user_id = ?",
                   (matched_rider_id, ))
        db.commit()        
        return json.dumps({})

def handle_driver_get_status(driver_request):
        existing_row = query_db("SELECT * FROM drivers WHERE user_id = ?",
                                (driver_request['user_id'],), one=True)
        if existing_row == None:
                raise InternalError("Driver sent get status request, but is not in db")
        print "existing row: ", existing_row
        return json.dumps({"lat": get_attr_from_driver_row(existing_row, "lat"),
                           "lon": get_attr_from_driver_row(existing_row, "lon"),
                           "matched_rider_id": get_attr_from_driver_row(existing_row, "matched_rider_id"),
                           "rider_in_car": get_attr_from_driver_row(existing_row, "rider_in_car")})

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
