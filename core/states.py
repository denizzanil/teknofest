from core.cpwrap import PropsSI

class State:
    def __init__(self, fluid="Water"):
        self.fluid = fluid
        self.P = None
        self.T = None
        self.h = None
        self.s = None
        self.m_dot = None
        self.fixed = set()

    def set_value(self, name, value, fixed=False):
        setattr(self, name, value)
        if fixed:
            try:
                self.fixed.add(name)
            except Exception:
                pass

    def is_fixed(self, name):
        return name in self.fixed

    def update(self):
        updated = False
        try:
            if self.P is not None and self.T is not None:
                if self.h is None and not self.is_fixed('h'):
                    self.h = PropsSI('H', 'P', self.P, 'T', self.T, self.fluid)
                    updated = True
                if self.s is None and not self.is_fixed('s'):
                    self.s = PropsSI('S', 'P', self.P, 'T', self.T, self.fluid)
                    updated = True

            if self.P is not None and self.h is not None:
                if self.T is None and not self.is_fixed('T'):
                    self.T = PropsSI('T', 'P', self.P, 'H', self.h, self.fluid)
                    updated = True
                if self.s is None and not self.is_fixed('s'):
                    self.s = PropsSI('S', 'P', self.P, 'H', self.h, self.fluid)
                    updated = True

            if self.P is not None and self.s is not None:
                if self.T is None and not self.is_fixed('T'):
                    self.T = PropsSI('T', 'P', self.P, 'S', self.s, self.fluid)
                    updated = True
                if self.h is None and not self.is_fixed('h'):
                    self.h = PropsSI('H', 'P', self.P, 'S', self.s, self.fluid)
                    updated = True

            if self.T is not None and self.s is not None:
                if self.P is None and not self.is_fixed('P'):
                    self.P = PropsSI('P', 'T', self.T, 'S', self.s, self.fluid)
                    updated = True
                if self.h is None and not self.is_fixed('h'):
                    self.h = PropsSI('H', 'T', self.T, 'S', self.s, self.fluid)
                    updated = True

        except ValueError:
            pass

        return updated