__author__ = "evfairchild"

import pandas as pd
import numpy as np
import pyodbc
from datetime import datetime
from tqdm import tqdm
from colorama import Fore


class Airframe(object):
    def __init__(self, start_date, end_date):
        self.startDate = start_date
        self.endDate = end_date
        self.year = start_date[0:4]
        self.month = start_date[5:7]
        self.yyyymm = self.year + "-" + self.month
        self.trax = pyodbc.connect('DSN=Trax Reporting;pwd=WelcomeToTrax#1')
        self.tails = self.get_tails()
        self.now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_fh_fc_history(self):
        """
        This method returns a pivot table with the entire fleet history by YYY-MM.
        It requires TRAX access via ODBC.   Email evan.fairchild@alaskaair.com for help with access & setup.
        SUPER FAST and easy!

        :return: pivot table indexed by AC registration and grouped by YYY-MM.  Included aggregate row and column.
        """
        query = "SELECT odb.AC_ACTUAL_FLIGHTS.AC AS AC, " \
                "(to_char(odb.AC_ACTUAL_FLIGHTS.FLIGHT_DATE, 'YYYY-MM')) AS BLAH, " \
                "SUM( ROUND( odb.AC_ACTUAL_FLIGHTS.FLIGHT_HOURS + " \
                "( odb.AC_ACTUAL_FLIGHTS.FLIGHT_MINUTES / 60 ), 5 ) ) AS FLIGHT_HOURS, " \
                "SUM ( odb.AC_ACTUAL_FLIGHTS.CYCLES ) AS FLIGHT_CYCLES " \
                "FROM odb.AC_ACTUAL_FLIGHTS " \
                "WHERE ( ( odb.AC_ACTUAL_FLIGHTS.FLIGHT_DATE + " \
                    "( NVL( odb.AC_ACTUAL_FLIGHTS.TO_HOUR, 0) / 24 ) + " \
                    "( NVL( odb.AC_ACTUAL_FLIGHTS.TO_MINUTE, 0) / 1440 )) <= to_date('{}', 'YYYY-MM-DD HH24-MI-SS')) " \
                "GROUP BY to_char(odb.AC_ACTUAL_FLIGHTS.FLIGHT_DATE, 'YYYY-MM'), AC " \
                "ORDER BY AC".format(self.endDate)

        df = pd.read_sql(query, self.trax)
        df.rename(columns={'BLAH': 'YYYY-MM'}, inplace=True)
        return pd.pivot_table(df, index=['AC'], columns=['YYYY-MM'], fill_value=0, aggfunc=np.sum, margins=True)

    def filter_to_yyyy_mm(self, pivot):
        """
        Filter a pivot table to the requested Month (YYYY-MM)
        :param pivot: pivot table with columns YYYY-MM
        :return: dataframe with requested YYYY-MM and aggregate totals for flight hours and flight cycles
        """
        return pivot.filter([('FLIGHT_HOURS', self.yyyymm), ('FLIGHT_HOURS', 'All'),
                             ('FLIGHT_CYCLES', self.yyyymm), ('FLIGHT_CYCLES', 'All')])

    def get_tails(self):
        query = "SELECT odb.AC_MASTER.AC FROM odb.AC_MASTER " \
                # "UNION " \
                # "SELECT odb.AC_MASTER_HD.AC FROM odb.AC_MASTER_HD"
        return list(pd.read_sql(query, self.trax, index_col='AC').index)

    def get_fh_fc(self, acs, asof='now'):
        acs = ([acs] if type(acs) != list else acs)

        if asof == 'now':
            asof = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif len(asof) <= 10:
            asof += " 23:59:59"

        for ac in acs:
            if ac.upper() not in self.tails:
                raise LookupError("AC registration {} invalid.".format(ac.upper()))

        query = "SELECT AC, SUM( ROUND( odb.AC_ACTUAL_FLIGHTS.FLIGHT_HOURS + " \
                "( odb.AC_ACTUAL_FLIGHTS.FLIGHT_MINUTES / 60 ), 5 ) ) AS FLIGHT_HOURS, " \
                "SUM ( odb.AC_ACTUAL_FLIGHTS.CYCLES ) AS FLIGHT_CYCLES " \
                "FROM odb.AC_ACTUAL_FLIGHTS " \
                "WHERE AC IN ({}) " \
                "AND ( FLIGHT_DATE <= to_date('{}', 'YYYY-MM-DD HH24-MI-SS')) " \
                "GROUP BY AC".format(','.join("'%s'" % ac.upper() for ac in acs), asof)

        # query_hd = query.replace('AC_ACTUAL_FLIGHTS', 'AC_ACTUAL_FLIGHTS_HD')
        #
        # query += " UNION " + query_hd

        df = pd.read_sql(query, self.trax, index_col='AC')

        return df

    def get_fh(self, ac, asof='now'):
        return self.get_fh_fc(ac, asof=asof)['FLIGHT_HOURS']

    def get_fc(self, ac, asof='now'):
        return self.get_fh_fc(ac, asof=asof)['FLIGHT_CYCLES']

    def run(self):
        print("Collecting Airframe Data...")
        pbar = tqdm(total=100)
        pbar.bar_format = "{l_bar}%s{bar}%s{r_bar}" % (Fore.GREEN, Fore.RESET)

        pbar.update(33)
        df = self.get_fh_fc_history()
        pbar.update(33)
        df = self.filter_to_yyyy_mm(df)
        pbar.update(34)
        pbar.close()
        return df
