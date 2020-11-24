from gym.envs.registration import register

register(
    id='Eve-v0',
    entry_point='A3C.envs.eve:EveEnv'
)

register(
    id='Energy-v0',
    entry_point='A3C.envs.energy:EnergyEnv'
)
