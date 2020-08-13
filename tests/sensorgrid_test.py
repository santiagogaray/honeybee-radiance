"""Test SensorGrid class."""
from honeybee_radiance.sensor import Sensor
from honeybee_radiance.sensorgrid import SensorGrid
import pytest


sensors = [Sensor((0, 0, 0), (0, 0, 1)), Sensor((0, 0, 10), (0, 0, 1))]


def test_creation():
    sg = SensorGrid('sg_1', sensors)
    assert sg.identifier == 'sg_1'
    assert len(sg) == 2
    assert sg[0] == sensors[0]
    assert sg[1] == sensors[1]


def test_updating_values():
    sg = SensorGrid('sg_1', sensors)
    # sensor is immutable - hence no assignment
    with pytest.raises(TypeError):
        sg.sensors[0] = Sensor((0, 0, 100), (0, 0, -10))


def test_invalid_input():
    with pytest.raises(ValueError):
        sg = SensorGrid('sg_1', ((0, 0, 0, 0, 0, 1),))


def test_from_planar_grid():
    positions = [[0, 0, 0], [0, 0, 5], [0, 0, 10]]
    plane_normal = [0, 0, 1]
    sg = SensorGrid.from_planar_grid('test_grid', positions, plane_normal)
    assert len(sg) == 3
    for sensor in sg:
        assert sensor.dir == (0, 0, 1)


def test_from_loc_dir():
    positions = [[0, 0, 0], [0, 0, 5], [0, 0, 10]]
    directions = [[0, 0, 1], [0, 0, -1], [0, 0, 10]]
    sg = SensorGrid.from_position_and_direction('sg', positions, directions)
    for count, sensor in enumerate(sg):
        list(sensor.pos) == positions[count]
        list(sensor.dir) == directions[count]


def test_from_file():
    sensor_grid = SensorGrid.from_file('./tests/assets/test_points.pts')
    assert sensor_grid.identifier == 'test_points'
    assert sensor_grid[0].pos == (0, 0, 0)
    assert sensor_grid[0].dir == (0, 0, 1)
    assert len(sensor_grid) == 3
    assert sensor_grid[1].to_radiance() == '0.2 0.3 0.4 0.5 0.6 0.7'
    assert sensor_grid[2].to_radiance() == '-10.0 -5.0 0.0 -50.0 -60.0 -70.0'


def test_to_radiance():
    sg = SensorGrid('sg', sensors)
    sg.to_radiance() == \
        """0.0 0.0 0.0 0.0 0.0 1.0\n0.0 0.0 10.0 0.0 0.0 1.0"""


def test_to_and_from_dict():
    sg = SensorGrid('sg', sensors)
    sg_dict = sg.to_dict()
    assert sg_dict == {
        'type': 'SensorGrid',
        'identifier': 'sg',
        'sensors': [
            {'pos': (0, 0, 0), 'dir': (0,  0, 1)},
            {'pos': (0, 0, 10), 'dir': (0,  0, 1)}
        ]
    }

    sensor_from = SensorGrid.from_dict(sg_dict)
    assert sensor_from == sg


def test_split_single_grid():
    """Test splitting a sensor grid."""
    sensor_grid = SensorGrid.from_file('./tests/assets/grid/sensor_grid_split.pts')
    folder = './tests/assets/temp'
    info = sensor_grid.to_files(folder, 1, 'single_grid')
    assert len(info) == 1
    assert info[0]['count'] == sensor_grid.count


def test_split_grid():
    """Test splitting a sensor grid."""
    sensor_grid = SensorGrid.from_file('./tests/assets/grid/sensor_grid_split.pts')
    folder = './tests/assets/temp'
    info = sensor_grid.to_files(folder, 6, 'test_sensor_grid')
    assert len(info) == 6
    for i in range(6 - 1):
        assert info[i]['count'] == 4

    assert info[-1]['count'] == 1
