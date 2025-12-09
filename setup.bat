@echo off
echo Setting up Django backend...
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
echo.
echo Backend setup complete!
echo.
echo To run the server:
echo   1. Activate virtual environment: venv\Scripts\activate
echo   2. Run: python manage.py runserver
echo.
echo Don't forget to add your Razorpay keys in bekola/settings.py
pause

