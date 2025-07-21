import numpy as np
import talib

close = np.random.random(100)

output = talib.SMA(close)
# При корректной работе библиотеки, вывод должен быть в виде не нулевого массива
print(output)