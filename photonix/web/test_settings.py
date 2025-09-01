import tempfile

from .settings import *


DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.sqlite3',
        'NAME':     ':memory:',
        'ATOMIC_REQUESTS': True,
        # 'OPTIONS': {
        #     # ...
        #     'timeout': 10,
        #     # ...
        # }
    }
}

DATA_DIR = tempfile.mkdtemp()
CACHE_DIR = str(Path(DATA_DIR) / 'cache')
PHOTO_RAW_PROCESSED_DIR = str(Path(DATA_DIR) / 'raw-photos-processed')
THUMBNAIL_ROOT = str(Path(CACHE_DIR) / 'thumbnails')

ROOT_URLCONF = 'tests.urls'

ROOT_URLCONF = 'tests.urls'

# Empty secret key for tests
SECRET_KEY = 'a-secret-key-for-tests'

DATABASES['default']['ATOMIC_REQUESTS'] = True