from __future__ import print_function, division, absolute_import

import unittest


class TestLoadXDSMFromOpenMDAOGroup(unittest.TestCase):

    def test_load_openmdao_group(self):
        from pyxdsm.XDSM import XDSM
        from dymos.examples.min_time_climb.min_time_climb_ode import MinTimeClimbODE
        from dymos.examples.ssto.launch_vehicle_ode import LaunchVehicleODE

        xdsm = XDSM()

        var_map = {'gam_dot': r'\dot{\gamma}',
                   'h_dot': r'\dot{h}',
                   'v_dot': r'\dot{v}',
                   'r_dot': r'\dot{r}',
                   'm_dot': r'\dot{m}',
                   'f_lift': r'L',
                   'f_drag': r'D',
                   'thrust': r'T',
                   'alpha': r'\alpha',
                   'gam': '\gamma',
                   'rho': r'\rho',
                   'mach': 'Mach',
                   'max_thrust': 'thrust',
                   'Isp': 'I_{sp}'}

        sys_map = {'aero': 'aerodynamics',
                   'atmos': 'atmosphere',
                   'prop': 'propulsion',
                   'flight_dynamics': r'flight \, dynamics'}

        xdsm.from_openmdao_group(MinTimeClimbODE(num_nodes=10), var_map=var_map, sys_map=sys_map)


        xdsm.write('min_time_climb_ode')


if __name__ == '__main__':
    unittest.main()




