from setuptools import setup, find_packages
import sys, os

# python setup.py check
# python.exe setup.py --long-description | rst2html.py > dummy.html

# To upload to PyPI test server
#   http://peterdowns.com/posts/first-time-with-pypi.html
# python setup.py register -r pypitest
# python setup.py sdist upload -r pypitest
# Test repo is at: https://testpypi.python.org/pypi

# To distribute on PyPI:
# python setup.py register sdist upload

from networkx_viewer import __version__ as version

long_desc = """
NetworkX Viewer provides a basic interactive GUI to view
`networkx <https://networkx.github.io/>`_ graphs.  In addition to standard
plotting and layout features as found natively in networkx, the GUI allows
you to:

  - Drag nodes around to tune the default layout
  - Show and hide nodes
  - Filter nodes
  - Pan and zoom
  - Display nodes only within a certain number of hops ("levels") of
    a "home node"
  - Display and highlight the shortest path between two nodes.  Nodes
    around the path can also be displayed within a settable number of
    levels
  - Intelligently find and display nodes near displayed nodes using
    "Grow" and "Grow Until" functions
  - Use attributes stored in the graph's node and edge dictionaries to
    customize the appearance of the node and edge tokens in the GUI
  - Mark nodes and edges for reference
  - Support for both `nx.Graph` and `nx.MultiGraph`

See https://github.com/jsexauer/networkx_viewer for more details
"""

setup(name='networkx_viewer',
      version=version,
      description="Interactive viewer for networkx graphs.",
      long_description=long_desc,
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