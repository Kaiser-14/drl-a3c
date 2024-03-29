training = {
	'env_name': 'A3C.envs.eve:Eve-v0',
	# 'CartPole-v0' to test / 'A3C.envs.eve:Eve-v0' / 'A3C.envs.energy:Energy-v0' to deploy
	'save_path': './Training/',
	'model_report': 5,  # Default was 20, but 600 corresponds to the whole EVE video
}

probe = {
	'data_plane': 'rest',
	'kafka': {
		'address': [
			'192.168.1.88',
		],
		'topic': [
			# [
			# 	'metric.topic.Blockiness_es',
			# 	'metric.topic.SpatialActivity_es',
			# 	'metric.topic.BlockLoss_es',
			# 	'metric.topic.Blur_es',
			# 	'metric.topic.TemporalActivity_es'],
			[
				'metric.topic.Blockiness_gr',
				'metric.topic.SpatialActivity_gr',
				'metric.topic.BlockLoss_gr',
				'metric.topic.Blur_gr',
				'metric.topic.TemporalActivity_gr']
		]
	},
	'rest': {
		'address': [
			'http://localhost:5000/api/probe'
		]}
}

transcoder = {
	'address': ['192.168.1.120:3000'],
	'profile': [7500, 15000, 25000],
	'background': ['192.168.1.99:3000']
}
