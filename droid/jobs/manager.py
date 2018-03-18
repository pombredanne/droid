import os
import yaml

import maya

from ..utils.importer import import_string


class JobManager:
    def __init__(self,
                 droid,
                 config_path,
                 types,
                 default_job_settings
                 ):
        self.droid = droid
        self.config_path = config_path
        assert os.path.exists(self.config_path), 'config_path does not exist'

        self.types = types
        self.default_job_settings = default_job_settings

        self.register_job_types()
        self.load_jobs()

    def register_job_types(self):
        self.job_classes = {}
        for name, import_path in self.types.items():
            self.job_classes[name] = import_string(import_path)

    def load_jobs(self):
        # allow a directory of configs to be loaded
        job_config_paths = []
        for root, subdirs, files in os.walk(self.config_path):
            for f in files:
                p = os.path.join(root, f)
                if p.endswith('.yml') or p.endswith('.yaml'):
                    job_config_paths.append(p)

        # TODO ensure job name unique, use dict

        self.jobs = []

        for job_config_path in job_config_paths:
            with open(job_config_path, 'r') as f:
                config = yaml.safe_load(f)

            config_file_default_settings = config.get('default_settings', {})

            for job in config.get('jobs', []):
                # create new instances of each job, using settings as kwargs
                job_class = self.job_classes[job['type']]

                settings = {
                    **self.default_job_settings,
                    **config_file_default_settings,
                    **job.get('settings', {}),
                }

                job_instance = job_class(
                    name=job['name'],
                    droid=self.droid,
                    schedule=job.get('schedule', None),
                    can_be_run_manually=job.get('can_be_run_manually', False),
                    **settings
                )
                self.jobs.append(job_instance)

    def run_job(self, job, send_notifications):
        try:
            job.run()
            if send_notifications:
                job.notify_for_state()
        except Exception as e:
            if send_notifications:
                job.on_error(e)

            raise e

    def run_jobs(self, jobs, send_notifications=True):
        exceptions = []

        for job in jobs:
            try:
                self.run_job(job, send_notifications)
            except Exception as e:
                self.logger.info('Exception while running job', e)
                exceptions.append(e)

        if exceptions:
            self.logger.error(exceptions)
            raise exceptions[0]

    def get_job_by_name(self, job_name):
        matching_jobs = [x for x in self.jobs if x.name == job_name]
        if matching_jobs:
            return matching_jobs[0]
        return None

    def run_job_by_name(self, job_name, send_notifications=True):
        matching_job = self.get_job_by_name(job_name)
        assert matching_job, f'Found no jobs with the name "{job_name}"'
        assert matching_job.can_be_run_manually, 'This job can not be run manually'
        self.run_job(matching_job, send_notifications)

    def get_scheduled_jobs(self):
        now_in_timezone = maya.now().datetime(to_timezone=self.timezone)
        return [x for x in self.jobs if x.scheduled_to_run_in_this_hour(now_in_timezone)]

    def run_scheduled_jobs(self, send_notifications=True):
        jobs = self.get_scheduled_jobs()
        if jobs:
            self.run_jobs(jobs, send_notifications=send_notifications)
        else:
            print('No jobs to run right now')

    # def run_all_jobs(self, send_notifications=True):
    #     self.run_jobs(self.jobs, send_notifications=send_notifications)