export FLASK_APP=run.py
export FLASK_ENV=development
source venv/bin/activate
nohup flask run --port 6666 --host 0.0.0.0 &
