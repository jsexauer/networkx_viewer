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

    def __getstate__(self):
        """Because the token object is a live tk object, we must save our
        state variables and reconstruct ourselves instead of letting python
        try to automatically pickle us"""
        ans = {
            '_complete': self._complete,
            '_default_bg': self._default_bg,
            '_marked': self._marked,
        }
        return ans


    def _setstate(self, state):
        """Set state from pickle.  See __getstate__ for details. Not
        __setstate__ because this must be a live tk object to work and python
        could call __setstate__ on an "undead" object."""
        for k,v in state.items():
            setattr(self, k, v)

        # Make sure we display our marked status
        if state['_marked']:
            self._marked = False    # Have to undo what we did in for loop above
            self.mark()

class EdgeToken(object):
    def __init__(self, edge_data):
        """This object mimics a token for the edges.  All of this class's
        returned values are used to configure the actual line drawn
        on the host canvas"""
        self.edge_data = edge_data
        self._marked = False
        self._spline_id = None
        self._host_canvas = None

    def render(self, host_canvas, coords, cfg=None, directed=False):
        """Called whenever canvas is about to draw an edge.
        The host_canvas will be the GraphCanvas object.
        coords is a tuple of the following, use to display the spline which
                    represents the edge.
            - x1,y1 -- Position of the start of the spline
            - xa,ya -- Position of the midpoint of spline
            - x2,y2 -- Position of the end of teh spline
        """
        if cfg is None:
            cfg = self.render_cfg()
        # Amend config options to include options which must be included
        cfg['tags'] = 'edge'
        cfg['smooth'] = True
        if directed:
            # Add arrow
            cfg['arrow'] = tk.LAST
            cfg['arrowshape'] = (30,40,5)
        self._spline_id = host_canvas.create_line(*coords, **cfg)
        self._host_canvas = host_canvas

    def itemconfig(self, cfg=None):
        """Update item config for underlying spline.  If cfg is none,
        auto-regenerate cfg from render_cfg method"""
        if cfg is None:
            cfg = self.render_cfg()
        assert self._host_canvas is not None, "Must draw using render method first"
        self._host_canvas.itemconfig(self._spline_id, cfg)

    def coords(self, coords):
        """Update coordinates for spline."""
        assert self._host_canvas is not None, "Must draw using render method first"
        return self._host_canvas.coords(self._spline_id, coords)

    def delete(self):
        """Remove spline from canvas"""
        self._host_canvas.delete(self._spline_id)

    def render_cfg(self):
        """Creates  config dict used by host canvas's create_line
        method to draw the spline"""
        return {}

    @property
    def id(self):
        """Returns id of spline drawn on host canvas"""
        return self._spline_id

    def mark(self):
        """Return config dictionary when toggling mark status"""
        mark_width = 4.0

        self._marked = not self._marked
        cfg = {}
        if self._marked:
            cfg = {'width': mark_width}
        else:
            cfg = {'width': 1.0}

        self.itemconfig(cfg)

    @property
    def is_marked(self):
        return self._marked

    def customize_menu(self, menu):
        """Ovewrite this method to customize the menu this token displays
        when it is right-clicked"""
        pass

    def __getstate__(self):
        """Because the token object is a live tk object, we must save our
        state variables and reconstruct ourselves instead of letting python
        try to automatically pickle us"""
        ans = {
            '_marked': self._marked,
        }
        return ans

    def _setstate(self, state):
        """Set state from pickle.  See __getstate__ for details. Not
        __setstate__ because this must be a live tk object to work and python
        could call __setstate__ on an "undead" object."""
        for k,v in state.items():
            setattr(self, k, v)

        # Make sure we display our marked status
        if state['_marked']:
            self._marked = False    # Have to undo what we did in for loop above
            self.mark()


class TkPassthroughNodeToken(NodeToken):
    def __init__(self, *args, **kwargs):
        self._default_label_color = 'black'
        self._default_outline_color = 'black'

        NodeToken.__init__(self, *args, **kwargs)


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
        self._default_outline_color = data.get('outline',self._default_outline_color)

        # Modify the text label using options from data
        cfg = self.itemconfig(self.label)
        for k,v in cfg.copy().items():
            cfg[k] = data.get('label_'+k, cfg[k][-1])
        self.itemconfig(self.label, **cfg)
        self._default_label_color = data.get('label_fill',self._default_label_color)

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
        self._complete = True
        self.itemconfig(self.marker, outline=self._default_outline_color)
        self.itemconfig(self.label, fill=self._default_label_color)

    def mark_incomplete(self):
        """Called by host canvas when all of my edges have not been drawn"""
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

    def render_cfg(self):
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

        cfg = {}
        if self._marked:
            cfg = {'width': self._marked_width}
        else:
            cfg = {'width': self._native_width}

        self.itemconfig(cfg)
