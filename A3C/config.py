training = dict(
    env_name='CartPole-v0',
    # env_name='A3C.envs.media:Media-v0',
    # env_name='A3C.envs.energy:Energy-v0',
    report=20,  # Steps to report to the global model
)
save = dict(
    path='./Training/',  # Save path for the model
)
api = dict(
    enable=False,  # Save path for the model
    address='192.168.1.44',  # IP Address of the REST API
    port='5000',  # Port of the REST API
)
traffic_manager = dict(
    max_capacity=20000
)
vce = dict(
    address='172.17.0.2',  # IP Address of the virtual Compression Engine
    port='3000',  # Port of the virtual Compression Engine
)
bg_tf = dict(
    address='localhost',  # IP Address of the Background Traffic
    port='3000',  # Port of the Background Traffic
)
kafka = dict(
    address='192.168.0.55:9092',  # IP address + port of the Kafka server
    topic='eve.a3c',  # Topic associated of the Kafka Server
)
