install-deps:
	# Install dependencies
	pip install --upgrade pip
	pip install -r requirements.txt

lint:
	# Run linter
	flake8 ./authentication ./core ./utils

format-check:
	# Check code formatting
	black --check ./authentication ./core ./utils

format:
	# Format code
	black ./authentication ./core ./utils

tests:
	# Run tests
	python manage.py test

run-migration:
	# Run database migrations
	python manage.py makemigrations
	python manage.py migrate

start-celery:
	# Start Celery worker in the background
	celery -A core worker -l info --concurrency=2 --max-tasks-per-child=50 -detach

run-app:
	# Start the development server
	python manage.py runserver

create-superuser:
	# Create a superuser for admin access
	python manage.py createsuperuser
