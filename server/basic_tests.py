import os
import basic
import json
import unittest
import tempfile

from globals import *

class BasicTestCase(unittest.TestCase):
    def setUp(self):
        self.db_fd, basic.app.config['DATABASE'] = tempfile.mkstemp()
        basic.app.config['TESTING'] = True
        self.app = basic.app.test_client()
        with basic.app.app_context():
                        basic.init_db()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(basic.app.config['DATABASE'])

    def send_rider_app_request(self, user_id, type, lat=None, lon=None):
        url = '/noober/rider_app?user_id={}&type={}'.format(
        user_id, type)
        if lat != None:
            url+='&lat={}'.format(lat)
        if lon != None:
            url+='&lon={}'.format(lon)
        return self.app.get(url)

    def send_driver_app_request(self, user_id, type, lat=None, lon=None):
        url = '/noober/driver_app?user_id={}&type={}'.format(
        user_id, type)
        if lat != None:
            url+='&lat={}'.format(lat)
        if lon != None:
            url+='&lon={}'.format(lon)
        return self.app.get(url)    
        
    def test_basic_flow(self):
        rv = self.send_rider_app_request(1, RIDER_REQUESTING_DRIVER ,123,234)
        response = json.loads(rv.data)
        assert len(response.keys()) == 1
        assert response["matched"] == False

        # now send matching request, expect response of with matched set to true
        # and lat,lon of previous rider.
        rv = self.send_driver_app_request(2, DRIVER_REQUESTING_RIDER ,123.1, 234.1)
        response = json.loads(rv.data)
        assert response == {"matched": True,
                           "lat": 123,
                           "lon": 234}

        rv = self.send_driver_app_request(2, DRIVER_DRIVING_TO_PICKUP ,123.2, 234.2)
        response = json.loads(rv.data)
        assert response == {"cancelled": False}

        rv = self.send_rider_app_request(1, RIDER_WAITING_FOR_PICKUP)
        response = json.loads(rv.data)
        print "response:", response
        assert response == {"cancelled": False,
                            "picked_up": False}        

        # driver picks up rider.
        self.send_driver_app_request(2, DRIVER_PICKED_UP_RIDER)

        # now rider should be picked up.
        rv = self.send_rider_app_request(1, RIDER_WAITING_FOR_PICKUP)
        response = json.loads(rv.data)
        assert response == {"cancelled": False,
                            "picked_up": True}

        # driver drops off rider
        self.send_driver_app_request(2, DRIVER_DROPPED_OFF)

        # check rider and driver statuses
        rv = self.send_rider_app_request(1, RIDER_GET_STATUS)
        response = json.loads(rv.data)
        assert response["matched_driver_id"] == None
        assert response["picked_up"] == False

        rv = self.send_driver_app_request(2, DRIVER_GET_STATUS)
        response = json.loads(rv.data)
        assert response["matched_rider_id"] == None
        assert response["rider_in_car"] == False        

    def test_rider_cancel_while_waiting_for_pickup(self):
        rv = self.send_driver_app_request(2, DRIVER_REQUESTING_RIDER ,123,234)
        response = json.loads(rv.data)
        assert len(response.keys()) == 1
        assert response["matched"] == False

        # now send matching request, expect response of with matched set to true
        # and lat,lon of previous driver.
        rv = self.send_rider_app_request(1, RIDER_REQUESTING_DRIVER ,123.1, 234.1)
        response = json.loads(rv.data)
        assert response == {"matched": True,
                           "lat": 123,
                           "lon": 234}

        rv = self.send_rider_app_request(1, RIDER_CANCEL)

        # check driver status to see if they are unmatched
        # TODO: need to be able to check that rider was deleted from DB also.
        # consider modifying get status request to make this possible or
        # see if there's way to inspect db directly.
        rv = self.send_driver_app_request(2, DRIVER_GET_STATUS)
        response = json.loads(rv.data)
        assert response["matched_rider_id"] == None
        assert response["rider_in_car"] == None        
        
if __name__ == '__main__':
    unittest.main()
