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
    users = []
    for i in range(n):
        u = models.User(username="User" + str(i)).set_password("Password" + str(i))
        users.append(u)

    sensors = []
    for user in users:
        for i in range(n):
            s = models.Sensor(name="Sensor" + str(i))
            s.user = user
            sensors.append(s)

    readings = []
    for sensor in sensors:
        for i in range(n):
            r = models.SensorReading(value=i)
            # set custom datetime
            r.datetime = datetime.datetime.utcnow() - datetime.timedelta(minutes=i, seconds=30)
            r.sensor = sensor
            readings.append(r)

    db.session.add_all(users + sensors + readings)
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


    def test_user_add_invalid(self):
        user0 = models.User.query.get(1)
        user_same_name = models.User(username=user0.username, password_hash="pwh")
        db.session.add(user_same_name)
        self.commitRaiseRollback(sqlalchemy.exc.IntegrityError)

        # no password
        user_no_pw = models.User(username="no_pw")
        db.session.add(user_no_pw)
        self.commitRaiseRollback(sqlalchemy.exc.IntegrityError)


    def test_user_delete(self):
        models.User.query.filter_by(id=1).delete()
        db.session.commit()
        # check if sensors have been deleted aswell
        self.assertIsNone(models.Sensor.query.filter_by(user_id=1).first())


    def test_user_password(self):
        u = models.User()
        u.set_password("valid")
        self.assertTrue(u.check_password("valid"))
        self.assertFalse(u.check_password("invalid"))


    def test_user_token(self):
        # test valid token
        u = models.User.query.first()
        token_valid = u.create_token({"key" : "value"})
        user_by_token, data = models.User.check_token(token_valid)
        self.assertEqual(u, user_by_token)
        self.assertEqual(data["key"], "value")

        # expired
        token_expired = u.create_token(exp=-1)
        res = models.User.check_token(token_expired)
        self.assertEqual(res, (None, None))

        # tempered
        res = models.User.check_token(token_valid + "a")
        self.assertEqual(res, (None, None))


    def test_sensor_delete(self):
        models.Sensor.query.filter_by(id=1).delete()
        db.session.commit()
        # check if readings have been deleted aswell
        self.assertIsNone(models.SensorReading.query.filter_by(sensor_id=1).first())


class TestWebApp(TestCaseWebApp):
    def setUp(self):
        super().setUp()
        populate_db(1)
        self.client = self.app.test_client()


    def tearDown(self):
        super().tearDown()
        self.client = None


    def test_app(self):
        self.assertIsNotNone(self.app)
        self.assertEqual(self.app, current_app)


    def test_login(self):
        response_invalid = self.client.post("/login",
            data={"username":"User0", "password":"invalid"},
            follow_redirects=True)
        self.assertEqual(response_invalid.status_code, 200)
        self.assertEqual(response_invalid.request.path, "/login")

        response = self.client.post("/login", 
            data={"username":"User0", "password":"Password0"})
        
        # check if api token has been set
        cookies = response.headers.get_all("Set-Cookie")
        self.assertTrue(any(c.startswith("api_token=") for c in cookies))


    def test_logout(self):
        # login
        self.client.post("/login",
            data={"username":"User0", "password":"Password0"})
        response = self.client.get("/logout")

        # check if api token has been removed
        cookies = response.headers.get_all("Set-Cookie")
        self.assertTrue(any(c.startswith("api_token=") for c in cookies))


