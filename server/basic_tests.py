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

    def send_rider_app_request(self, user_id, request_type, lat, lon):
        url = '/noober/rider_app?user_id={}&request_type={}&lat={}&lon={}'.format(
        user_id, request_type, lat, lon)
        return self.app.get(url)

    def send_driver_app_request(self, user_id, request_type, lat, lon):
        url = '/noober/driver_app?user_id={}&request_type={}&lat={}&lon={}'.format(
        user_id, request_type, lat, lon)
        return self.app.get(url)    
        
    def test_rider_request_driver_when_no_drivers(self):
        rv = self.send_rider_app_request(1, RIDER_REQUESTING_DRIVER ,123,234)
        response = json.loads(rv.data)
        assert len(response.keys()) == 1
        assert response["matched"] == False

    def test_driver_request_rider_when_no_riders(self):
        rv = self.send_driver_app_request(1, DRIVER_REQUESTING_RIDER ,123,234)
        response = json.loads(rv.data)
        assert len(response.keys()) == 1
        assert response["matched"] == False
        
if __name__ == '__main__':
    unittest.main()
