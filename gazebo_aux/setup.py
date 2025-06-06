import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'gazebo_aux'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), 
            glob(os.path.join('launch', '*launch.[pxy][yma]*')))
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='borg',
    maintainer_email='dpsoler09@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'overwatch = gazebo_aux.overwatch:main',
            'handler = gazebo_aux.handler:main',
            'handler_af25a = gazebo_aux.handler_af25a:main',
        ],
    },
)
