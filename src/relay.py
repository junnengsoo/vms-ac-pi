import logging

import RPi.GPIO as GPIO
from time import sleep
from datetime import datetime
import multitasking
import json
import os
import threading
from lock import config_lock

from eventActionTriggerConstants import GEN_OUT_1
from executor import thread_pool_executor

path = os.path.dirname(os.path.abspath(__file__))


# Create a logger
logger = logging.getLogger(__name__)

# Set the level of logging. It can be DEBUG, INFO, WARNING, ERROR, CRITICAL
logger.setLevel(logging.DEBUG)

# Create a file handler for outputting log messages to a file
file_handler = logging.FileHandler('/home/etlas/Relay.log')

# Create a formatter and add it to the handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(file_handler)

# everytime relay triggers, mag_status_open = True
# if mag_contact opened but mag_status_open = False, TRIGGER ALARM

config = None
GPIOpins = None

Relay_1 = None
Relay_2 = None

E1_opened = False
E2_opened = False
E1_perm_opened = False
E2_perm_opened = False
E1_previous = None
E2_previous = None

GEN_1_OPEN, GEN_2_OPEN, GEN_3_OPEN = False, False, False


def update_config():
    global config, GPIOpins, Relay_1, Relay_2, GEN_OUT_1, GEN_OUT_2, GEN_OUT_3
    with config_lock:
        f = open(path+'/json/config.json')
        config = json.load(f)
        f.close()

    GPIOpins = config["GPIOpins"]
    Relay_1 = int(GPIOpins["Relay_1"])
    Relay_2 = int(GPIOpins["Relay_2"])
    GEN_OUT_1 = int(GPIOpins["Gen_Out_1"])
    GEN_OUT_2 = int(GPIOpins["Gen_Out_2"])
    GEN_OUT_3 = int(GPIOpins["Gen_Out_3"])


update_config()
# *** GPIO Setp/Cleanup ***


def setGpioMode():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    return


def cleanupGpio():
    GPIO.cleanup()
    return

# *** Relay pin setup/set high/low ***


def setupRelayPin(relayPin):
    GPIO.setup(relayPin, GPIO.OUT)
    GPIO.output(relayPin, GPIO.LOW)
    return


def setRelayPinHigh(relayPin):
    GPIO.output(relayPin, GPIO.HIGH)
    return


def setRelayPinLow(relayPin):
    GPIO.output(relayPin, GPIO.LOW)
    return

# *** Relay activate/deactivate/toggle ***


def activateRelay(relayPin, activateLevel):
    print("activateRelay", activateLevel, relayPin)
    if activateLevel == 'High':
        setRelayPinHigh(relayPin)
    else:
        setRelayPinLow(relayPin)
    return


def deActivateRelay(relayPin, activateLevel):
    if activateLevel == 'High':
        setRelayPinLow(relayPin)
    else:
        setRelayPinHigh(relayPin)
    return


def toggleRelay1(relayPin, activateLevel, activateMilliSeconds, deActivateMilliSeconds, toggleCount):
    
    global E1_opened
    logger.info("Trigger toggleRelay 1, E1_opened: %s", E1_opened)
    if not E1_opened:
        # print timing before gpio set up
        setGpioMode()
        setupRelayPin(relayPin)

        for i in range(toggleCount):
            logger.info("toggleRelay1 Activated")
            activateRelay(relayPin, activateLevel)

            E1_opened = True
            sleep(activateMilliSeconds / 1000)
            # print(E1_perm_opened)
        if E1_perm_opened:
            pass
        else:
            logger.info("toggleRelay1 Deactivated")
            E1_opened = False
            deActivateRelay(relayPin, activateLevel)
            sleep(deActivateMilliSeconds / 1000)

    return


def toggleRelay2(relayPin, activateLevel, activateMilliSeconds, deActivateMilliSeconds, toggleCount):
    global E2_opened
    logger.info("Trigger toggleRelay 2, E2_opened: %s", E2_opened)
    if not E2_opened:
        setGpioMode()
        setupRelayPin(relayPin)
        for i in range(toggleCount):
            activateRelay(relayPin, activateLevel)

            E2_opened = True
            sleep(activateMilliSeconds / 1000)
            # print(E1_perm_opened)
        if E2_perm_opened:
            pass
        else:
            E2_opened = False
            deActivateRelay(relayPin, activateLevel)
            sleep(deActivateMilliSeconds / 1000)

    return