class TestApi(TestCaseWebApp):
    def setUp(self):
        super().setUp()
        self.n = 2
        populate_db(self.n)
        self.client = self.app.test_client()


    def tearDown(self):
        super().tearDown()
        self.client = None


    @staticmethod
    def header_user_token(user):
        """ Returns the correct token auth header for given user

        Args:
            user (models.User): User object for the related token

        Returns:
            dict of header key and token value
        """
        return {"Authorization": "Bearer " + user.create_token()}


    def request(self, request_cb, url, status_code, user=None, **kwargs):
        """
        helper function for request and response status code check
        reduce redudance code by using lambdas
            get = lambda status_code, **kwargs: self.request(self.client.get, "/api/sensor", status_code, **kwargs)
            get(200, user=user)

        Args:
            request_cb (callable): request callback function, eg. self.client.get
            url (str): url for request
            status_code (int): expected status code, will fail if not correct
            user (models.User): user object for token auth header
            **kwargs: kwargs for request

        Returns:
            response
        """
        # add user token to headers
        if not user is None:
            kwargs["headers"] = {
                **self.header_user_token(user),
                **kwargs.get("headers", {}),
            }

        response = request_cb(url, **kwargs)
        self.assertEqual(response.status_code, status_code)

        return response


    def test_sensor_get(self):
        get = lambda status_code, **kwargs: self.request(self.client.get, "/api/sensor", status_code, **kwargs)

        u = models.User.query.get(1)
        # request all user sensors
        response_valid = get(200, user=u)
        self.assertEqual(len(response_valid.get_json()), self.n)

        #filtering
        response_filtered = get(200, user=u, query_string={"id[]": [1,]})
        self.assertEqual(len(response_filtered.get_json()), 1)

        # no auth
        get(401)


    def test_sensor_post(self):
        post = lambda status_code, **kwargs: self.request(self.client.post, "/api/sensor", status_code, **kwargs)

        u = models.User.query.get(1)
        # post new valid sensor
        post(200, user=u, json={"name":"new sensor"})
        self.assertIsNotNone(models.Sensor.query.filter_by(name="new sensor").first())

        # post sensor invalid data
        post(400, user=u, json={"value":1}) #name missing
        post(400, user=u, json={"name":"a", "user_id":2}) # user_id should not be settable
        post(400, user=u, json={"name":"a", "id":999}) # id should not se settable
        post(400, user=u, json={"name":"a", "notExistingColumn":"a"}) # not existing column

        # post sensor no auth
        post(401, json={"name":"a"})


    def test_sensor_delete(self):
        delete = lambda status_code, id, **kwargs: self.request(self.client.delete, "/api/sensor/" + str(id), status_code, **kwargs)

        u = models.User.query.get(1)
        # delete own sensor
        sensor = u.sensors[0]
        delete(200, sensor.id, user=u)
        self.assertIsNone(models.Sensor.query.get(sensor.id))

        # does not exist
        delete(400, 999999, user=u)

        # delete from other user
        sensor_foreign = models.User.query.get(2).sensors[0]
        delete(401, sensor_foreign.id, user=u)

        # no auth
        delete(401, sensor.id)


    def test_sensor_put(self):
        put = lambda status_code, id, **kwargs: self.request(self.client.put, "/api/sensor/" + str(id), status_code, **kwargs)

        u = models.User.query.get(1)
        # valid change
        sensor = u.sensors[0]
        put(200, sensor.id, user=u, json={"description":"desc"})
        self.assertEqual(sensor.description, "desc")

        # invalid changes
        put(400, sensor.id, user=u, json={"id":999999})
        put(400, sensor.id, user=u, json={"user_id":2})
        
        # foreign sensor
        sensor_foreign = models.Sensor.query.filter_by(user_id=2).first()
        put(401, sensor_foreign.id, user=u, json={"description":"no permission"})

        # no auth
        put(401, sensor.id, json={"description":"no auth"})


    def test_sesor_reading_get(self):
        get = lambda status_code, **kwargs: self.request(self.client.get, "/api/sensor/reading", status_code, **kwargs)

        u = models.User.query.get(1)
        # query all for one user
        response_all = get(200, user=u, query_string={"days":1})
        data = response_all.get_json()
        self.assertEqual(len(data), self.n)
        # count all readings for this user
        readingCount = models.SensorReading.query \
            .join(models.Sensor, models.User) \
            .filter(models.User.id == u.id) \
            .count()
        self.assertEqual(len([r for readings in data.values() for r in readings]), readingCount)

        # filter by first sensor
        sensor = u.sensors[0]
        response_sensor0 = get(200, user=u, query_string={"sensor_id[]":[sensor.id], "days":1})
        data = response_sensor0.get_json()
        self.assertEqual(len([r for readings in data.values() for r in readings]), len(sensor.readings))

        # filter by last minute, should only yield one reading for each sensor
        response_last_minute = get(200, user=u, query_string={"sensor_id[]":[sensor.id], "minutes":1})
        data = response_last_minute.get_json()
        self.assertEqual(len([r for readings in data.values() for r in readings]), 1)

        # ask for foreign sensor
        foreign_sensor = models.User.query.get(2).sensors[0]
        get(401, user=u, query_string={"sensor_id[]":foreign_sensor.id})

        # ask for non existent sensor
        get(400, user=u, query_string={"sensor_id[]":999999})


    def test_sensor_reading_post(self):
        post = lambda status_code, **kwargs: self.request(self.client.post, "/api/sensor/reading", status_code, **kwargs)

        # post one valid
        u = models.User.query.get(1)
        response_valid_one = post(200, user=u, json={"sensor_id":u.sensors[0].id})
        reading_id = response_valid_one.get_json()[0]["id"]
        self.assertIsNotNone(models.SensorReading.query.get(reading_id))

        # post multiple
        response_valid_multiple = post(
            status_code=200,
            user=u,
            json=[{"sensor_id":u.sensors[0].id}, {"sensor_id":u.sensors[0].id}]
        )
        reading_ids = [v["id"] for v in response_valid_multiple.get_json()]
        self.assertEqual(models.SensorReading.query \
            .filter(models.SensorReading.id.in_(reading_ids)).count(), len(reading_ids))
        
        # post invalid
        post(400, user=u, json={"sensor_id": 1, "value" : "not a float"})
        post(400, user=u, json={"sensor_id": 1, "not a column" : None})
        post(400, user=u, json={"value":1.3}) # sensor_id missing
        post(400, user=u, json=[{"sensor_id":1}, {}]) # one valid, one invalid


        # post foreign sensor
        sensor_foreign = models.User.query.get(2).sensors[0]
        post(401, user=u, json={"sensor_id":sensor_foreign.id})

        # post unauth
        post(401, json={"sensor_id":1})


    def test_sensor_reading_delete(self):
        delete = lambda status_code, id, **kwargs: self.request(self.client.delete, "/api/sensor/reading/" + str(id), status_code, **kwargs)

        u = models.User.query.get(1)
        # delete valid
        reading = u.sensors[0].readings[0]
        delete(200, reading.id, user=u)
        self.assertIsNone(models.SensorReading.query.get(reading.id))

        # delete non existent
        delete(400, 999999, user=u)

        # delete foreign
        readings_foreign = models.SensorReading.query \
            .join(models.Sensor).filter(
                models.Sensor.user_id == 2
            ).first()
        delete(401, readings_foreign.id, user=u)

        # no auth
        delete(401, 2)


    def test_sensor_reading_put(self):
        put = lambda status_code, id, **kwargs: self.request(self.client.put, "/api/sensor/reading/" + str(id), status_code, **kwargs)

        u = models.User.query.get(1)
        # change valid
        reading = u.sensors[0].readings[0]
        put(200, reading.id, user=u, json={"value":-1})
        self.assertEqual(reading.value, -1)

        # swap reading to another sensor or yours
        put(200, reading.id, user=u, json={"sensor_id":u.sensors[1].id})

        # invalid
        put(400, reading.id, user=u, json={"id":999999}) # not changeable
        put(400, reading.id, user=u, json={"value":"a"}) # invalid type
        put(400, reading.id, user=u, json={"invalidColumn":None})

        # does not exist
        put(400, 999999, user=u, json={"value":1})

        # swap to foreign users sensor
        sensor_foreign = models.Sensor.query.filter_by(user_id=2).first()
        put(401, reading.id, user=u, json={"sensor_id":sensor_foreign.id})

        # foreign reading
        reading_foreign = models.SensorReading.query.join(models.Sensor) \
            .filter(models.Sensor.user_id == 2).first()
        put(401, reading_foreign.id, user=u, json={"value":1})

        # no auth
        put(401, reading.id, json={"value":1})
