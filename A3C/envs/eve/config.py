training = dict(
    # env_name='CartPole-v0',
    env_name='A3C.envs.eve:Eve-v0',
    report=20,  # Steps to report to the global model
)
save = dict(
    path='./Training/',  # Save path for the model
)
# EVE
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
# kafka = dict(
    # address='192.168.0.55:9092',  # IP address + port of the Kafka server
    # topic='eve.a3c',  # Topic associated of the Kafka Server
# )
kafka = [
    ['app.uc1.server', 'app.uc1.italy'],
    ['app.uc1.italy', 'app.uc1.client'],
]
transcoder = [
    ['172.17.0.2', '3000'],
    ['172.17.0.2', '3000']
]
streaming = [
    30000, 20000, 10000
]
api = dict(
    enable=False,  # Save path for the model
    address='None',  # IP Address of the REST API
    port='5000',  # Port of the REST API
)
