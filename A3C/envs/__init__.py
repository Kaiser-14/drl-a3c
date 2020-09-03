from gym.envs.registration import register

register(
    id='Media-v0',
    entry_point='A3C.envs.media:MediaEnv'
)

register(
    id='Energy-v0',
    entry_point='A3C.envs.energy:EnergyEnv'
)
