# coding=utf-8
u"""Create a Radiance view."""
from __future__ import division
import honeybee.typing as typing
import honeybee_radiance.parser as parser
import math
import os
from copy import deepcopy
import ladybug_geometry.geometry3d.pointvector as pv
import ladybug_geometry.geometry3d.plane as plane
import ladybug.futil as futil
from honeybee_radiance_command.options import BoolOption, TupleOption, \
    StringOptionJoined, NumericOption


class View(object):
    u"""A Radiance view.

    Usage:

        v = View()
        # add a fore clip
        v.fore_clip = 100
        print(v)

        > -vtv -vp 0.000 0.000 0.000 -vd 0.000 0.000 1.000 -vu 0.000 1.000
           0.000 -vh 60.000 -vv 60.000 -vo 100.000

        # split the view into a view grid
        gridViews = v.grid(2, 2, 600, 600)
        for g in gridViews:
            print(g)

        > -vtv -vp 0.000 0.000 0.000 -vd 0.000 0.000 1.000 -vu 0.000 1.000
           0.000 -vh 29.341 -vv 32.204  -vs -0.500 -vl -0.500 -vo 100.000

        > -vtv -vp 0.000 0.000 0.000 -vd 0.000 0.000 1.000 -vu 0.000 1.000
           0.000 -vh 29.341 -vv 32.204 -vs 0.500 -vl -0.500 -vo 100.000

        > -vtv -vp 0.000 0.000 0.000 -vd 0.000 0.000 1.000 -vu 0.000 1.000
           0.000 -vh 29.341 -vv 32.204 -vs -0.500 -vl 0.500 -vo 100.000

        > -vtv -vp 0.000 0.000 0.000 -vd 0.000 0.000 1.000 -vu 0.000 1.000
          0.000 -vh 29.341 -vv 32.204 -vs 0.500 -vl 0.500 -vo 100.000
    """

    def __init__(self, name, position=None, direction=None, up_vector=None, type='v',
                 h_size=60, v_size=60, shift=None, lift=None):
        u"""Create a view.

        Arg:
            position: Set the view position (-vp) to (x, y, z). This is the focal
                point of a perspective view or the center of a parallel projection.
                Default: (0, 0, 0)
            direction: Set the view direction (-vd) vector to (x, y, z). The
                length of this vector indicates the focal distance as needed by
                the pixel depth of field (-pd) in rpict. Default: (0, 0, 1)
            up_vector: Set the view up (-vu) vector (vertical direction) to
                (x, y, z) default: (0, 1, 0).
            type: Set view type (-vt) to one of the choices below.
                    0 - Perspective (v)
                    1 - Hemispherical fisheye (h)
                    2 - Parallel (l)
                    3 - Cylindrical panoroma (c)
                    4 - Angular fisheye (a)
                    5 - Planisphere [stereographic] projection (s)
                For more detailed description about view types check rpict manual
                page: (http://radsite.lbl.gov/radiance/man_html/rpict.1.html)
            h_size: Set the view horizontal size (-vh). For a perspective
                projection (including fisheye views), val is the horizontal field
                of view (in degrees). For a parallel projection, val is the view
                width in world coordinates.
            v_size: Set the view vertical size (-vv). For a perspective
                projection (including fisheye views), val is the horizontal field
                of view (in degrees). For a parallel projection, val is the view
                width in world coordinates.
            shift: Set the view shift (-vs). This is the amount the actual
                image will be shifted to the right of the specified view. This
                option is useful for generating skewed perspectives or rendering
                an image a piece at a time. A value of 1 means that the rendered
                image starts just to the right of the normal view. A value of -1
                would be to the left. Larger or fractional values are permitted
                as well.
            lift: Set the view lift (-vl) to a value. This is the amount the
                actual image will be lifted up from the specified view.
        """
        self.name = name
        self._position = TupleOption(
            'vp', 'view position', position if position is not None else (0, 0, 0)
        )
        self._direction = TupleOption(
            'vd', 'view direction', direction if direction is not None else (0, 0, 1)
        )
        self._up_vector = TupleOption(
            'vu', 'view up vector', up_vector if up_vector is not None else (0, 1, 0)
        )
        self._h_size = NumericOption('vh', 'view horizontal size', h_size, min_value=0)
        self._v_size = NumericOption('vv', 'view vertical size', v_size, min_value=0)
        self._shift = NumericOption('vs', 'view shift', shift)
        self._lift =  NumericOption('vl', 'view lift', lift)
        self._type = StringOptionJoined(
            'vt', 'view type', type, valid_values=['v', 'h', 'l', 'c', 'a', 's']
        )
        # set for_clip to None
        self._fore_clip = NumericOption('vo', 'view fore clip')
        self._aft_clip = NumericOption('va', 'view aft clip')

    @property
    def name(self):
        """AnalysisGrid name."""
        return self._name

    @name.setter
    def name(self, n):
        self._name = typing.valid_string(n)

    @property
    def is_fisheye(self):
        """Check if the view type is one of the fisheye views."""
        return self.type in ('h', 'a', 's')

    @property
    def type(self):
        """Set and get view type (-vt) to one of the choices below.

        v - Perspective (v), h - Hemispherical fisheye (h),
        l - Parallel (l),    c - Cylindrical panorma (c),
        a - Angular fisheye (a),
        s - Planisphere [stereographic] projection (s)
        """
        return self._type

    @property
    def vt(self):
        """View type as a string in radiance format."""
        return self._type.to_radiance()

    @type.setter
    def type(self, value):
        self._type.value = value[-1:]  # this will handle both vtv and v inputs

        # set view size to 180 degrees for fisheye views
        if self.type in ('h', 'a', 's'):
            if self.h_size != 180:
                self.h_size = 180
                print("Changed h_size to 180 for fisheye view type.")
            if self.v_size != 180:
                self.v_size = 180
                print("Changed v_size to 180 for fisheye view type.")

        elif self.type == 'v':
            assert self.h_size < 180, ValueError(
                '\n{} is an invalid horizontal view size for Perspective view.\n'
                'The size should be smaller than 180.'.format(self.h_size))
            assert self.v_size < 180, ValueError(
                '\n{} is an invalid vertical view size for Perspective view.\n'
                'The size should be smaller than 180.'.format(self.v_size))

    @property
    def position(self):
        """Set the view position (-vp) to (x, y, z).

        This is the focal point of a perspective view or the center of a parallel
        projection. Default: (0, 0, 0)
        """
        return self._position

    @property
    def vp(self):
        """View point / position as a string in radiance format."""
        return self._position.to_radiance()

    @position.setter
    def position(self, value):
        self._position.value = value

    @property
    def direction(self):
        """Set the view direction (-vd) vector to (x, y, z).

        The length of this vector indicates the focal distance as needed by
        the pixel depth of field (-pd) in rpict. Default: (0, 0, 1)
        """
        return self._direction

    @property
    def vd(self):
        """View direction as a string in radiance format."""
        return self._direction.to_radiance()

    @direction.setter
    def direction(self, value):
        self._direction.value = value

    @property
    def up_vector(self):
        """Set and get the view up (-vu) vector (vertical direction) to (x, y, z)

        Default: (0, 1, 0).
        """
        return self._up_vector

    @property
    def vu(self):
        """View up as a string in radiance format."""
        return self._up_vector.to_radiance()

    @up_vector.setter
    def up_vector(self, value):
        self._up_vector.value = value

    @property
    def h_size(self):
        """Set the view horizontal size (-vh).

        For a perspective projection (including fisheye views), val is the horizontal
        field of view (in degrees). For a parallel projection, val is the view
        width in world coordinates.
        """
        return self._h_size

    @property
    def vh(self):
        """View horizontal size as a string in radiance format."""
        return self._h_size.to_radiance()

    @h_size.setter
    def h_size(self, value):
        self._h_size.value = value if value is not None else 60

    @property
    def v_size(self):
        """Set the view vertical size (-vv).

        For a perspective projection (including fisheye views), val is the horizontal
        field of view (in degrees). For a parallel projection, val is the view width in
        world coordinates.
        """
        return self._v_size

    @property
    def vv(self):
        """View vertical size as a string in radiance format."""
        return self.v_size.to_radiance()

    @v_size.setter
    def v_size(self, value):
        self._v_size.value = value if value is not None else 60

    @property
    def shift(self):
        """Set the view shift (-vs).

        This is the amount the actual image will be shifted to the right of the specified
        view. This option is useful for generating skewed perspectives or rendering an
        image a piece at a time. A value of 1 means that the rendered image starts just
        to the right of the normal view. A value of -1 would be to the left. Larger or
        fractional values are permitted as well.
        """
        return self._shift

    @property
    def vs(self):
        """View shift as a string in radiance format."""
        return self._shift.to_radiance()

    @shift.setter
    def shift(self, value):
        self._shift.value = value

    @property
    def lift(self):
        """Set the view lift (-vl) to a value.

        This is the amount the actual image will be lifted up from the specified view.
        """
        return self._lift

    @property
    def vl(self):
        """View lift as a string in radiance format."""
        return self.lift.to_radiance()

    @lift.setter
    def lift(self, value):
        self._lift.value = value

    @property
    def fore_clip(self):
        """View fore clip (-vo) at a distance from the view point.

        The plane will be perpendicular to the view direction for perspective
        and parallel view types. For fisheye view types, the clipping plane is
        actually a clipping sphere, centered on the view point with radius val.
        Objects in front of this imaginary surface will not be visible. This may
        be useful for seeing through walls (to get a longer perspective from an
        exterior view point) or for incremental rendering. A value of zero implies
        no foreground clipping. A negative value produces some interesting effects,
        since it creates an inverted image for objects behind the viewpoint.
        """        
        return self._fore_clip

    @property
    def vo(self):
        """View fore clip as a string in radiance format."""
        return self._fore_clip.to_radiance()

    @fore_clip.setter
    def fore_clip(self, distance):
        self._fore_clip.value = distance

    @property
    def aft_clip(self):
        """View aft clip (-va) at a distance from the view point.

        Set the view aft clipping plane at a distance of val from the view point. Like
        the view fore plane, it will be perpendicular to the view direction for
        perspective and parallel view types. For fisheye view types, the clipping plane
        is actually a clipping sphere, centered on the view point with radius val.
        Objects behind this imaginary surface will not be visible. A value of zero means
        no aft clipping, and is the only way to see infinitely distant objects such as
        the sky.
        """
        return self._aft_clip

    @property
    def va(self):
        """View aft clip as a string in radiance format."""
        return self._aft_clip.to_radiance()

    @aft_clip.setter
    def aft_clip(self, distance):
        self._aft_clip.value = distance

    @classmethod
    def from_dict(cls, view_dict):
        """Create a view from a dictionary."""

        view = cls(
            name=view_dict['name'],
            position=view_dict['position'],
            direction=view_dict['direction'],
            up_vector=view_dict['up_vector'],
            h_size=view_dict['h_size'],
            v_size=view_dict['v_size'],
            shift=view_dict['shift'],
            lift=view_dict['lift'],
        )

        view.fore_clip = view_dict['fore_clip']
        view.aft_clip = view_dict['aft_clip']

        return view

    @classmethod
    def from_string(cls, name, view_string):
        """Create a view object from a string.
        
        This method is similar to from_string method for radiance parameters with the
        difference that all the parameters that are not related to view will be ignored.
        """
        mapper = {
            'name': name, 'vp': 'position', 'vd': 'direction', 'vu': 'up_vector',
            'vh': 'h_size', 'vv': 'v_size', 'vs': 'shift', 'vl': 'lift',
            'vo': 'fore_clip', 'va': 'aft_clip'
        }

        base = {
            'name': name,
            'position': None,
            'direction': None,
            'up_vector': None, 
            'h_size': None,
            'v_size': None,
            'shift': None,
            'lift': None,
            'type': None,
            'fore_clip': None,
            'aft_clip': None
        }

        # parse the string here
        options = parser.parse_radiance_options(view_string)

        for opt, value in options.items():
            if opt in mapper:
                base[mapper[opt]] = value
            elif opt[:2] == 'vt':
                base['type'] = opt
            else:
                print('%s is not a view parameter and is ignored.' % opt)

        return cls.from_dict(base)

    @classmethod
    def from_file(self, file_path, name=None):
        """Create view from a view file.

        Args:
            file_path: Full path to view file.
            name: Optional name for this view. View name will be set to file name if not
            provided.
        """

        if not os.path.isfile(file_path):
            raise IOError("Can't find {}.".format(file_path))
        name = name or os.path.split(os.path.splitext(file_path)[0])[-1]

        with open(file_path, 'r') as input_data:
            view_string = str(input_data.read()).rstrip()

        assert view_string[:3] == 'rvu', \
            'View file must start with rvu not %s' % view_string[:3]
        return self.from_string(name, view_string)

    def dimension(self, x_res=None, y_res=None):
        """Get dimensions for this view as '-x %d -y %d [-ld-]'.

        This method is same as vwrays -d. Default values for x_res and y_res are set to
        match Radiance defaults.
        """
        x, y = self.dimension_x_y(x_res, y_res)
        return '-x %d -y %d -ld%s' % (
            x, y,
            '-' if (self.fore_clip.to_radiance() + self.aft_clip.to_radiance() == '')
            else '+'
        )

    def dimension_x_y(self, x_res=None, y_res=None):
        """Get dimensions for this view as x, y.
        
        Default values for x_res and y_res are set to match Radiance defaults.
        """
        # radiance default is 512
        x_res = int(x_res) if x_res is not None else 512
        y_res = int(y_res) if y_res is not None else 512

        if self.is_fisheye:
            return min(x_res, y_res), min(x_res, y_res)

        vh = self.h_size.value
        vv = self.v_size.value

        if self.type == 'v':
            hv_ratio = math.tan(math.radians(vh) / 2.0) / \
                math.tan(math.radians(vv) / 2.0)
        else:
            hv_ratio = vh / vv

        # radiance keeps the largest max size and tries to scale the other size
        # to fit the aspect ratio. In case the size doesn't match it reverses
        # the process.
        if y_res <= x_res:
            new_x = int(round(hv_ratio * y_res))
            if new_x <= x_res:
                return new_x, y_res
            else:
                new_y = int(round(x_res / hv_ratio))
                return x_res, new_y
        else:
            new_y = int(round(x_res / hv_ratio))
            if new_y <= y_res:
                return x_res, new_y
            else:
                new_x = int(round(hv_ratio * y_res))
                return new_x, y_res

    def grid(self, x_div_count=1, y_div_count=1):
        """Break-down the view into a grid of views based on x and y grid count.

        Views will be returned row by row from right to left.

        Args:
            x_div_count: Set number of divisions in x direction (Default: 1).
            y_div_count: Set number of divisions in y direction (Default: 1).

        Returns:
            A tuple of views. Views are sorted row by row from right to left.
        """
        PI = math.pi
        try:
            x_div_count = abs(x_div_count)
            y_div_count = abs(y_div_count)
        except TypeError as e:
            raise ValueError("Division count should be a number.\n%s" % str(e))

        assert x_div_count * y_div_count != 0, "Division count should be larger than 0."

        if x_div_count == y_div_count == 1:
            return [self]

        _views = list(range(x_div_count * y_div_count))

        if self.type == 'l':
            # parallel view (vtl)
            _vh = self.h_size / x_div_count
            _vv = self.v_size / y_div_count

        elif self.type == 'v':
            # perspective (vtv)
            _vh = (2. * 180. / PI) * \
                math.atan(((PI / 180. / 2.) * self.h_size) / x_div_count)
            _vv = (2. * 180. / PI) * \
                math.atan(math.tan((PI / 180. / 2.) * self.v_size) / y_div_count)

        elif self.is_fisheye:
            # fish eye
            _vh = (2. * 180. / PI) * \
                math.asin(math.sin((PI / 180. / 2.) * self.h_size) / x_div_count)
            _vv = (2. * 180. / PI) * \
                math.asin(math.sin((PI / 180. / 2.) * self.v_size) / y_div_count)

        else:
            print("Grid views are not supported for %s." % self.type.to_radiance())
            return [self]

        # create a set of new views
        for view_count in range(len(_views)):
            # calculate view shift and view lift
            if x_div_count == 1:
                _vs = 0
            else:
                _vs = (((view_count % x_div_count) / (x_div_count - 1)) - 0.5) \
                    * (x_div_count - 1)

            if y_div_count == 1:
                _vl = 0
            else:
                _vl = ((int(view_count / y_div_count) / (y_div_count - 1)) - 0.5) \
                    * (y_div_count - 1)

            # create a copy from the current copy
            _n_view = View('%s_%d' % (self.name, view_count))

            # update parameters
            _n_view.h_size = _vh
            _n_view.v_size = _vv
            _n_view.shift = _vs
            _n_view.lift = _vl

            # add the new view to views list
            _views[view_count] = _n_view

        return _views

    def to_radiance(self):
        """Return full Radiance definition as a string."""
        # create base information of view
        view_options = ' '.join((
            self.vt, self.vp, self.vd, self.vu,
            self.vh, self.vv, self.vs, self.vl,
            self.vo, self.va
        ))

        return ' '.join(view_options.split())  # remove white spaces

    def to_dict(self):
        """Translate view to a dictionary."""
        return {
            'name': self.name,
            'position': self.position.value,
            'direction': self.direction.value,
            'up_vector': self.up_vector.value, 
            'h_size': self.h_size.value,
            'v_size': self.v_size.value, 
            'shift': self.shift.value,
            'lift': self.lift.value,
            'type': self.type.value, 
            'fore_clip': self.fore_clip.value,
            'aft_clip': self.aft_clip.value
        }

    def to_file(self, folder, file_name=None, mkdir=False):
        """Save view to a file.

        Args:
            folder: Target folder.
            file_name: Optional file name without extension (Default: self.name).
            mkdir: A boolean to indicate if the folder should be created in case it
                doesn't exist already (Default: False). 

        Returns:
            Full path to newly created file.
        """

        name = file_name or self.name + '.vf'
        # add rvu before the view itself
        content = 'rvu ' + self.to_radiance()
        return futil.write_to_file_by_name(folder, name, content, mkdir)

    def move(self, vector):
        """Move view."""
        position = pv.Point3D(*self.position)
        self.position = tuple(position.move(pv.Vector3D(*vector)))

    def rotate(self, angle, axis=None, position=None):
        """Rotate view around an axis.

        Args:
            angle: Rotation angle in radians.
            axis: Rotation axis as a Vector3D (Default: self.up_vector).
            position: Rotation position point as a Point3D (Default: self.position)
        """
        view_up_vector = pv.Vector3D(*self.up_vector)
        view_position = pv.Point3D(*self.position)
        view_direction = pv.Vector3D(*self.direction)
        view_plane = plane.Plane(n=view_up_vector, o=view_position, x=view_direction)
        axis = pv.Vector3D(*axis) or view_up_vector
        position = pv.Point3D(*position) or view_position
        
        rotated_plane = view_plane.rotate(axis, angle, position)

        self.position = rotated_plane.o
        self.direction = rotated_plane.x
        self.up_vector = rotated_plane.n

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        """View representation."""
        return self.to_radiance()