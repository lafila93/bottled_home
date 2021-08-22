from app import create_app, db, models

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        "db" : db,
        "Sensor" : models.Sensor,
        "Sensor_Reading": models.Sensor_Reading,
    }
