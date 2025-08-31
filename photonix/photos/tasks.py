from celery import shared_task


@shared_task
def add(x, y):
    return x + y


@shared_task
def hello_world():
    print("Hello from a Celery task!")
    return "Hello, World!"
