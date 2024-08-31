from time import time, strftime, localtime

stopwatch_initial_time = localtime()

while True:
    stopwatch_elapsed_time = localtime()

    print(localtime().tm_sec - stopwatch_initial_time.tm_sec)