from app import create_app, db, models

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        "db" : db,
        "models" : models,
        "Sensor" : models.Sensor,
        "SensorReading": models.SensorReading,
        "User" : models.User,
    }
