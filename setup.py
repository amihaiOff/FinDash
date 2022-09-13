# !/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


README = ''
with open('README.md', encoding="utf-8") as f:
    README = f.read()

INSTALL_REQUIRES = []
TEST_REQUIRES = [
    # testing and coverage
    'pytest', 'coverage', 'pytest-cov', 'pytest-ordering',
    # non-testing packagesrequired by tests, not by the package
    'scikit-learn', 'pdutil', 'nltk', 'xdg',
    # dev scripts
    'rich',
    # to be able to run `python setup.py checkdocs`
    'collective.checkdocs', 'pygments',
]


setup(
        name='fin_dash',
        description="Financial Dashboard for cash flow management",
        long_description=README,
        long_description_content_type='text/markdown',
        author="Amihai Offenbacher",
        author_email="amihaio@gmail.com",
        packages=find_packages(),
        install_requires=INSTALL_REQUIRES,
        extras_require={
            'test': TEST_REQUIRES
        },
        platforms=['any'],
        keywords='',
        classifiers=[],
)
