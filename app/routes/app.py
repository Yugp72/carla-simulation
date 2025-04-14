from flask import Flask
from carControl import control_routes
from anomalyAPI import anomaly_api

app = Flask(__name__)
app.register_blueprint(control_routes)
app.register_blueprint(anomaly_api)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
