# Bottled Home

## Requirements

`.env` file with the following entries:
```
FLASK_APP=main.py
SECRET_KEY=<your secret key>
SQLALCHEMY_DATABASE_URI=<your database>
```

## Database

Migrate after db changes
```
> flask db migrate -m 'description goes here'
```

Upgrade to latest
```
> flask db upgrade
```

## Create user

```
> flask shell
> u = User(username="your username").set_password("your password")
> db.session.add(u)
> db.session.commit()
```

### Generate Api token

```
> u.create_token(exp=None) # set expiration to your liking
```

### Api call with token

Curl example
```
> curl -H "Authorization: Bearer YOUR_TOKEN" ip:port/api/sensor
```