try:
    # Python 3
    import tkinter as tk
except ImportError:
    # Python 2
    import Tkinter as tk

class NodeToken(tk.Canvas):
    def __init__(self, host_canvas, data, node_name):
        tk.Canvas.__init__(self, width=20, height=20, highlightthickness=0)

        self._host_canvas = host_canvas
        self._complete = True
        self._marked = False
        self._default_bg = None

        self.bind('<ButtonPress-1>', self._host_event('onNodeButtonPress'))
        self.bind('<ButtonRelease-1>', self._host_event('onNodeButtonRelease'))
        self.bind('<B1-Motion>', self._host_event('onNodeMotion'))

        self.bind('<Button-3>', self._host_event('onTokenRightClick'))

        self.bind('<Key>', self._host_event('onNodeKey'))
        self.bind('<Enter>', lambda e: self.focus_set())
        self.bind('<Leave>', lambda e: self.master.focus())

        # Draw myself
        self.render(data, node_name)

    def render(self, data, node_name):
        """Draw on canvas what we want node to look like"""
        self.create_oval(5,5,15,15, fill='red',outline='black')


    def mark(self):
        """Mark the token just so it's easy for the user to pick out"""
        if self._marked:
            self.config(bg=self._default_bg)
        else:
            self._default_bg = self['background']
            self.config(bg='yellow')
        self._marked = not self._marked

    def mark_complete(self):
        """Called by host canvas when all of my edges have been drawn"""
        if not self._complete:
            self._complete = True

    def mark_incomplete(self):
        """Called by host canvas when all of my edges have not been drawn"""
        if self._complete:
            self._complete = False

    @property
    def is_marked(self):
        return self._marked

    @property
    def is_complete(self):
        """Returns True if all edges have been drawn"""
        return self._complete

    def customize_menu(self, menu, item):
        """Ovewrite this method to customize the menu this token displays
        when it is right-clicked"""
        pass


    def _host_event(self, func_name):
        """Wrapper to correct the event's x,y coordinates and pass to host
        canvas.  Argument should be string of name of function from
        _host_canvas to call."""
        func = getattr(self._host_canvas, func_name)
        def _wrapper(event):
            # Modify even to be relative to the host's canvas
            event.x += self.winfo_x()
            event.y += self.winfo_y()
            return func(event)
        return _wrapper

class EdgeToken(object):
    def __init__(self, edge_data):
        """This object mimics a token for the edges.  All of this class's
        returned values are used to configure the actual line drawn
        on the host canvas"""
        self.edge_data = edge_data
        self._marked = False

    def render(self):
        """Called whenever canvas is about to draw an edge.
        Must return dictionary of config options for create_line"""
        return {}

    def mark(self):
        """Return config dictionary when toggling mark status"""
        mark_width = 4.0

        self._marked = not self._marked

        if self._marked:
            return {'width': mark_width}
        else:
            return {'width': 1.0}

    @property
    def is_marked(self):
        return self._marked

    def customize_menu(self, menu):
        """Ovewrite this method to customize the menu this token displays
        when it is right-clicked"""
        pass

class TkPassthroughNodeToken(NodeToken):
    def render(self, data, node_name):
        """Draw on canvas what we want node to look like.  If data contains
        keys that can configure a tk.Canvas oval, it will do so.  If data
        contains keys that start with "label_" and can configure a text
        object, it will configure the text."""

        # Take a first cut at creating the marker and label
        self.label = self.create_text(0, 0, text=node_name)
        self.marker = self.create_oval(0, 0, 10, 10,
                                       fill='red',outline='black')

        # Modify marker using options from data
        cfg = self.itemconfig(self.marker)
        for k,v in cfg.copy().items():
            cfg[k] = data.get(k, cfg[k][-1])
        self.itemconfig(self.marker, **cfg)

        # Modify the text label using options from data
        cfg = self.itemconfig(self.label)
        for k,v in cfg.copy().items():
            cfg[k] = data.get('label_'+k, cfg[k][-1])
        self.itemconfig(self.label, **cfg)

        # Figure out how big we really need to be
        bbox = self.bbox(self.label)
        bbox = [abs(x) for x in bbox]
        br = ( max((bbox[0] + bbox[2]),20), max((bbox[1]+bbox[3]),20) )

        self.config(width=br[0], height=br[1]+7)

        # Place label and marker
        mid = ( int(br[0]/2.0), int(br[1]/2.0)+7 )
        self.coords(self.label, mid)
        self.coords(self.marker, mid[0]-5,0, mid[0]+5,10)


    def mark_complete(self):
        """Called by host canvas when all of my edges have been drawn"""
        if not self._complete:
            self._complete = True
            self.itemconfig(self.marker, outline='black')
            self.itemconfig(self.label, fill='black')

    def mark_incomplete(self):
        """Called by host canvas when all of my edges have not been drawn"""
        if self._complete:
            self._complete = False
            self.itemconfig(self.marker, outline='')
            self.itemconfig(self.label, fill='grey')


class TkPassthroughEdgeToken(EdgeToken):
    _tk_line_options = [
        'stipple', 'activefill', 'joinstyle', 'dash',
        'disabledwidth', 'dashoffset', 'activewidth', 'fill', 'splinesteps',
        'offset', 'disabledfill', 'disableddash', 'width', 'state',
        'disabledstipple', 'activedash', 'tags', 'activestipple',
        'capstyle', 'arrowshape', 'smooth', 'arrow'
    ]
    _marked_width = 4.0

    def render(self):
        """Called whenever canvas is about to draw an edge.
        Must return dictionary of config options for create_line"""
        cfg = {}
        for k in self._tk_line_options:
            v = self.edge_data.get(k, None)
            if v:
                cfg[k] = v
        self._native_width = cfg.get('width', 1.0)
        return cfg

    def mark(self):
        """Return config dictionary when toggling marked status"""
        self._marked = not self._marked

        if self._marked:
            return {'width': self._marked_width}
        else:
            return {'width': self._native_width}