# Events Management: Output actions timer for GENOUT_1/2/3


def toggleRelayGen(relayPin, activateLevel, activateMilliSeconds, GenNo):
    global GEN_1_OPEN, GEN_2_OPEN, GEN_3_OPEN, E1_opened, E2_opened
    activateRelay(relayPin, activateLevel)
    if (GenNo == 1):
        GEN_1_OPEN = True
    elif (GenNo == 2):
        GEN_2_OPEN = True
    elif (GenNo == 3):
        GEN_3_OPEN = True
    sleep(activateMilliSeconds)
    deActivateRelay(relayPin, activateLevel)
    if (GenNo == 1):
        GEN_1_OPEN = False
    elif (GenNo == 2):
        GEN_2_OPEN = False
    elif (GenNo == 3):
        GEN_3_OPEN = False
    while (GEN_1_OPEN or GEN_2_OPEN or GEN_3_OPEN or E1_opened or E2_opened):
        sleep(1)
    return
# *** Tests ***

# *** Toggle Relay ***


# # insert a parameter to determine whether to use GEN_OUT_1/2/3
# # third_party_option -> null, GEN_OUT_1/2/3
# def trigger_relay_one(third_party_options):

#     if third_party_options:
#         setGpioMode()
#         setupRelayPin(third_party_options)

#         try:
#             toggleRelay(relayPin = third_party_options, activateLevel = 'High', \
#                     activateMilliSeconds = 5000, deActivateMilliSeconds = 1000, \
#                     toggleCount = 1)
#             cleanupGpio()
#         except RuntimeError:
#             print("Entrance is still opened 'third-party-options'.")

#         return


#     setGpioMode()
#     setupRelayPin(Relay_1)

#     print(" EM 1 unlocked at " + str(datetime.now()))
#     try:
#         toggleRelay(relayPin = Relay_1, activateLevel = 'High', \
#                 activateMilliSeconds = 5000, deActivateMilliSeconds = 1000, \
#                 toggleCount = 1)
#         cleanupGpio()
#     except RuntimeError:
#         print("Entrance is still opened")

#     return


def trigger_relay_one(thirdPartyOption=None):
    outputPin = Relay_1

    if thirdPartyOption == "GEN_OUT_1":
        outputPin = GEN_OUT_1
        # print(thirdPartyOption,outputPin)

    if thirdPartyOption == "GEN_OUT_2":
        outputPin = GEN_OUT_2
        # print(thirdPartyOption,outputPin)

    if thirdPartyOption == "GEN_OUT_3":
        outputPin = GEN_OUT_3
        # print(thirdPartyOption,outputPin)

    print(" EM 1 unlocked at " + str(datetime.now()))
    try:
        setGpioMode()
        setupRelayPin(outputPin)
        print("opening")
        logger.info("Before toggleRelay1")
        # toggleRelay1(outputPin, 'High', 5000, 1000, 1)
        thread_pool_executor.submit(toggleRelay1, outputPin, 'High', 5000, 1000, 1)

        # cleanupGpio()
    except RuntimeError:
        print("Entrance is still opened")
    # print("test")
    return


def trigger_relay_two(thirdPartyOption=None):

    outputPin = Relay_2

    if thirdPartyOption == "GEN_OUT_1":
        outputPin = GEN_OUT_1

    if thirdPartyOption == "GEN_OUT_2":
        outputPin = GEN_OUT_2
    if thirdPartyOption == "GEN_OUT_3":
        outputPin = GEN_OUT_3

    # print('  EM 2 unlocked')
    try:
        setGpioMode()
        setupRelayPin(outputPin)
        toggleRelay2(relayPin=outputPin, activateLevel='High',
                     activateMilliSeconds=5000, deActivateMilliSeconds=1000,
                     toggleCount=1)
        cleanupGpio()
    except RuntimeError:
        print("Entrance is still opened")
    return

