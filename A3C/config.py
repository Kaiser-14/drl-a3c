training = dict(
    # env_name='CartPole-v0',
    env_name='A3C.envs.media:Media-v0',
    # env_name='A3C.envs.energy:Energy-v0',
    max_eps=500,  # Maximum number of episodes of training
    report=25,  # Steps to report to the global model
    # render=True,  # Set to True to render the environment (e.g. Cartpole)
)
save = dict(
    aux=0,
    path='./Training/',  # Save path for the model
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
