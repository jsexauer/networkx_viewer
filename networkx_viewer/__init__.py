__version__ = '0.2.0'


from .graph_canvas import GraphCanvas
from .tokens import (NodeToken, EdgeToken, TkPassthroughNodeToken,
                    TkPassthroughEdgeToken)
from .viewer import ViewerApp, TkPassthroughViewerApp

BasicViewer = ViewerApp
Viewer = TkPassthroughViewerApp