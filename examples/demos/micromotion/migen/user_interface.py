import deltalanguage as dl


@dl.DeltaBlock()
def user_interface() -> bool:
    if input('Start Experiment (y/n): ') == 'y':
        return True
    else:
        raise dl.DeltaRuntimeExit
