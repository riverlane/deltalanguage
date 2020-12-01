from deltalanguage.runtime import DeltaRuntimeExit
from deltalanguage.wiring import DeltaBlock


@DeltaBlock()
def user_interface() -> bool:
    if input('Start Experiment (y/n): ') == 'y':
        return True
    else:
        raise DeltaRuntimeExit
