from setuptools import setup, find_packages
import sys, os

# python setup.py check

# To upldate to PyPI test server
#   http://peterdowns.com/posts/first-time-with-pypi.html
# python setup.py register -r pypitest
# python setup.py sdist upload -r pypitest
# Test repo is at: https://testpypi.python.org/pypi

# To distribute on PyPI:
# python setup.py register sdist upload

from networkx_viewer import __version__ as version

setup(name='networkx_viewer',
      version=version,
      description="Interactive viewer for networkx graphs.",
      long_description=open('README.md').read(),
      classifiers=[
          'Development Status :: 4 - Beta',
          'Topic :: Scientific/Engineering :: Mathematics',
          'Topic :: Scientific/Engineering :: Visualization',
          'Natural Language :: English',
          'License :: OSI Approved :: GNU General Public License (GPL)',
      ], # Get from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='networkx, topology, graph theory',
      author='Jason Sexauer',
      author_email='genericcarbonlifeform@gmail.com',
      url='http://github.com/jsexauer/networkx_viewer',
      license='LICENSE.txt',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      setup_requires=['networkx>=1.4'],
      install_requires=[
          'networkx>=1.4'
      ],
      )