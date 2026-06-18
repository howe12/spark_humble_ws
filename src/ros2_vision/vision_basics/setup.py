from setuptools import find_packages, setup

package_name = 'vision_basics'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='spark',
    maintainer_email='howe12@126.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'ros2_img_show = vision_basics.ros2_img_show:main',
            'ros2_bgr2gray = vision_basics.ros2_bgr2gray:main',
            'ros2_bgr2hsv = vision_basics.ros2_bgr2hsv:main',
            'ros2_blur = vision_basics.ros2_blur:main',
            'ros2_edge = vision_basics.ros2_edge:main',
            'ros2_morph = vision_basics.ros2_morph:main',
            'ros2_hist = vision_basics.ros2_hist:main',
            'ros2_corner = vision_basics.ros2_corner:main',
            'ros2_match = vision_basics.ros2_match:main',
            'pcd_subscriber = vision_basics.pcd_subscriber:main',
            'pcd_filter = vision_basics.pcd_filter:main',
            'pcd_downsample = vision_basics.pcd_downsample:main',
            'pcd_stats = vision_basics.pcd_stats:main',
            'ros2_grasp_detect = vision_basics.ros2_grasp_detect:main',
            'ros2_tag_detect = vision_basics.ros2_tag_detect:main',
        ],
    },
)
