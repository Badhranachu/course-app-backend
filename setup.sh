#!/bin/bash
echo "Setting up Django backend..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
echo ""
echo "Backend setup complete!"
echo ""
echo "To run the server:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run: python manage.py runserver"
echo ""
echo "Don't forget to add your Razorpay keys in bekola/settings.py"

