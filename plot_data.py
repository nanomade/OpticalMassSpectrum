import numpy as np
import matplotlib
import matplotlib.pyplot as plt


with open('data.npy', 'rb') as f:
    data = np.load(f)

wavelengths = data[0]
intensities = data[1]

fig = plt.figure()
axis = fig.add_subplot(1, 1, 1)
(graph,) = axis.plot(wavelengths, intensities, '-')
plt.show()
