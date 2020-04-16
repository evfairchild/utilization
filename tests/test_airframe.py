import sys
import unittest
import logging
from reports.airframe import Airframe

fleet_size = 71
start_date, end_date = '2020-03-01 00:00:00', '2020-03-31 23:59:59'
A = Airframe(start_date, end_date)
logger = logging.getLogger("Airframe unit tests starting...")


class TestAirframe(unittest.TestCase):
    def test_ac_count(self):
        logger.info("Testing current Aircraft Fleet size.")
        self.assertEqual(len(A.tails), fleet_size)

    def test_tail_case(self):
        logger.info("Testing aircraft registration input (case sensitivity).")
        acs = ['n921va', 'n922va', 'n621va']
        self.assertCountEqual(list(A.get_fh_fc(acs).index), [ac.upper() for ac in acs])

    def test_get_fh_fc(self):
        logger.info("Testing Flight Hour and Flight cycle totals.")
        self.longMessage = True
        self.assertEqual(len(A.get_fh_fc(A.tails)), fleet_size)
        self.assertEqual(A.get_fh_fc(['N281VA', 'N282VA']).shape, (2, 2))
        self.assertEqual(len(A.get_fh_fc(A.tails, asof="2020-03-31")), fleet_size)
        self.assertEqual(len(A.get_fh_fc(A.tails, asof="2020-03-31 00:00:00")), fleet_size)
        self.assertRaises(LookupError, A.get_fh_fc, ['n631VA'])

    def test_get_fh(self):
        logger.info("Testing Flight Hours.")
        self.assertEqual(len(A.get_fh(A.tails)), fleet_size)
        self.assertEqual(A.get_fh(['N281VA', 'N282VA']).shape, (2,))
        self.assertEqual(len(A.get_fh(A.tails, asof="2020-03-31")), fleet_size)
        self.assertEqual(len(A.get_fh(A.tails, asof="2020-03-31 00:00:00")), fleet_size)

    def test_get_fc(self):
        logger.info("Testing Flight Cycles.")
        self.assertEqual(len(A.get_fc(A.tails)), fleet_size)
        self.assertEqual(A.get_fc(['N281VA', 'N282VA']).shape, (2,))
        self.assertEqual(len(A.get_fc(A.tails, asof="2020-03-31")), fleet_size)
        self.assertEqual(len(A.get_fc(A.tails, asof="2020-03-31 00:00:00")), fleet_size)

    def test_get_fh_fc_history(self):
        logger.info("Testing total fleet flight hour and flight cycle history.")
        df = A.get_fh_fc_history()
        self.assertEqual(df.columns.min()[1], '2005-12')
        self.assertEqual(list(df.columns)[-2][1], A.yyyymm)
        self.assertEqual(df.shape[0], fleet_size + 1)

    def test_set_fleet(self):
        logger.info("Testing subfleet and tail number attributes.")
        a = Airframe()
        ac_dict = {'A319': ['N521VA', 'N522VA', 'N523VA', 'N524VA', 'N525VA', 'N526VA', 'N527VA', 'N528VA', 'N529VA', 'N530VA'],
                   'A320': ['N281VA', 'N282VA', 'N283VA', 'N284VA', 'N285VA', 'N286VA', 'N361VA', 'N362VA', 'N363VA', 'N364VA', 'N365VA', 'N621VA', 'N622VA', 'N623VA', 'N624VA', 'N625VA', 'N626VA', 'N627VA', 'N628VA', 'N629VA', 'N630VA', 'N632VA', 'N633VA', 'N635VA', 'N636VA', 'N637VA', 'N638VA', 'N639VA', 'N640VA', 'N641VA', 'N642VA', 'N835VA', 'N836VA', 'N837VA', 'N838VA', 'N839VA', 'N840VA', 'N841VA', 'N842VA', 'N843VA', 'N844VA', 'N845VA', 'N846VA', 'N847VA', 'N848VA', 'N849VA', 'N851VA', 'N852VA', 'N853VA', 'N854VA', 'N855VA'],
                   'A321': ['N921VA', 'N922VA', 'N923VA', 'N924VA', 'N925VA', 'N926VA', 'N927VA', 'N928VA', 'N929VA', 'N930VA']}
        ac_dict['all'] = ac_dict['A319'] + ac_dict['A320'] + ac_dict['A321']

        for subfleet in ['A319', 'A320', 'A321', 'all']:
            a.set_fleet(subfleet)
            self.assertCountEqual(a.tails, ac_dict[subfleet])


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr)
    logging.getLogger().setLevel(logging.INFO)
    unittest.main()
