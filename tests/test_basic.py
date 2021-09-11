import datetime
import unittest

import app
import config
import sqlalchemy.exc
from app import db, models
from flask import current_app

config.Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
config.Config.WTF_CSRF_ENABLED = False


def populate_db(n=2):
    """Populates db

    Args:
        n (int): number of entries and children per entry
    """
    sensors = []
    for i in range(n):
        s = models.Sensor(name="Sensor" + str(i))
        sensors.append(s)

    readings = []
    for sensor in sensors:
        for i in range(n):
            r = models.SensorReading(value=i)
            # set custom datetime
            r.datetime = datetime.datetime.utcnow() - datetime.timedelta(minutes=i, seconds=30)
            r.sensor = sensor
            readings.append(r)

    db.session.add_all(sensors + readings)
    db.session.commit()

class TestCaseWebApp(unittest.TestCase):
    """ Inheritable flask app testcase for setup and teardown
    """
    def setUp(self):
        self.app = app.create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()


    def tearDown(self):
        db.drop_all()
        self.app_context.pop()
        self.app, self.app_context = None, None


class TestModels(TestCaseWebApp):
    def setUp(self):
        super().setUp()
        populate_db(1)


    def commitRaiseRollback(self, e):
        """ commits db changes, expects exception and rolls back

        Args:
            e (Exception): Type of Exception that should occur
        """
        with self.assertRaises(e):
            db.session.commit()
        db.session.rollback()


    def test_sensor_delete(self):
        models.Sensor.query.filter_by(id=1).delete()
        db.session.commit()
        # check if readings have been deleted aswell
        self.assertIsNone(models.SensorReading.query.filter_by(sensor_id=1).first())

    def test_sensor_update_cascade(self):
        models.Sensor.query.get(1).id = 999999
        db.session.commit()
        self.assertIsNone(models.SensorReading.query.filter_by(sensor_id=1).first())


class TestWebApp(TestCaseWebApp):
    def setUp(self):
        super().setUp()
        #populate_db(1)
        #self.client = self.app.test_client()


    def tearDown(self):
        super().tearDown()
        #self.client = None


    def test_app(self):
        self.assertIsNotNone(self.app)
        self.assertEqual(self.app, current_app)


