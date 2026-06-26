from setuptools import setup

package_name = 'ml_basics'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/' + package_name, ['package.xml']),
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='spark',
    maintainer_email='spark@nxrobo.com',
    description='Spark ML Basics — ROS2 practice course',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'ros2_imu_tracker = ml_basics.ros2_imu_tracker:main',
        ],
    },
)
