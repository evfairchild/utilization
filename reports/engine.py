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

    def get_install_time_by_yyyy_mm(self, startdate, enddate, ac):
        """
        This method return a dataframe for a single aircraft over a specific datetime interval (start - end).
        :param startdate: Install date of the ESN being queried from the run() method.  ex. 2020-01-01 00:00:00
        :param enddate: Removal date of the ESN being queried from the run() method.  ex. 2020-01-31 23:59:95
        :param ac: aircraft registration ex. NXXXVA
        :return: dataframe indexed by ac with columns YYYY-MM
        """
        query = "SELECT (to_char(odb.AC_ACTUAL_FLIGHTS.FLIGHT_DATE, 'YYYY-MM')) AS BLAH, " \
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
                "GROUP BY to_char(odb.AC_ACTUAL_FLIGHTS.FLIGHT_DATE, 'YYYY-MM') " \
                "ORDER BY BLAH".format(startdate, enddate, ac)

        df = pd.read_sql(query, self.trax)
        if df.empty:
            query = query.replace("AC_ACTUAL_FLIGHTS", "AC_ACTUAL_FLIGHTS_HD")
            df = pd.read_sql(query, self.trax)
        else:
            pass

        df.rename(columns={'BLAH': 'YYYY-MM'}, inplace=True)
        self.esn_history.update(df)
        return df

    def run(self):
        print("Collecting Engine Data...")
        pairs = self._get_install_removal_pairs()

        return self._build_dataframe(pairs)

    def _build_dataframe(self, pairs):
        """
        Needs revision.  This method calls on 'get_install_time_by_yyyy_mm()' for each install-removal pair and merges
        unique records based on ESN. This is time-consuming (~50s) and should be written as an array function (df.apply)
        :return: dataframe with flight hours and cycles for each ESN in the fleet's history, filtered to YYYY-MM with totals
        """
        pbar = tqdm(total=len(pairs))
        pbar.bar_format = "{l_bar}%s{bar}%s{r_bar}" % (Fore.GREEN, Fore.RESET)

        df_result = pd.DataFrame(columns=['ESN', 'INSTALLED_AC', 'YYYY-MM', 'FLIGHT_HOURS', 'FLIGHT_CYCLES'])

        for i, esn in pairs.iterrows():
            df_tmp = self.get_install_time_by_yyyy_mm(esn['INSTALL_DATE'], esn['REMOVAL_DATE'], esn['AC'])
            df_tmp['ESN'] = esn['ESN']

            if str(esn['REMOVAL_DATE']) == self.endDate:
                df_tmp['INSTALLED_AC'] = esn['AC']
            else:
                df_tmp['INSTALLED_AC'] = 'SPARE'

            df_result = df_result.append(df_tmp, ignore_index=True)
            pbar.update(1)

        pbar.close()

        piv = self.filter_to_yyyy_mm(
            pd.pivot_table(df_result, index=['ESN'], columns=['YYYY-MM'], fill_value=0, aggfunc=np.sum, margins=True))
        installed_ac = df_result.loc[df_result['YYYY-MM'] == self.yyyymm]
        installed_ac = installed_ac[['ESN', 'INSTALLED_AC']]
        installed_ac.set_index('ESN', inplace=True)

        df_out = piv.merge(installed_ac, how='outer', left_index=True, right_index=True)

        return df_out.sort_values(by='INSTALLED_AC')

    def run_apply(self):
        """
        Under development.  Uses array formula (pd.apply) instead of for loop for each ESN.
        :return:
        """
        esns = self._get_install_removal_pairs()

        self.esn_history = pd.concat([esns, self.esn_history], axis=1).fillna(0)
        # df2[['TSI', 'CSI']] = df2.apply(
        #     lambda row: pd.Series(e.get_tsi_csi(str(row['INSTALL_DATE']), str(row['REMOVAL_DATE']), row['AC'])), axis=1)

        self.esn_history.apply(lambda row: pd.Series(self.get_install_time_by_yyyy_mm(row[2], row[4], row[1])), axis=1)

        return self.esn_history

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
