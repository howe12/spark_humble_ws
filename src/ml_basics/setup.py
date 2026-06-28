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
            'waste_classifier = ml_basics.waste_classifier:main',
            'nlp_intent_classifier = ml_basics.nlp_intent_classifier:main',
            'nlp_param_parser = ml_basics.nlp_param_parser:main',
            'nlp_cmd_control = ml_basics.nlp_cmd_control:main',
            # 4.1 颜色跟随
            'color_follow = ml_basics.color_follow:main',
            # 4.2 笑脸检测
            'face_smile_detect = ml_basics.face_smile_detect:main',
            # 4.3 人脸识别
            'face_capture = ml_basics.face_capture:main',
            'face_trainer = ml_basics.face_trainer:main',
            'face_recognizer = ml_basics.face_recognizer:main',
        ],
    },
)
