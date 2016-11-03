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

    def send_rider_app_request(self, user_id, request_type, lat=None, lon=None):
        url = '/noober/rider_app?user_id={}&request_type={}'.format(
        user_id, request_type)
        if lat != None:
            url+='&lat={}'.format(lat)
        if lon != None:
            url+='&lon={}'.format(lon)
        return self.app.get(url)

    def send_driver_app_request(self, user_id, request_type, lat=None, lon=None):
        url = '/noober/driver_app?user_id={}&request_type={}'.format(
        user_id, request_type)
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

        self.send_driver_app_request(2, DRIVER_PICKED_UP_RIDER)

        # now rider should be picked up.
        rv = self.send_rider_app_request(1, RIDER_WAITING_FOR_PICKUP)
        response = json.loads(rv.data)
        assert response == {"cancelled": False,
                            "picked_up": True}        

    def test_driver_request_rider_when_no_riders(self):
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
        
if __name__ == '__main__':
    unittest.main()
