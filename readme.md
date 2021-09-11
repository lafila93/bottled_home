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