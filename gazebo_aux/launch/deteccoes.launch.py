# deteccoes.launch.py
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='apriltag_ros',
            executable='apriltag_node',
            name='apriltag_node',
            remappings=[
                ('image_rect', '/camera/image_raw'),
                ('camera_info', '/camera/camera_info'),
            ],
            parameters=[{
                'tag_family': 'tag36h11',
                'approximate_sync': True,
                'max_sync_delay': 0.3,
                'use_sim_time': True
            }],
        ),
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='bridge_image',
            arguments=[
                '/camera/image_raw@sensor_msgs/msg/Image@gz.msgs.Image',
                '--ros-args', '--param', 'use_multithreaded_executor:=true'
            ],
            parameters=[{'queue_size': 10}],
        ),
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='bridge_info',
            arguments=[
                '/camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo',
                '--ros-args', '--param', 'use_multithreaded_executor:=true'
            ],
            parameters=[{'queue_size': 10}],
        ),
        Node(
            package='gazebo_aux',
            executable='april_tag',
            name='april_tag',
        ),
        Node(
            package='gazebo_aux',
            executable='yolo',
            name='yolo_detector',
        )
    ])
