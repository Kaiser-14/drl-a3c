training = {
	'env_name': 'A3C.envs.eve:Eve-v0',  # 'CartPole-v0' to test / 'A3C.envs.eve:Eve-v0' to deploy
	'save_path': './Training/',
	'model_report': 20,
}

probe = {
	'data_plane': 'rest',
	'kafka': {
		'address': ['192.168.1.88', '192.168.1.89'],
		'topic': [
			[
				'metric.topic.Blockiness_es',
				'metric.topic.SpatialActivity_es',
				'metric.topic.BlockLoss_es',
				'metric.topic.Blur_es',
				'metric.topic.TemporalActivity_es'
			],
			[
				'metric.topic.Blockiness_gr',
				'metric.topic.SpatialActivity_gr',
				'metric.topic.BlockLoss_gr',
				'metric.topic.Blur_gr',
				'metric.topic.TemporalActivity_gr'
			],
		]
	},
	'rest': {'address': ['http://localhost:5000/api/probe']},
}

transcoder = {
	'address': ['192.168.1.88:9092', '192.168.1.88:9092'],
	'profile': [25000, 15000, 1000],
}
