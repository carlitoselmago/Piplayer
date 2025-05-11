# setup.py

from setuptools import setup, find_packages

setup(
    name='piplayer',
    version='0.1.0',
    author='Carlos',
    description='Lightweight audio and GPIO sequencer for Raspberry Pi.',
    packages=find_packages(),
    python_requires='>=3.7',
    install_requires=[
        'mido',
        'RPi.GPIO',
        'pydub',
        'simpleaudio'.
        'mpv'
    ],

    entry_points={
        "console_scripts": [
            "piplayer=piplayer.cli:main",
            "piplayer-setup=piplayer.piplayer_setup:main",
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: POSIX :: Linux',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Multimedia :: Sound/Audio :: Players',
        'License :: OSI Approved :: MIT License',
    ],
)