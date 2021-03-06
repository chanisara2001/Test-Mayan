import errno
import os

from django.conf import settings
from django.core import management
from django.core.management.utils import get_random_secret_key

import mayan
from mayan.settings.literals import (
    DEFAULT_USER_SETTINGS_FOLDER, SECRET_KEY_FILENAME, SYSTEM_DIR
)
from mayan.apps.storage.utils import touch

from ...signals import signal_post_initial_setup, signal_pre_initial_setup


class Command(management.BaseCommand):
    help = 'Initializes an install and gets it ready to be used.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true', dest='force',
            help='Force execution of the initialization process.',
        )

        parser.add_argument(
            '--no-dependencies', action='store_true', dest='no_dependencies',
            help='Don\'t download dependencies.',
        )

    def initialize_system(self, force=False):
        system_path = os.path.join(settings.MEDIA_ROOT, SYSTEM_DIR)
        settings_path = os.path.join(
            settings.MEDIA_ROOT, DEFAULT_USER_SETTINGS_FOLDER
        )
        secret_key_file_path = os.path.join(system_path, SECRET_KEY_FILENAME)

        if not os.path.exists(path=settings.MEDIA_ROOT) or force:
            # Create the media folder
            try:
                os.makedirs(name=settings.MEDIA_ROOT)
            except OSError as exception:
                if exception.errno == errno.EEXIST and force:
                    """Folder already exists. Ignore."""
                else:
                    raise

            # Touch media/__init__.py
            touch(os.path.join(settings.MEDIA_ROOT, '__init__.py'))

            # Create user settings folder
            try:
                os.makedirs(name=settings_path)
            except OSError as exception:
                if exception.errno == errno.EEXIST and force:
                    """Folder already exists. Ignore."""
                else:
                    raise

            # Touch media/settings/__init__.py
            touch(filename=os.path.join(settings_path, '__init__.py'))

            # Create the media/system folder
            try:
                os.makedirs(name=system_path)
            except OSError as exception:
                if exception.errno == errno.EEXIST and force:
                    """Folder already exists. Ignore."""
                else:
                    raise

            version_file_path = os.path.join(system_path, 'VERSION')
            with open(file=version_file_path, mode='w') as file_object:
                file_object.write(mayan.__version__)

            with open(file=secret_key_file_path, mode='w') as file_object:
                secret_key = get_random_secret_key()
                file_object.write(secret_key)

            settings.SECRET_KEY = secret_key
        else:
            self.stdout.write(
                self.style.NOTICE(
                    'Existing media files at: {0}. Backup, remove this folder, '
                    'and try again. Or use the --force argument'.format(
                        settings.MEDIA_ROOT
                    )
                )
            )

    def handle(self, *args, **options):
        self.initialize_system(force=options.get('force', False))
        signal_pre_initial_setup.send(sender=self)

        if not options.get('no_dependencies', False):
            management.call_command(command_name='installdependencies')
            management.call_command(
                command_name='preparestatic', interactive=False
            )

        management.call_command(command_name='createautoadmin')
        management.call_command(command_name='savesettings')
        signal_post_initial_setup.send(sender=self)
