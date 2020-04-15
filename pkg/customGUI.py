from tkinter import Tk, LEFT, RIGHT, BOTH, Message, Entry
from tkinter.ttk import Frame, Button, Style
from ttkcalendar import Calendar


class UserPrompts(object):
    def __init__(self):
        self.root = Tk()
        self.entrybox = None
        self.unit = None
        self.result = []

    def units(self):
        mainframe = Frame(self.root)
        mainframe.master.title("Units")
        mainframe.style = Style()
        mainframe.style.theme_use("default")

        message = 'How would you like to measure the EC?'

        lbl1 = Message(mainframe, text=message)
        lbl1.pack(expand=True, fill='x')
        lbl1.bind("<Configure>", lambda e: lbl1.configure(width=e.width-10))

        mainframe.pack(fill=BOTH, expand=True)

        button1 = Button(mainframe, text="Date", command=lambda: self.save_value("Date"))
        button1.pack(side=LEFT, padx=5, pady=5)
        button2 = Button(mainframe, text="Flight Hours", command=lambda: self.save_value("FH"))
        button2.pack(side=RIGHT, padx=5, pady=5)
        button3 = Button(mainframe, text="Flight Cycles", command=lambda: self.save_value("FC"))
        button3.pack(side=RIGHT, padx=5, pady=5)

        self.root.mainloop()

    def value_input(self, unit):
        self.unit = unit
        mainframe = Frame(self.root)
        mainframe.master.title("Units")
        mainframe.style = Style()
        mainframe.style.theme_use("default")

        message = 'What {} range? ex: 10, 100, 750, etc'.format(unit)
        lbl1 = Message(mainframe, text=message)
        lbl1.pack(expand=True, fill='x')
        lbl1.bind("<Configure>", lambda e: lbl1.configure(width=e.width))

        mainframe.pack(fill=BOTH, expand=True)

        self.entrybox = Entry(mainframe)
        self.entrybox.pack()
        button = Button(mainframe, text='OK', command=lambda: self.quit_gui())
        button.pack()

        self.root.mainloop()

    def save_value(self, option):
        self.result.append(option)
        self.root.quit()

    def quit_gui(self):
        self.result.append(self.entrybox.get())
        self.root.destroy()

    def run(self):
        self.units()
        self.value_input(self.result[0])
        return self.result


class Calendar2(Calendar):
    def __init__(self, master=None, call_on_select=None, **kw):
        Calendar.__init__(self, master, **kw)
        self.set_selection_callback(call_on_select)
        self.result = []
        self.total_selections = 0

    def set_selection_callback(self, a_fun):
        self.call_on_select = a_fun

    def print_date(self):
        if self.total_selections == 0:
            print("Start Date:", str(self.selection)[0:11])
        elif self.total_selections == 1:
            print("End Date:", str(self.selection)[0:11])
            print("Please close this box to continue.")

    def _pressed(self, evt):
        Calendar._pressed(self, evt)

        self.result.append(self.selection)
        if self.call_on_select:
            self.call_on_select(self.selection)

        self.print_date()

        self.total_selections += 1
        if self.total_selections == 2:
            self.destroy()

    def run(self):
        self.pack(expand=1, fill='both')
        self.mainloop()
        return self.result


def test():
    cal_result = Calendar2().run()
    print(cal_result)
    gui = UserPrompts().run()
    print(gui)


if __name__ == '__main__':
    test()

