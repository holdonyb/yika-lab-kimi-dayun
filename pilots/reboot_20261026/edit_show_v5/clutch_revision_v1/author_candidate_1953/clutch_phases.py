import json
from pathlib import Path

FPS = 24
FRAMES = 192
ANGULAR_SPEED = 8.0
PRESSURE_LIFT = .010
DISC_FLOAT = .002
BEARING_FREE_TRAVEL = .009
BEARING_LOAD_TRAVEL = .007
FINGER_TRAVEL = .007
AXIAL_DISPLAY_SCALE = 4.0


def smooth(t,a,b):
    if t <= a:
        return 0.0
    if t >= b:
        return 1.0
    x = (t-a)/(b-a)
    return x*x*(3-2*x)


def timeline():
    rows = []
    driven = 0.0
    previous_speed = 0.0
    for frame in range(1,FRAMES+1):
        t = (frame-1)/FPS
        if t < 2:
            release = 0.0
            driven_speed = ANGULAR_SPEED
            phase = 'engaged'
        elif t < 2.25:
            release = 0.0
            driven_speed = ANGULAR_SPEED
            phase = 'release_free_travel'
        elif t < 3:
            release = smooth(t,2.25,3)
            driven_speed = ANGULAR_SPEED*(1-release)
            phase = 'releasing'
        elif t < 4.2:
            release = 1.0
            driven_speed = 0.0
            phase = 'disengaged'
        elif t < 4.65:
            release = 1-smooth(t,4.2,4.65)
            driven_speed = 0.0
            phase = 'reengaging'
        elif t < 5:
            release = 0.0
            driven_speed = ANGULAR_SPEED*smooth(t,4.65,5)
            phase = 'synchronizing'
        else:
            release = 0.0
            driven_speed = ANGULAR_SPEED
            phase = 'engaged'
        if t < 2.25:
            free_travel = BEARING_FREE_TRAVEL*smooth(t,2,2.25)
        elif t < 4.65:
            free_travel = BEARING_FREE_TRAVEL
        else:
            free_travel = BEARING_FREE_TRAVEL*(1-smooth(t,4.65,4.85))
        if frame > 1:
            driven += previous_speed/FPS
        bearing_travel = free_travel+BEARING_LOAD_TRAVEL*release
        rows.append({'frame':frame,'sourceTime':t,'phase':phase,'engine_angle':t*ANGULAR_SPEED,
                     'clutch_angle':driven,'wheel_angle':driven/3,
                     'clutch_release':release,'engineSpeed':ANGULAR_SPEED,'drivenSpeed':driven_speed,
                     'pressureGap':.008*release,'flywheelGap':.002*release,
                     'pressureLift':PRESSURE_LIFT*release,'discFloat':DISC_FLOAT*release,
                     'bearingTravel':bearing_travel,'fingerDeflection':FINGER_TRAVEL*release,
                     'bearingFingerGap':.009-bearing_travel+FINGER_TRAVEL*release})
        previous_speed = driven_speed
    return rows


def phase_report():
    rows = timeline()
    first_gap = next(row['frame'] for row in rows if row['pressureGap'] > 0 and row['flywheelGap'] > 0)
    recontact = next(row['frame'] for row in rows[97:] if row['pressureGap'] == 0 and row['flywheelGap'] == 0)
    spring_contact = next(row['frame'] for row in rows if row['bearingFingerGap'] == 0)
    return {'fps':FPS,'frameCount':FRAMES,'durationSeconds':FRAMES/FPS,
            'mechanism':'Generic single dry clutch; push-type release bearing and deflecting diaphragm spring',
            'axialDisplayScale':AXIAL_DISPLAY_SCALE,
            'nominalPressureGapMeters':.002,'nominalFlywheelGapMeters':.0005,
            'actualFullReleasePressureGapMeters':.008,'actualFullReleaseFlywheelGapMeters':.002,
            'scaleNote':'Axial clearances are four times the declared teaching nominal, not OEM measurements',
            'contactSequence':'Bearing first takes up free play, then deflects fingers; on reassembly the friction faces make contact before the stopped input accelerates',
            'keyPhases':{
                'engagedStill':{'frame':25,'sourceTime':1.0},
                'startRelease':{'frame':50,'sourceTime':49/24},
                'releaseBearingContactsSpring':{'frame':spring_contact,'sourceTime':(spring_contact-1)/24},
                'firstFrictionSeparation':{'frame':first_gap,'sourceTime':(first_gap-1)/24},
                'fullyDisengaged':{'frame':73,'sourceTime':3.0},
                'releasedStill':{'frame':85,'sourceTime':3.5},
                'startReengage':{'frame':102,'sourceTime':101/24},
                'recontact':{'frame':recontact,'sourceTime':(recontact-1)/24},
                'synchronized':{'frame':121,'sourceTime':5.0},
                'reengagedStill':{'frame':145,'sourceTime':6.0},
            },
            'frames':rows}


if __name__ == '__main__':
    path = Path(__file__).resolve().parent/'clutch_phase.json'
    path.write_text(json.dumps(phase_report(),indent=2),encoding='utf-8')
    print(path)
