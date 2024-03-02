import RPi.GPIO as GPIO
import time

motorPin = 17
buttonPin = 18

GPIO.setmode(GPIO.BCM)
GPIO.setup(motorPin, GPIO.OUT)
GPIO.setup(buttonPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

motor_state = False  

def motor():
    global motor_state
    motor_state = not motor_state  
    GPIO.output(motorPin, GPIO.HIGH if motor_state else GPIO.LOW)  

try:
    while True:
        if GPIO.input(buttonPin) == 0:
            motor()
            while GPIO.input(buttonPin) == 0:
                time.sleep(0.1)
except KeyboardInterrupt:
    GPIO.cleanup()
