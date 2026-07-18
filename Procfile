release: flask db upgrade
web: gunicorn god_eye_system.app:create_app\(\) -b 0.0.0.0:$PORT -w 3