class TestApi(TestCaseWebApp):
    def setUp(self):
        super().setUp()
        self.n = 2
        populate_db(self.n)
        self.client = self.app.test_client()


    def tearDown(self):
        super().tearDown()
        self.client = None


    def request(self, request_cb, url, status_code, **kwargs):
        """
        helper function for request and response status code check
        reduce redudance code by using lambdas
            get = lambda status_code, **kwargs: self.request(self.client.get, "/api/sensor", status_code, **kwargs)
            get(200)

        Args:
            request_cb (callable): request callback function, eg. self.client.get
            url (str): url for request
            status_code (int): expected status code, will fail if not correct
            **kwargs: kwargs for request

        Returns:
            response
        """
        response = request_cb(url, **kwargs)
        self.assertEqual(response.status_code, status_code)

        return response


    def test_sensor_get(self):
        get = lambda status_code, **kwargs: self.request(self.client.get, "/api/sensor", status_code, **kwargs)

        # request all sensors
        response_valid = get(200)
        self.assertEqual(len(response_valid.get_json()), models.Sensor.query.count())

        #filtering
        response_filtered = get(200, query_string={"id[]": [1,]})
        self.assertEqual(len(response_filtered.get_json()), 1)


    def test_sensor_post(self):
        post = lambda status_code, **kwargs: self.request(self.client.post, "/api/sensor", status_code, **kwargs)

        # post new valid sensor
        post(200, json={"name":"new sensor"})
        self.assertIsNotNone(models.Sensor.query.filter_by(name="new sensor").first())

        # post sensor invalid data
        post(400, json={"value":1}) #name missing
        post(400, json={"name":"a", "notExistingColumn":"a"}) # not existing column


    def test_sensor_delete(self):
        delete = lambda status_code, id, **kwargs: self.request(self.client.delete, "/api/sensor/" + str(id), status_code, **kwargs)

        # delete existing sensor
        sensor = models.Sensor.query.get(1)
        delete(200, sensor.id)
        self.assertIsNone(models.Sensor.query.get(sensor.id))

        # does not exist
        delete(400, 999999)


    def test_sensor_put(self):
        put = lambda status_code, id, **kwargs: self.request(self.client.put, "/api/sensor/" + str(id), status_code, **kwargs)

        # valid change
        sensor = models.Sensor.query.get(1)
        put(200, sensor.id, json={"description":"desc"})
        self.assertEqual(sensor.description, "desc")

        # invalid changes
        put(400, sensor.id, json={"id":"a"}) # invalid type
        put(400, sensor.id, json={"notExistantColumn":"a"}) # invalid column
        
    def test_sesor_reading_get(self):
        get = lambda status_code, **kwargs: self.request(self.client.get, "/api/sensor/reading", status_code, **kwargs)

        # query all
        response_all = get(200, query_string={"days":1})
        data = response_all.get_json()
        self.assertEqual(len(data), self.n)
        # count all readings
        readingCount = models.SensorReading.query.count()
        self.assertEqual(len([r for readings in data.values() for r in readings]), readingCount)

        # filter by first sensor
        sensor = models.Sensor.query.get(1)
        response_sensor0 = get(200, query_string={"sensor_id[]":[sensor.id], "days":1})
        data = response_sensor0.get_json()
        self.assertEqual(len([r for readings in data.values() for r in readings]), len(sensor.readings))

        # filter by last minute, should only yield one reading for each sensor
        response_last_minute = get(200, query_string={"sensor_id[]":[sensor.id], "minutes":1})
        data = response_last_minute.get_json()
        self.assertEqual(len([r for readings in data.values() for r in readings]), 1)

        # ask for non existent sensor
        get(400, query_string={"sensor_id[]":999999})


    def test_sensor_reading_post(self):
        post = lambda status_code, **kwargs: self.request(self.client.post, "/api/sensor/reading", status_code, **kwargs)

        # post one valid
        sensor = models.Sensor.query.get(1)
        response_valid_one = post(200, json={"sensor_id":sensor.id})
        reading_id = response_valid_one.get_json()[0]["id"]
        self.assertIsNotNone(models.SensorReading.query.get(reading_id))

        # post multiple
        response_valid_multiple = post(
            status_code=200,
            json=[{"sensor_id":sensor.id}, {"sensor_id":sensor.id}]
        )
        reading_ids = [v["id"] for v in response_valid_multiple.get_json()]
        self.assertEqual(models.SensorReading.query \
            .filter(models.SensorReading.id.in_(reading_ids)).count(), len(reading_ids))
        
        # post invalid
        post(400, json={"sensor_id": 1, "value" : "not a float"})
        post(400, json={"sensor_id": 1, "not a column" : None})
        post(400, json={"value":1.3}) # sensor_id missing
        post(400, json=[{"sensor_id":1}, {}]) # one valid, one invalid


    def test_sensor_reading_delete(self):
        delete = lambda status_code, id, **kwargs: self.request(self.client.delete, "/api/sensor/reading/" + str(id), status_code, **kwargs)

        # delete valid
        delete(200, 1)
        self.assertIsNone(models.SensorReading.query.get(1))

        # try deleting non existent
        delete(400, 999999)

    def test_sensor_reading_put(self):
        put = lambda status_code, id, **kwargs: self.request(self.client.put, "/api/sensor/reading/" + str(id), status_code, **kwargs)

        # change valid
        reading = models.SensorReading.query.get(1)
        put(200, reading.id, json={"value":-1})
        self.assertEqual(reading.value, -1)

        # invalid
        put(400, reading.id, json={"value":"a"}) # invalid type
        put(400, reading.id, json={"invalidColumn":None})

        # does not exist
        put(400, 999999, json={"value":1})
