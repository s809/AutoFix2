#!/bin/bash

python autofix/manage.py makemigrations
python autofix/manage.py migrate
