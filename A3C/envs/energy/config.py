training = dict(
    env_name='CartPole-v0',
    # env_name='A3C.envs.media:Media-v0',
    # env_name='A3C.envs.energy:Energy-v0',
    report=20,  # Steps to report to the global model
)
save = dict(
    path='./Training/',  # Save path for the model
)
kafka = dict(
    address='192.168.0.55:9092',  # IP address + port of the Kafka server
    topic='eve.a3c',  # Topic associated of the Kafka Server
)
# Energy
api = dict(
    enable=False,  # Save path for the model
    address='None',  # IP Address of the REST API
    port='5000',  # Port of the REST API
)
