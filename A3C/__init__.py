from gym.envs.registration import register

register(
    id='Media-v0',
    entry_point='A3C.envs:MediaEnv',
)