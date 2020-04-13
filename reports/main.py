__author__ = "evfairchild"

import os
from customGUI import Calendar2
from pandas import pd
from reports.airframe import Airframe
from reports.engine import Engine


def select_dates():
    cal_result = Calendar2().run()
    start, end = [i.strftime("%Y-%m-%d") for i in cal_result]
    start += ' 00:00:00'
    end += ' 23:59:59'
    return start, end


if __name__ == "__main__":
    # start, end = select_dates()
    start_date, end_date = '2020-03-01 00:00:00', '2020-03-31 23:59:59'
    airframe = Airframe(start_date, end_date).run()
    engines = Engine(start_date, end_date).run_apply()
    removals = Engine(start_date, end_date).get_removals()

    file = "utilization_{}.xlsx".format(Airframe(start_date, end_date).yyyymm)

    with pd.ExcelWriter(file) as writer:
        airframe.to_excel(writer, sheet_name="airframe")
        engines.to_excel(writer, sheet_name="engines")
        removals.to_excel(writer, sheet_name="removals")
    file = os.path.join(os.getcwd(), file)

    os.system("start EXCEL.EXE {}".format(file))
