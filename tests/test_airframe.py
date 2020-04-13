import unittest
from reports.airframe import Airframe

fleet_size = 71
start_date, end_date = '2020-03-01 00:00:00', '2020-03-31 23:59:59'
A = Airframe(start_date, end_date)


class TestAirframe(unittest.TestCase):
    def test_ac_count(self):
        self.assertEqual(len(A.tails), fleet_size)

    def test_tail_case(self):
        acs = ['n921va', 'n922va', 'n621va']
        self.assertCountEqual(list(A.get_fh_fc(acs).index), [ac.upper() for ac in acs])

    def test_get_fh_fc(self):
        self.longMessage = True
        self.assertEqual(len(A.get_fh_fc(A.tails)), fleet_size)
        self.assertEqual(len(A.get_fh_fc(A.tails, asof="2020-03-31")), fleet_size)
        self.assertEqual(len(A.get_fh_fc(A.tails, asof="2020-03-31 00:00:00")), fleet_size)

        self.assertRaises(LookupError, A.get_fh_fc, ['n631VA'])


if __name__ == '__main__':
    unittest.main()
