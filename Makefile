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
	celery -A core worker -Q default,emails -l info --concurrency=2 --detach
	# celery -A core beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler --detach

stop-celery:
	# Stop Celery worker
	pkill -f 'celery worker'

run-app:
	# Start the development server
	python manage.py runserver

create-superuser:
	# Create a superuser for admin access
	python manage.py createsuperuser

run-prod-checks:
	# Run production checks
	python manage.py check --deploy
	python manage.py check --deploy --fail-level E
	python manage.py check --deploy --fail-level W

run-all:
	# Run all commands
	make install-deps
	make lint
	make format-check
	make format
	make tests
	make run-migration
	make start-celery
	make run-app
	make create-superuser
	make run-prod-checks
