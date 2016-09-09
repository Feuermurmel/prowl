import argparse
import getpass
import json
import os
import re
import requests
import socket
import sys


def log(message, *args):
    line = '{}: {}'.format(os.path.basename(sys.argv[0]), message.format(*args))

    print(line, file=sys.stderr)


def read_file(path):
    with open(path, 'rb') as file:
        return file.read()


def write_file(path, data):
    dir = os.path.dirname(path)
    temp_path = path + '~'

    if not os.path.exists(dir):
        os.makedirs(dir)

    with open(temp_path, 'wb') as file:
        file.write(data)

    os.rename(temp_path, path)


class UserError(Exception):
    def __init__(self, msg, *args):
        self.message = msg.format(*args)


class Settings:
    def __init__(self, path):
        self._path = path
        self._values = None

    def _load_values(self):
        if self._values is None:
            if os.path.exists(self._path):
                self._values = json.loads(read_file(self._path).decode())
            else:
                self._values = {}

    def _save_values(self):
        if self._values is not None:
            write_file(self._path, json.dumps(self._values).encode())

    def get(self, key, default=None):
        self._load_values()

        return self._values.get(key, default)

    def set(self, key, value):
        self._load_values()

        self._values[key] = value

        self._save_values()


def api_key_type(value):
    if not re.match('[0-9a-f]{40}$', value):
        raise UserError('Invalid API key specified.')

    return value


def api_argument_type(value):
    """
    A workaround for the Prowl API not accepting the string "0" as a valid
    argument.
    """
    if value == '0':
        value += ' '

    return value


def parse_args():
    usage = '\n'.join([
        'prowl --help',
        '       prowl --set-api-key=<api-key>',
        '       prowl [<options>] [[<event>] <description>]'])

    parser = argparse.ArgumentParser(
        description='Deliver a notification using Prowl for iOS.',
        usage=usage)

    parser.add_argument(
        'event',
        type=api_argument_type,
        nargs='?',
        help='The event part of the notification.')

    parser.add_argument(
        'description',
        type=api_argument_type,
        nargs='?',
        help='The description part of the notification. Defaults to the URL '
             'specified using --url, if one is specified. Otherwise the '
             'description is mandatory,')

    parser.add_argument(
        '-a',
        '--application',
        type=api_argument_type,
        help='The application part of the notification. Defaults current '
             'user\'s name and the host\'s name in the form of '
             '<username>@<hostname>.')

    parser.add_argument(
        '-u',
        '--url',
        help='URL that should be opened when the notification is activated.')

    parser.add_argument(
        '-p',
        '--priority',
        type=int,
        default=0,
        help='The priority of the notification. Specify a number from -2 to 2. '
             'Defaults to 0.')

    parser.add_argument(
        '-k',
        '--api-key',
        type=api_key_type,
        help='API key to use for the notification.')

    parser.add_argument(
        '--set-api-key',
        type=api_key_type,
        help='Set the default API key used for calls where -k is not '
             'specified.')

    args = parser.parse_args()

    if args.set_api_key is None:
        # If no event is given, the description is actually stored in event.
        if args.event is None:
            if args.url is None:
                raise UserError('Required argument `description\' missing.')
            else:
                args.event = args.url

        if args.description is None:
            args.description = args.event
            args.event = None

        if not (-2 <= args.priority <= 2):
            raise UserError('Invalid value for --priority: {}', args.priority)
    else:
        if args.event is not None \
                or args.description is not None \
                or args.application is not None \
                or args.url is not None \
                or args.priority != 0 \
                or args.api_key is not None:
            raise UserError('Cannot use --set-api-key with any other arguments '
                            'or options.')

    return args


def main(event, description, application, url, priority, api_key, set_api_key):
    settings = Settings(
        os.path.join(os.path.expanduser('~'), 'opt/etc/prowl.json'))

    if set_api_key is None:
        api_key = api_key
        application = application

        if api_key is None:
            api_key = settings.get('default-api-key')

            if api_key is None:
                raise UserError('--api-key is mandatory if because default '
                                'API key has been set.')

        if application is None:
            application = '{}@{}'.format(getpass.getuser(), socket.gethostname())

        def iter_arguments():
            yield 'apikey', api_key
            yield 'application', application

            if url is not None:
                yield 'url', url

            if event is not None:
                yield 'event', event

            if description:
                yield 'description', description

            if priority:
                yield 'priority', priority

        response = requests.post(
            'https://api.prowlapp.com/publicapi/add',
            dict(iter_arguments()))

        if not response.ok:
            raise UserError('Error received from server: {}', response.content)
    else:
        settings.set('default-api-key', set_api_key)


def script_main():
    try:
        main(**vars(parse_args()))
    except UserError as e:
        log('Error: {}', e)
        sys.exit(1)
    except KeyboardInterrupt:
        log('Operation interrupted.')
        sys.exit(2)
