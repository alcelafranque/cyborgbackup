import datetime
import logging

from django.conf import settings
from django.db import models
from django.utils.dateparse import parse_datetime
from django.utils.timezone import utc
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_text

from cyborgbackup.api.versioning import reverse
from cyborgbackup.main.fields import JSONField
from cyborgbackup.main.models.base import CreatedModifiedModel, PrimordialModel
from cyborgbackup.main.utils.common import could_be_script, copy_model_by_class, copy_m2m_relationships
from cyborgbackup.main.consumers import emit_channel_notification

analytics_logger = logging.getLogger('cyborgbackup.models.Repository')

__all__ = ['Repository']

class Repository(PrimordialModel):

    name = models.CharField(
        max_length=1024,
    )

    path = models.CharField(
        max_length=1024,
    )

    enabled = models.BooleanField(
        default=True
    )

    repository_key = models.CharField(
        max_length=1024,
    )

    ready = models.BooleanField(
        default=False
    )

    original_size = models.BigIntegerField(
        default=0
    )

    compressed_size = models.BigIntegerField(
        default=0
    )

    deduplicated_size = models.BigIntegerField(
        default=0
    )

    latest_prepare = models.DateTimeField(
        null=True,
        default=None,
        editable=False,
    )

    def get_absolute_url(self, request=None):
        return reverse('api:repository_detail', kwargs={'pk': self.pk}, request=request)

    def get_ui_url(self):
        return "/#/repositories/{}".format(self.pk)

    def save(self, *args, **kwargs):
        #encrypted = settings_registry.is_setting_encrypted(self.key)
        encrypted = False
        # If update_fields has been specified, add our field names to it,
        # if it hasn't been specified, then we're just doing a normal save.
        update_fields = kwargs.get('update_fields', [])
        # When first saving to the database, don't store any encrypted field
        # value, but instead save it until after the instance is created.
        # Otherwise, store encrypted value to the database.
        if encrypted:
                self.value = encrypt_field(self, 'value')
                if 'value' not in update_fields:
                    update_fields.append('value')
        super(Repository, self).save(*args, **kwargs)

    @classmethod
    def get_cache_key(self, key):
        return key

    @classmethod
    def get_cache_id_key(self, key):
        return '{}_ID'.format(key)

    @classmethod
    def _get_job_class(cls):
        from cyborgbackup.main.models.jobs import Job
        return Job

    def create_prepare_repository(self, **kwargs):
        '''
        Create a new prepare job for this repository.
        '''
        eager_fields = kwargs.pop('_eager_fields', None)

        job_class = self._get_job_class()
        fields = ('extra_vars', 'job_type')
        unallowed_fields = set(kwargs.keys()) - set(fields)
        if unallowed_fields:
            logger.warn('Fields {} are not allowed as overrides.'.format(unallowed_fields))
            map(kwargs.pop, unallowed_fields)

        job = copy_model_by_class(self, job_class, fields, kwargs)

        if eager_fields:
            for fd, val in eager_fields.items():
                setattr(job, fd, val)

        # Set the job back-link on the job
        job.repository_id = self.pk
        job.name = "Prepare Repository {}".format(self.name)
        job.description = "Repository {} Borg Preparation".format(self.name)
        job.save()

        from cyborgbackup.main.signals import disable_activity_stream
        fields = ()
        with disable_activity_stream():
            copy_m2m_relationships(self, job, fields, kwargs=kwargs)

        #job.create_config_from_prompts(kwargs)

        return job
