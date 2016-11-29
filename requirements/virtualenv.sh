# Create the virtualenv and install requirements
mkdir -p sailthru
virtualenv sailthru
. venv/bin/activate

pip install -r requirements/base.txt
