from setuptools import setup


setup(
    name='prowl',
    version='0.1',
    description='Command line tool to interact with the Prowl API from '
                'https://www.prowlapp.com/.',
    maintainer='Michael Schwarz',
    maintainer_email='michi.schwarz@gmail.com',
    url='https://github.com/Feuermurmel/prowl',
    install_requires=['requests'],
    py_modules=['prowl'],
    entry_points=dict(
        console_scripts=[
            'prowl = prowl:script_main']))
