from setuptools import setup

package_name = 'pika_remote_diana'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/teleop_double_diana.launch.py']),
        ('share/' + package_name + '/launch', ['launch/teleop_single_diana.launch.py']),
        ('share/' + package_name + '/config', [
            'config/left_params.yaml',
            'config/right_params.yaml',
        ]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='your_name',
    maintainer_email='you@example.com',
    description='Teleop support for Diana arm',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'teleop_diana = pika_remote_diana.teleop_diana:main',
        ],
    },
)
