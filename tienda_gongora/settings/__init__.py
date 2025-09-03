from .base import *

import environ
env = environ.Env()
if env.bool("DJANGO_USE_DEV", default=False):
    from .dev import *
