import logging

from .cli import cli
from .server import app
from .jobs import JobManager
from .slack import SlackManager


class Droid:
    def __init__(self, jobs, slack, name='droid', timezone=None, environment=None):
        self.name = name
        self.timezone = timezone
        self.environment = environment
        self.configure_logger()

        self.job_manager = JobManager(droid=self, **jobs)
        self.slack_manager = SlackManager(droid=self, **slack)

        app.droid = self
        app.debug = not self.is_production()
        self.server = app

    def __str__(self):
        return self.name

    def configure_logger(self):
        self.logger = logging.getLogger(self.name)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s "%(name)s" %(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

    def cli(self):
        return cli(obj={'droid': self})

    def is_production(self):
        return self.environment == 'production'

    def assert_is_production(self):
        assert self.is_production() == 'production', 'This does not look like your production environment. Be careful.'
