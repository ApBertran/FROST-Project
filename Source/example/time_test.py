from time import time, strftime, localtime

stopwatch_initial_time = localtime()

while True:
    elapsed_time = (localtime().tm_hour - stopwatch_initial_time.tm_hour) * 3600 + (localtime().tm_min - stopwatch_initial_time.tm_min) * 60 + (localtime().tm_sec - stopwatch_initial_time.tm_sec)
    
    # Calculate hours
    hours = str(elapsed_time // 3600)

    # Calculate minutes
    minutes = str((elapsed_time - int(hours) * 3600) // 60)
    if int(minutes) < 10:
        minutes = '0' + minutes
    
    # Calculate seconds
    seconds = str(elapsed_time - (int(hours) * 3600) - (int(minutes) * 60))
    if int(seconds) < 10:
        seconds = '0' + seconds
    
    stopwatch_output = hours + ':' + minutes + ":" + seconds

    print(stopwatch_output)