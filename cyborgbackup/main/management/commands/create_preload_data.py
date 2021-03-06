from django.core.management.base import BaseCommand
from django.core.management import call_command
from crum import impersonate
from cyborgbackup.main.models import Policy, Client, Repository, Schedule
from django.contrib.auth import get_user_model
from cyborgbackup.main.models.settings import Setting
#from cyborgbackup.main.signals import disable_computed_fields


class Command(BaseCommand):
    """Create preloaded data, intended for new installs
    """
    help = 'Creates a preload tower data iff there is none.'

    def handle(self, *args, **kwargs):
        # Sanity check: Is there already an organization in the system?
        if Setting.objects.count():
            print('System is already configured, exiting.')
            print('(changed: False)')
            return

        User = get_user_model()
        User.objects.create_superuser('admin@cyborg.local', 'adminadmin')

        call_command("loaddata", "settings")

        # Create a default organization as the first superuser found.
        try:
            superuser = User.objects.filter(is_superuser=True).order_by('pk')[0]
        except IndexError:
            superuser = None
        with impersonate(superuser):
            r = Repository.objects.create(
                name='Demo Repository',
                path='/tmp/repository',
                repository_key='0123456789abcdef',
                enabled=False)
            s = Schedule.objects.create(name='Demo Schedule',
                crontab='0 5 * * MON *',
                enabled=False)
            c = Client.objects.create(hostname='localhost',
                enabled=False)
            p = Policy(name='Demo Policy',
                        mode_pull=False,
                        enabled=False,
                        repository=r,
                        schedule=s)
            p.save(skip_update=True)
            p.clients.add(c)
        print('Demo Client, Repository, Schedule and Policy added.')
        print('(changed: True)')