def lock_unlock_entrance_one(thirdPartyOption=None, unlock=False):
    outputPin = Relay_1
    if thirdPartyOption == "GEN_OUT_1":
        outputPin = GEN_OUT_1

    if thirdPartyOption == "GEN_OUT_2":
        outputPin = GEN_OUT_2

    if thirdPartyOption == "GEN_OUT_3":
        outputPin = GEN_OUT_3

    global E1_perm_opened
    global E1_previous

    if (E1_previous != None and E1_previous != outputPin):
        deActivateRelay(E1_previous, 'High')
        E1_previous = None

    if unlock:
        try:
            E1_perm_opened = True
            E1_previous = outputPin
            setGpioMode()
            setupRelayPin(outputPin)
            activateRelay(outputPin, 'High')
        except RuntimeError:
            print("Entrance is still opened")
    else:
        try:
            E1_perm_opened = False
            E1_previous = None
            if (not E1_opened):
                # print("trying to lock")
                setGpioMode()
                setupRelayPin(outputPin)
                deActivateRelay(outputPin, 'High')
        except RuntimeError:
            print("Entrance is still closed")
    # print("test")
    return

def lock_unlock_entrance_two(thirdPartyOption=None, unlock=False):

    outputPin = Relay_2

    if thirdPartyOption == "GEN_OUT_1":
        outputPin = GEN_OUT_1
        # print(thirdPartyOption,outputPin)

    if thirdPartyOption == "GEN_OUT_2":
        outputPin = GEN_OUT_2
        # print(thirdPartyOption,outputPin)

    if thirdPartyOption == "GEN_OUT_3":
        outputPin = GEN_OUT_3
        # print(thirdPartyOption,outputPin)

    global E2_perm_opened
    global E2_previous

    if (E2_previous != None and E2_previous != outputPin):
        deActivateRelay(E2_previous, 'High')
        E2_previous = None

    if unlock:
        try:
            E2_perm_opened = True
            E2_previous = outputPin
            setGpioMode()
            setupRelayPin(outputPin)
            activateRelay(outputPin, 'High')
        except RuntimeError:
            print("Entrance is still opened")
    else:
        try:
            E2_perm_opened = False
            E2_previous = None
            if (not E2_opened):
                # print("trying to lock")
                setGpioMode()
                setupRelayPin(outputPin)
                deActivateRelay(outputPin, 'High')
        except RuntimeError:
            print("Entrance is still closed")
    # print("test")
    return


@multitasking.task
def open_GEN_OUT(GEN_OUT_PIN=None, timer=1000, GenNo=1):
    # print("open_GEN_OUT activated")
    # doesnt get run on second scan

    outputPin = None

    if GEN_OUT_PIN == "GEN_OUT_1":
        outputPin = GEN_OUT_1
        # print(GEN_OUT_PIN,outputPin)

    if GEN_OUT_PIN == "GEN_OUT_2":
        outputPin = GEN_OUT_2
        # print(GEN_OUT_PIN,outputPin)

    if GEN_OUT_PIN == "GEN_OUT_3":
        outputPin = GEN_OUT_3
        # print(GEN_OUT_PIN,outputPin)

    setGpioMode()
    setupRelayPin(outputPin)

    # print(f" {GEN_OUT_PIN}  unlocked")
    try:
        toggleRelayGen(relayPin=outputPin, activateLevel='High',
                       activateMilliSeconds=timer, GenNo=GenNo
                       )
        print(f"finish open_GEN_OUT {outputPin}")
        cleanupGpio()
    except RuntimeError:
        print(f" {GEN_OUT_PIN} still opened")
    return



@multitasking.task
def unlock_entrance_one():

    setGpioMode()
    setupRelayPin(Relay_1)

    print(" EM 1 unlocked at " + str(datetime.now()))
    try:
        activateRelay(Relay_1, 'High')
    except RuntimeError:
        print("Entrance is still opened")

    return


@multitasking.task
def lock_entrance_one():

    setGpioMode()
    setupRelayPin(Relay_1)

    print(" EM 1 locked at " + str(datetime.now()))
    try:
        deActivateRelay(Relay_1, 'High')
    except RuntimeError:
        print("Entrance is still opened")

    return


@multitasking.task
def unlock_entrance_two():

    setGpioMode()
    setupRelayPin(Relay_2)

    print(" EM 2 unlocked at " + str(datetime.now()))
    try:
        activateRelay(Relay_2, 'High')
    except RuntimeError:
        print("Entrance is still opened")

    return


@multitasking.task
def lock_entrance_two():

    setGpioMode()
    setupRelayPin(Relay_2)

    print(" EM 2 locked at " + str(datetime.now()))
    try:
        deActivateRelay(Relay_2, 'High')
    except RuntimeError:
        print("Entrance is still opened")

    return


def main():
    trigger_relay_one()
    trigger_relay_two()


if __name__ == '__main__':
    main()
