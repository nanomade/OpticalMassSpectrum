import time

import usb
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, TextBox

import seabreeze
from seabreeze.spectrometers import Spectrometer

seabreeze.use('pyseabreeze')
# seabreeze.use('cseabreeze')


class Spectrometer:
    def __init__(self):
        self.spec = seabreeze.spectrometers.Spectrometer.from_first_available()
        # print(self.spec.features)
        self.integration_time = 200  # ms
        self.spec.integration_time_micros(self.integration_time * 1000)
        self.wavelengths = self.spec.wavelengths()
        self.dark_spectrum = self.acquire_dark_spectrum(int_time=60000, plot=False)

    def plot_single_spectum(self, intensities):
        fig = plt.figure()
        axis = fig.add_subplot(1, 1, 1)
        (graph,) = axis.plot(self.wavelengths, intensities, '-')
        plt.show()

    def _get_single_spectrum(self):
        error = 0
        while error > -1:
            try:
                intensities = self.spec.intensities()
                error = -1
            except usb.core.USBError:
                error += 1
                if error > 5:
                    print('Read error')
        return intensities

    def _acquire_fresh_dark_spectrum(self, int_time):
        dark_spectrum = np.zeros(len(self.wavelengths))
        iterations = int(int_time / (self.integration_time))
        print(iterations)
        for i in range(1, iterations + 1):
            if i % 5 == 0:
                print('{} / {}'.format(i, iterations))
            intensities = self._get_single_spectrum()
            dark_spectrum += intensities
        dark_spectrum = dark_spectrum / iterations
        return dark_spectrum

    def acquire_dark_spectrum(self, int_time, force_reread=False, plot=False):
        reread = force_reread
        if not reread:
            try:
                with open('dark_spectrum.npy', 'rb') as f:
                    dark_spectrum = np.load(f)
            except FileNotFoundError:
                reread = True
        if reread:
            dark_spectrum = self._acquire_fresh_dark_spectrum(int_time)
            with open('dark_spectrum.npy', 'wb') as f:
                np.save(f, dark_spectrum)
        if plot:
            self.plot_single_spectum(dark_spectrum)
        return dark_spectrum

    def get_spectrum(self, int_time=200):
        spectrum = np.zeros(len(self.wavelengths))
        iterations = int(int_time / (self.integration_time))
        print()
        print('Iterations is: {}'.format(iterations))
        for i in range(iterations):
            intensities = self._get_single_spectrum()
            spectrum += intensities
            print(
                i,
                spectrum[100],
                spectrum[200],
                spectrum[300],
                spectrum[400],
                spectrum[500],
            )
        spectrum = spectrum / iterations
        spectrum = spectrum - self.dark_spectrum
        return spectrum


class SpectrumPlotter:
    def __init__(self):
        self.spectrometer = Spectrometer()
        self.intensities = self.spectrometer.get_spectrum()
        self.integration_time = 1
        self.running = True
        self.paused = False
        self.ylim = [-30, 1000]

    def quit(self, event):
        self.running = False

    def auto_scale(self, event):
        y_max = max(self.intensities)
        print('Set autoscale: {}'.format(y_max))
        self.ylim[1] = y_max * 1.2

    def acquire(self, event):
        print('Acqure spectrum for {}s'.format(self.integration_time))
        self.paused = True
        time.sleep(0.2)

        intensities = self.spectrometer.get_spectrum(self.integration_time * 1000)
        print('Done')

    def save_data(self, event):
        xy_data = np.vstack(
            (
                self.spectrometer.wavelengths,
                self.intensities,
            )
        )
        with open('data.npy', 'wb') as f:
            np.save(f, xy_data)

    def logscale(self, event):
        if self.ylim[0] == 0:
            # Scale is lin
            self.ylim = [1, self.ylim[1]]
            self.axis.set_yscale('log')
        else:
            # Scale is log
            self.ylim = [0, self.ylim[1]]
            self.axis.set_yscale('linear')

    def set_integration_time(self, value):
        try:
            self.integration_time = float(value)
        except ValueError:
            print('Cannot read value!!!!!')
            self.integration_time = 0.1

    def restart(self, event):
        self.paused = False

    def _create_axis(self):
        plt.ion()

        self.fig = plt.figure()
        self.axis = self.fig.add_subplot(1, 1, 1)
        (self.graph,) = self.axis.plot(
            self.spectrometer.wavelengths, self.intensities, '-'
        )

    def main(self):
        self._create_axis()

        # Make a small helper function to create and store the buttons
        # self.buttons = {}
        b_quit_ax = plt.axes([0.1, 0.9, 0.05, 0.05])
        b_quit = Button(b_quit_ax, 'Quit')
        b_quit.on_clicked(self.quit)

        b_autoscale_ax = plt.axes([0.2, 0.9, 0.05, 0.05])
        b_autoscale = Button(b_autoscale_ax, 'Autoscale')
        b_autoscale.on_clicked(self.auto_scale)

        b_logscale_ax = plt.axes([0.3, 0.9, 0.05, 0.05])
        b_logscale = Button(b_logscale_ax, 'Log')
        b_logscale.on_clicked(self.logscale)

        b_acquire_ax = plt.axes([0.4, 0.9, 0.05, 0.05])
        b_acquire = Button(b_acquire_ax, 'Acquire')
        b_acquire.on_clicked(self.acquire)

        b_savedata_ax = plt.axes([0.5, 0.9, 0.05, 0.05])
        b_savedata = Button(b_savedata_ax, 'Save data')
        b_savedata.on_clicked(self.save_data)

        b_restart_ax = plt.axes([0.6, 0.9, 0.05, 0.05])
        b_restart = Button(b_restart_ax, 'Restart')
        b_restart.on_clicked(self.restart)

        b_int_time_ax = plt.axes([0.9, 0.9, 0.05, 0.05])
        text_box = TextBox(b_int_time_ax, 'Integration time', initial='1')
        text_box.on_submit(self.set_integration_time)

        while self.running:
            if not self.paused:
                self.intensities = self.spectrometer.get_spectrum()
            else:
                time.sleep(0.1)
            self.graph.set_ydata(self.intensities)
            self.axis.set_ylim(self.ylim[0], self.ylim[1])
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()


if __name__ == '__main__':
    sp = SpectrumPlotter()
    sp.main()
