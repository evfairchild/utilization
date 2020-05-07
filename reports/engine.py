__author__ = "evfairchild"

from reports.airframe import Airframe
import pandas as pd
import numpy as np
from tqdm import tqdm
from colorama import Fore


class Engine(Airframe):
    def __init__(self, start_date, end_date):
        super(Engine, self).__init__(start_date, end_date)
        cols = self.get_fh_fc_history().columns
        self.esn_history = pd.DataFrame(columns=cols)

    def get_removals(self):
        """
        This method queries the removal records for the month input by the user.
        PN query: 1887M10G% for the CFM56-5B and 2489M10G% for the LEAP-1A engines
        :return: dataframe with ESN, AC and Date removed
        """
        query = "SELECT SN, PN, TRANSACTION_TYPE, AC, " \
                "(TRUNC(TRANSACTION_DATE) + " \
                    "( NVL( TRANSACTION_HOUR, 0) / 24 ) + " \
                    "( NVL( TRANSACTION_MINUTE, 0) / 1440 )) AS TRANS_DATE, " \
                "SCHEDULE_CATEGORY, POSITION, " \
                "ROUND ( HOURS_INSTALLED + ( MINUTES_INSTALLED / 60 ), 5 ) AS TSI, " \
                "CYCLES_INSTALLED AS CSI, REMOVAL_REASON " \
                "FROM odb.AC_PN_TRANSACTION_HISTORY " \
                "WHERE ( TRANSACTION_DATE >= to_date('{}', 'YYYY-MM-DD HH24:MI:SS')) " \
                "AND ( TRANSACTION_DATE <= to_date('{}', 'YYYY-MM-DD HH24:MI:SS')) " \
                "AND ( PN LIKE '1887M10G%' OR PN LIKE '2489M10G%' ) " \
                "ORDER BY AC, TRANSACTION_DATE".format(self.startDate, self.endDate)

        return pd.read_sql(query, self.trax)

    def _get_install_removal_pairs(self):
        """
        This method merges Install and Removal records from the odb.AC_PN_TRANSACTION_HISTORY table in TRAX so that
        hours and cycles by ESM can be tabulated.
        :return: dataframe containing install and removal pairs based on ESN and installed aircraft
        """
        query = "SELECT SN, TRANSACTION_TYPE, AC, " \
                "(TRUNC(TRANSACTION_DATE) + " \
                    "( NVL( TRANSACTION_HOUR, 0) / 24 ) + " \
                    "( NVL( TRANSACTION_MINUTE, 0) / 1440 )) AS TRANSACTION_DATE, " \
                "POSITION " \
                "FROM odb.AC_PN_TRANSACTION_HISTORY " \
                "WHERE ( PN LIKE '1887M10G%' OR PN LIKE '2489M10G%' ) " \
                "AND ( TRANSACTION_TYPE LIKE '{}' ) " \
                "ORDER BY TRANSACTION_DATE"

        self.installs = pd.read_sql(query.format('IN%'), self.trax)
        self.removals = pd.read_sql(query.format('REMOVE'), self.trax)

        self.installs.drop_duplicates(inplace=True)
        self.removals.drop_duplicates(inplace=True)

        # For some reason there are two original install records for N521VA engines, the merge cannot work 1-to-1
        # because of this.  For that reason it is forced to be removed.  There is also an erroneous ESN entry (397549)
        for i, install in self.installs.iterrows():
            if install['AC'] == 'N521VA' and str(install['TRANSACTION_DATE']) == '2006-04-04 00:00:00':
                self.installs.drop([i], inplace=True)
            elif install['SN'] == '397549':
                self.installs.drop([i], inplace=True)
            elif install['SN'] == '643151' and str(install['TRANSACTION_DATE']) == '2010-09-27 00:00:00':
                self.installs.drop([i], inplace=True)
            elif install['SN'] == '643152' and str(install['TRANSACTION_DATE']) == '2010-09-27 00:00:00':
                self.installs.drop([i], inplace=True)
            else:
                pass

        self.pairs = pd.merge_asof(self.installs.rename(columns={'TRANSACTION_DATE': 'INSTALL_DATE'}),
                                   self.removals.rename(columns={'TRANSACTION_DATE': 'REMOVAL_DATE'}),
                                   left_on='INSTALL_DATE',
                                   right_on='REMOVAL_DATE',
                                   by=['SN', 'AC'], direction='forward')

        self.column_names = {'SN': 'ESN', 'TRANSACTION_TYPE_x': 'INSTALL',
                             'TRANSACTION_TYPE_y': 'REMOVE', 'POSITION_x': 'POSITION'}
        self.pairs.rename(columns=self.column_names, inplace=True)
        self.pairs[['REMOVAL_DATE']] = self.pairs[['REMOVAL_DATE']].fillna(value=pd.Timestamp(self.endDate))

        return self.pairs.sort_values(by=['ESN', 'INSTALL_DATE'], ascending=(True, True), ignore_index=True)\
            .drop(['INSTALL', 'REMOVE', 'POSITION_y'], axis=1)

    def get_esn_history(self, df):
        """
        This method return a dataframe for a single aircraft over a specific datetime interval (start - end).
        :param df: dataframe with ESN, INSTALL_DATE, REMOVAL_DATE and AC
        :return: dataframe indexed by ac with columns YYYY-MM
        """
        query = "SELECT '{}' AS ESN, AC, (to_char(odb.AC_ACTUAL_FLIGHTS.FLIGHT_DATE, 'YYYY-MM')) AS BLAH, " \
                "SUM( ROUND( odb.AC_ACTUAL_FLIGHTS.FLIGHT_HOURS + " \
                "( odb.AC_ACTUAL_FLIGHTS.FLIGHT_MINUTES / 60 ), 5 ) ) AS FLIGHT_HOURS, " \
                "SUM ( odb.AC_ACTUAL_FLIGHTS.CYCLES ) AS FLIGHT_CYCLES " \
                "FROM odb.AC_ACTUAL_FLIGHTS " \
                "WHERE ( ( odb.AC_ACTUAL_FLIGHTS.FLIGHT_DATE + " \
                "( NVL( odb.AC_ACTUAL_FLIGHTS.TO_HOUR, 0) / 24 ) + " \
                "( NVL( odb.AC_ACTUAL_FLIGHTS.TO_MINUTE, 0) / 1440 )) >= to_date('{}', 'YYYY-MM-DD HH24:MI:SS')) " \
                "AND ( ( odb.AC_ACTUAL_FLIGHTS.FLIGHT_DATE + " \
                "( NVL( odb.AC_ACTUAL_FLIGHTS.TO_HOUR, 0) / 24 ) + " \
                "( NVL( odb.AC_ACTUAL_FLIGHTS.TO_MINUTE, 0) / 1440 )) <= to_date('{}', 'YYYY-MM-DD HH24:MI:SS')) " \
                "AND ( odb.AC_ACTUAL_FLIGHTS.AC = '{}' ) " \
                "GROUP BY to_char(odb.AC_ACTUAL_FLIGHTS.FLIGHT_DATE, 'YYYY-MM'), AC"

        query_out = ""

        for i, row in df.iterrows():
            esn = row['ESN']
            startdate = row['INSTALL_DATE']
            enddate = row['REMOVAL_DATE']
            ac = row['AC']
            query_tmp = query.format(esn, startdate, enddate, ac)

            if ac == 'N631VA' or ac == 'N634VA':    # Aircraft removed from Op Spec
                query_tmp = query_tmp.replace("AC_ACTUAL_FLIGHTS", "AC_ACTUAL_FLIGHTS_HD")

            if i == (len(df) - 1):
                query_out += query_tmp
                break
            else:
                query_out += query_tmp + " UNION "

        df = pd.read_sql(query_out, self.trax)

        # if df.empty:
        #     query_out = query_out.replace("AC_ACTUAL_FLIGHTS", "AC_ACTUAL_FLIGHTS_HD")
        #     df = pd.read_sql(query_out, self.trax)
        # else:
        #     pass

        df.rename(columns={'BLAH': 'YYYY-MM'}, inplace=True)

        return pd.pivot_table(df, index=['ESN'], columns=['YYYY-MM'], fill_value=0, aggfunc=np.sum, margins=True)

    def run(self):
        print("Collecting Engine Data...")
        pbar = tqdm(total=100)
        pbar.bar_format = "{l_bar}%s{bar}%s{r_bar}" % (Fore.GREEN, Fore.RESET)
        pairs = self._get_install_removal_pairs()
        pbar.update(10)
        esn_history = self.get_esn_history(pairs)
        pbar.update(75)
        df = self.filter_to_yyyy_mm(esn_history)
        df.columns = ['%s%s' % (a, ' | %s' % b if b else '') for a, b in df.columns]
        pbar.update(10)
        df = df.merge(self.installed_ac(), on='ESN', how='outer')
        pbar.update(5)

        return df.sort_values(by='INSTALLED_AC')

    def get_tsi_csi(self, startdate, enddate, ac):
        query = "SELECT SUM ( " \
            "ROUND( odb.AC_ACTUAL_FLIGHTS.FLIGHT_HOURS + (odb.AC_ACTUAL_FLIGHTS.FLIGHT_MINUTES / 60), 2)) AS TSI, " \
            "COUNT( odb.AC_ACTUAL_FLIGHTS.CYCLES ) AS CSI " \
            "FROM odb.AC_ACTUAL_FLIGHTS " \
            "WHERE ( ( odb.AC_ACTUAL_FLIGHTS.FLIGHT_DATE + " \
                "( NVL( odb.AC_ACTUAL_FLIGHTS.TO_HOUR, 0) / 24 ) + " \
                "( NVL( odb.AC_ACTUAL_FLIGHTS.TO_MINUTE, 0) / 1440 )) >= to_date('{}', 'YYYY-MM-DD HH24:MI:SS')) " \
            "AND ( ( odb.AC_ACTUAL_FLIGHTS.FLIGHT_DATE + " \
                "( NVL( odb.AC_ACTUAL_FLIGHTS.TO_HOUR, 0) / 24 ) + " \
                "( NVL( odb.AC_ACTUAL_FLIGHTS.TO_MINUTE, 0) / 1440 )) < to_date('{}', 'YYYY-MM-DD HH24:MI:SS')) " \
            "AND ( odb.AC_ACTUAL_FLIGHTS.AC = '{}' ) ".format(startdate, enddate, ac)

        df = pd.read_sql(query, self.trax)
        # print(pd.Series(df['TSI'][0], int(df['CSI'][0])))
        return df['TSI'][0], int(df['CSI'][0])

    def installed_ac(self):
        query = "SELECT SN, INSTALLED_AC " \
                "FROM odb.PN_INVENTORY_DETAIL WHERE PN LIKE '1887M10G%' OR PN LIKE '2489M10G%'"

        df = pd.read_sql(query, self.trax)
        df.rename(columns={'SN': 'ESN'}, inplace=True)
        df.set_index('ESN', inplace=True)

        return df


if __name__ == "__main__":
    start_date, end_date = '2020-04-01 00:00:00', '2020-04-30 23:59:59'
    e = Engine(start_date, end_date)
    df = e.run()
